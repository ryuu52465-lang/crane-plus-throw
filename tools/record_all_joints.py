"""/joint_states を指定秒数、0.25秒ごとに全関節分表示する調査用スクリプト(手首の張り付きの発見に使用)."""
import sys, time, rclpy
from rclpy.node import Node
from sensor_msgs.msg import JointState
rclpy.init(); n = Node("rec_all"); last = [0.0]; t0 = [None]
def cb(m):
    t = m.header.stamp.sec + m.header.stamp.nanosec * 1e-9
    if t0[0] is None: t0[0] = t
    if t - last[0] >= 0.25:
        q = dict(zip(m.name, m.position)); last[0] = t
        print("t=%5.2f j1=%+.2f j2=%+.2f j3=%+.2f j4=%+.2f hand=%+.2f" % (t - t0[0], q["crane_plus_joint1"], q["crane_plus_joint2"], q["crane_plus_joint3"], q["crane_plus_joint4"], q["crane_plus_joint_hand"]), flush=True)
n.create_subscription(JointState, "/joint_states", cb, 10)
end = time.time() + float(sys.argv[1])
while time.time() < end: rclpy.spin_once(n, timeout_sec=0.1)
