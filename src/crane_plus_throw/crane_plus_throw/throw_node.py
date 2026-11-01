"""ボールをつかんで振りかぶり、手首のスナップを効かせて真上で離して投げるノード.

関節の符号: joint2は+で前傾, joint3/joint4は+で後ろに曲がる.
逆運動学は書籍のcrane_plus_commander.kinematicsを利用する.
"""
import threading
import time
from math import atan2, pi

import rclpy
from rclpy.node import Node
from builtin_interfaces.msg import Duration
from sensor_msgs.msg import JointState
from std_msgs.msg import Empty, String
from trajectory_msgs.msg import JointTrajectory, JointTrajectoryPoint

from crane_plus_commander.kinematics import inverse_kinematics, joint_in_range

ARM_JOINTS = ['crane_plus_joint1', 'crane_plus_joint2',
              'crane_plus_joint3', 'crane_plus_joint4']
HAND_JOINT = 'crane_plus_joint_hand'


def to_duration(t):
    return Duration(sec=int(t), nanosec=int((t % 1) * 1e9))


class ThrowNode(Node):

    def __init__(self):
        super().__init__('throw_node')
        self.declare_parameter('ball_xyz', [0.05, -0.13, 0.02])     # base_link基準
        self.declare_parameter('target_xy', [0.30, 0.0])
        self.declare_parameter('gripper_open', -0.6)
        self.declare_parameter('gripper_hold', -0.3)                 # ボールに軽く添える開き具合
        self.declare_parameter('joint_vel_limit', 2.0)               # CRANE+のURDFの速度上限
        # 振りかぶり(joint2〜4)。手首は肩・肘より振りかぶりを小さくして、その分だけ遅れて動き出す
        self.declare_parameter('windup', [-1.3, 1.3, 1.0])
        self.declare_parameter('after_release', [0.4, -0.4, -0.4])   # 離した後に止める姿勢
        self.declare_parameter('stop_time', 0.4)
        self.declare_parameter('release_joint2', 0.0)                # この角度を超えたら離す
        self.declare_parameter('swing_speed', 2.0)                   # 振る角速度(速度上限まで)

        self.arm_pub = self.create_publisher(
            JointTrajectory, '/crane_plus_arm_controller/joint_trajectory', 10)
        self.hand_pub = self.create_publisher(
            JointTrajectory, '/crane_plus_gripper_controller/joint_trajectory', 10)
        self.attach_pub = self.create_publisher(Empty, '/throw/attach', 10)
        self.detach_pub = self.create_publisher(Empty, '/throw/detach', 10)

        self.joint2 = 0.0
        self.release_angle = None   # 投げている間だけ設定する
        self.released = False
        self.create_subscription(JointState, '/joint_states', self.on_joint_states, 100)
        self.grip_state = None   # DetachableJointの状態('attached' / 'detached')
        self.create_subscription(String, '/model/ball/detachable_joint/state',
                                 self.on_grip_state, 10)

    def on_grip_state(self, msg):
        self.grip_state = msg.data
        self.get_logger().info(f'DetachableJoint: {msg.data}')

    def p(self, name):
        return self.get_parameter(name).value

    def on_joint_states(self, msg):
        if 'crane_plus_joint2' not in msg.name:
            return
        self.joint2 = msg.position[msg.name.index('crane_plus_joint2')]
        if self.release_angle is not None and not self.released \
                and self.joint2 >= self.release_angle:
            self.detach_pub.publish(Empty())
            self.released = True
            self.send_hand(self.p('gripper_open'), 0.1)   # 離すと同時に手を開く
            stamp = msg.header.stamp.sec + msg.header.stamp.nanosec * 1e-9
            self.get_logger().info(f'release! joint2={self.joint2:.3f} t={stamp:.3f}')

    def move_arm(self, points, wait=True):
        """points: [(関節角4つ, 開始からの時刻[, 角速度4つ]), ...] を送り、waitなら終わるまで待つ."""
        msg = JointTrajectory()
        msg.joint_names = ARM_JOINTS
        for point in points:
            pt = JointTrajectoryPoint()
            pt.positions = [float(v) for v in point[0]]
            pt.time_from_start = to_duration(point[1])
            if len(point) > 2:
                pt.velocities = [float(v) for v in point[2]]
            msg.points.append(pt)
        self.arm_pub.publish(msg)
        if wait:
            time.sleep(points[-1][1] + 0.3)

    def send_hand(self, value, t):
        msg = JointTrajectory()
        msg.joint_names = [HAND_JOINT]
        pt = JointTrajectoryPoint()
        pt.positions = [float(value)]
        pt.time_from_start = to_duration(t)
        msg.points.append(pt)
        self.hand_pub.publish(msg)

    def move_hand(self, value, t=0.5):
        self.send_hand(value, t)
        time.sleep(t + 0.3)

    def ik(self, x, y, z):
        """手先を真下に向けた姿勢から少しずつ傾け、全関節が可動範囲に収まる解を返す.

        範囲外の角度を指令すると手首が可動限界に張り付き、その後の指令に追従しなくなった.
        """
        for k in range(16):
            pitch = -pi / 2 + k * pi / 60      # 真下(-90°)から-45°まで3°刻み
            q = inverse_kinematics([x, y, z, pitch], elbow_up=True)
            if q is not None and all(joint_in_range(q)):
                return q
        raise RuntimeError(f'可動範囲内のIK解なし: {(x, y, z)}')

    def snap_throw(self, yaw, speed):
        """肩・肘を先に振り、手首を遅らせてスナップさせ、全関節がspeedで動く瞬間に真上を通す."""
        v = min(speed, self.p('joint_vel_limit'))
        w2, w3, w4 = self.p('windup')
        t_straight = max(abs(w2), abs(w3)) / v      # 肩・肘が真上(0)に着く時刻
        t_wrist = t_straight - abs(w4) / v          # 手首が動き出す時刻(それまで溜める)
        # 肩・肘がt_wristまでに進む角度(速度上限で動く前提)
        s = v * t_wrist
        a2, a3, a4 = self.p('after_release')
        straight_vel = [0.0, v, -v, -v]             # 前に振る向き: joint2は+, joint3/4は-
        self.move_arm([
            ([yaw, w2 + s, w3 - s, w4], t_wrist, [0.0, v, -v, 0.0]),
            ([yaw, 0.0, 0.0, 0.0], t_straight, straight_vel),
            ([yaw, a2, a3, a4], t_straight + self.p('stop_time'), [0.0] * 4),
        ], wait=False)
        return t_straight + self.p('stop_time')

    def wait_for_subscribers(self, timeout=10.0):
        """ブリッジ等と接続される前にpublishするとメッセージが捨てられるため、接続を待つ."""
        pubs = [self.arm_pub, self.hand_pub, self.attach_pub, self.detach_pub]
        end = time.time() + timeout
        while time.time() < end:
            if all(p.get_subscription_count() > 0 for p in pubs):
                return
            time.sleep(0.1)
        raise RuntimeError('コントローラかros_gz_bridgeに接続できない')

    def setup(self):
        self.wait_for_subscribers()
        # 接続直後の最初のメッセージが捨てられることがあるため、害のない指令を数回送って慣らす.
        # detachは、起動直後に固定状態になっているDetachableJointの解放も兼ねる
        for _ in range(3):
            self.move_arm([([0.0, 0.0, 0.0, 0.0], 0.5)], wait=False)
            self.send_hand(self.p('gripper_open'), 0.5)
            self.detach_pub.publish(Empty())
            time.sleep(0.5)
        time.sleep(0.5)

    def pick(self, bx, by, bz):
        """base_link基準の(bx, by, bz)にあるボールを真上からつかむ."""
        self.get_logger().info(f'つかみに行く ({bx:.3f}, {by:.3f})')
        self.move_hand(self.p('gripper_open'))
        self.move_arm([(self.ik(bx, by, bz + 0.06), 2.0)])
        self.move_arm([(self.ik(bx, by, bz), 1.0)])
        # 先に閉じると指がボールを押し上げ、手の中の位置が毎回ずれて飛距離が2通りに分かれた.
        # 机の上で止まっているうちに固定し、指は軽く添えるだけにする
        self.attach_pub.publish(Empty())
        time.sleep(0.3)
        self.move_hand(self.p('gripper_hold'))
        self.move_arm([(self.ik(bx, by, bz + 0.06), 1.0)])

    def throw(self, tx, ty, release, speed):
        """(tx, ty)の方向へ向き、角速度speedで振って、joint2がreleaseを超えた瞬間に離す."""
        yaw = atan2(ty, tx)
        self.get_logger().info(f'振りかぶる (yaw={yaw:.3f})')
        self.move_arm([([yaw] + list(self.p('windup')), 2.0)])
        time.sleep(0.5)

        self.get_logger().info(f'投げる (release_joint2={release:.3f}, speed={speed:.3f})')
        self.released = False
        self.release_angle = release
        duration = self.snap_throw(yaw, speed)
        end = time.time() + duration + 0.5
        while not self.released and time.time() < end:
            time.sleep(0.005)
        self.release_angle = None
        if not self.released:   # 念のため
            self.detach_pub.publish(Empty())
        time.sleep(max(0.0, end - time.time()) + 1.0)

    def go_home(self):
        self.move_arm([([0.0, 0.0, 0.0, 0.0], 2.0)])

    def run(self):
        self.setup()
        self.pick(*self.p('ball_xyz'))
        self.throw(*self.p('target_xy'), self.p('release_joint2'), self.p('swing_speed'))
        self.go_home()
        self.get_logger().info('完了')


def spin_in_background(node):
    """run系の処理はsleepで待つため、コールバックは別スレッドで回す."""
    threading.Thread(target=rclpy.spin, args=(node,), daemon=True).start()


def main():
    rclpy.init()
    node = ThrowNode()
    spin_in_background(node)
    try:
        node.run()
    finally:
        node.destroy_node()
        rclpy.shutdown()


if __name__ == '__main__':
    main()
