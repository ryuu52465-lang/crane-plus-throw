"""ボールを持たずに手首(joint4)などへ順に指令し、追従するか確かめる調査用スクリプト."""
import time, rclpy
from rclpy.node import Node
from builtin_interfaces.msg import Duration
from sensor_msgs.msg import JointState
from trajectory_msgs.msg import JointTrajectory, JointTrajectoryPoint
rclpy.init(); n = Node("wrist_test"); q = {}
n.create_subscription(JointState, "/joint_states", lambda m: q.update(zip(m.name, m.position)), 10)
pub = n.create_publisher(JointTrajectory, "/crane_plus_arm_controller/joint_trajectory", 10)
while pub.get_subscription_count() == 0: rclpy.spin_once(n, timeout_sec=0.1)
for target in [[0, 0, 0, 0], [0, 0, 0, 1.0], [0, 0, 0, -1.0], [0, -1.3, 1.3, 1.0], [0, 0, 0, 0]]:
    m = JointTrajectory(); m.joint_names = ["crane_plus_joint1","crane_plus_joint2","crane_plus_joint3","crane_plus_joint4"]
    p = JointTrajectoryPoint(); p.positions = [float(v) for v in target]; p.time_from_start = Duration(sec=2); m.points = [p]
    for _ in range(3): pub.publish(m); time.sleep(0.1)
    end = time.time() + 3
    while time.time() < end: rclpy.spin_once(n, timeout_sec=0.05)
    print("cmd", target, "-> j2=%.2f j3=%.2f j4=%.2f" % (q["crane_plus_joint2"], q["crane_plus_joint3"], q["crane_plus_joint4"]))
