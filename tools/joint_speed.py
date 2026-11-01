"""/joint_states を指定秒数記録し、各関節の最大角速度(位置の差分から計算)を表示する."""
import sys
import time

import rclpy
from rclpy.node import Node
from sensor_msgs.msg import JointState

rows = []


def main():
    duration = float(sys.argv[1]) if len(sys.argv) > 1 else 15.0
    rclpy.init()
    node = Node('joint_speed')
    node.create_subscription(
        JointState, '/joint_states',
        lambda m: rows.append((m.header.stamp.sec + m.header.stamp.nanosec * 1e-9,
                               dict(zip(m.name, m.position)))), 100)
    end = time.time() + duration
    while time.time() < end:
        rclpy.spin_once(node, timeout_sec=0.1)
    for j in ['crane_plus_joint2', 'crane_plus_joint3', 'crane_plus_joint4']:
        vmax = 0.0
        for (t0, a), (t1, b) in zip(rows, rows[1:]):
            if t1 > t0:
                vmax = max(vmax, abs(b[j] - a[j]) / (t1 - t0))
        print(f'{j}: 最大角速度 {vmax:.2f} rad/s')
    node.destroy_node()
    rclpy.shutdown()


if __name__ == '__main__':
    main()
