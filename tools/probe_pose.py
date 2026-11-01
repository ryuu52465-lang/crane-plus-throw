"""指定した関節角にアームを動かし、各リンクの位置(base_link基準)を表示する確認用スクリプト."""
import sys
import time

import rclpy
from rclpy.node import Node
from builtin_interfaces.msg import Duration
from trajectory_msgs.msg import JointTrajectory, JointTrajectoryPoint
import tf2_ros

JOINTS = ['crane_plus_joint1', 'crane_plus_joint2', 'crane_plus_joint3', 'crane_plus_joint4']


def main():
    rclpy.init()
    node = Node('probe_pose')
    pub = node.create_publisher(JointTrajectory, '/crane_plus_arm_controller/joint_trajectory', 10)
    buf = tf2_ros.Buffer()
    tf2_ros.TransformListener(buf, node)

    poses = [[float(v) for v in arg.split(',')] for arg in sys.argv[1:]]
    for q in poses:
        msg = JointTrajectory()
        msg.joint_names = JOINTS
        pt = JointTrajectoryPoint()
        pt.positions = q
        pt.time_from_start = Duration(sec=2)
        msg.points = [pt]
        time.sleep(0.5)
        pub.publish(msg)
        end = time.time() + 3.0
        while time.time() < end:
            rclpy.spin_once(node, timeout_sec=0.1)
        print(f'joints={q}')
        for frame in buf.all_frames_as_string().splitlines():
            name = frame.split(' ')[1]
            try:
                t = buf.lookup_transform('base_link', name, rclpy.time.Time()).transform.translation
                print(f'  {name:28s} x={t.x:+.3f} y={t.y:+.3f} z={t.z:+.3f}')
            except Exception:
                pass
    node.destroy_node()
    rclpy.shutdown()


if __name__ == '__main__':
    main()
