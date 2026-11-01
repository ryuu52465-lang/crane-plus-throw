"""振りかぶり→振り切りの軌道を送る確認用スクリプト.

符号: joint2は+で前傾, joint3/joint4は-で前に曲がる(回転軸が逆向き).
"""
import sys
import time

import rclpy
from rclpy.node import Node
from builtin_interfaces.msg import Duration
from trajectory_msgs.msg import JointTrajectory, JointTrajectoryPoint

JOINTS = ['crane_plus_joint1', 'crane_plus_joint2', 'crane_plus_joint3', 'crane_plus_joint4']
WINDUP = [0.0, -1.2, 1.0, 0.8]    # 全体が後ろに反る
FOLLOW = [0.0, 0.8, -0.6, -0.6]   # 全体が前にしなる
HOME = [0.0, 0.0, 0.0, 0.0]


def point(q, t):
    pt = JointTrajectoryPoint()
    pt.positions = q
    pt.time_from_start = Duration(sec=int(t), nanosec=int((t % 1) * 1e9))
    return pt


def main():
    swing_time = float(sys.argv[1]) if len(sys.argv) > 1 else 0.4
    hold = float(sys.argv[2]) if len(sys.argv) > 2 else 3.0
    rclpy.init()
    node = Node('swing_test')
    pub = node.create_publisher(JointTrajectory, '/crane_plus_arm_controller/joint_trajectory', 10)
    time.sleep(0.5)

    t = 2.0
    pts = [point(WINDUP, t)]
    t += hold
    pts.append(point(WINDUP, t))
    t += swing_time
    pts.append(point(FOLLOW, t))
    t += hold
    pts.append(point(FOLLOW, t))
    t += 2.0
    pts.append(point(HOME, t))

    msg = JointTrajectory()
    msg.joint_names = JOINTS
    msg.points = pts
    pub.publish(msg)
    time.sleep(0.5)
    print(f'sent: swing {swing_time}s, total {t:.1f}s')
    node.destroy_node()
    rclpy.shutdown()


if __name__ == '__main__':
    main()
