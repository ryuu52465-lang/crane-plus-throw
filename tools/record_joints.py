"""/joint_states を記録し、動いている区間の joint2〜4 を0.03秒ごとに表示する調査用スクリプト."""
import sys
import time

import rclpy
from rclpy.node import Node
from sensor_msgs.msg import JointState

rows = []


def main():
    duration = float(sys.argv[1]) if len(sys.argv) > 1 else 20.0
    rclpy.init()
    node = Node('record_joints')
    node.create_subscription(
        JointState, '/joint_states',
        lambda m: rows.append((m.header.stamp.sec + m.header.stamp.nanosec * 1e-9,
                               dict(zip(m.name, m.position)))), 100)
    end = time.time() + duration
    while time.time() < end:
        rclpy.spin_once(node, timeout_sec=0.1)
    # joint2が最も速く増えている区間(投げ)の前後だけを表示する
    speeds = [(b[1]['crane_plus_joint2'] - a[1]['crane_plus_joint2']) / (b[0] - a[0])
              for a, b in zip(rows, rows[1:]) if b[0] > a[0]]
    i = max(range(len(speeds)), key=lambda k: speeds[k])
    t_peak = rows[i][0]
    last = -1.0
    for t, q in rows:
        if t_peak - 1.0 <= t <= t_peak + 0.6 and t - last >= 0.03:
            print(f't={t - t_peak:+.2f}  j2={q["crane_plus_joint2"]:+.2f}  '
                  f'j3={q["crane_plus_joint3"]:+.2f}  j4={q["crane_plus_joint4"]:+.2f}  '
                  f'hand={q["crane_plus_joint_hand"]:+.2f}')
            last = t
    node.destroy_node()
    rclpy.shutdown()


if __name__ == '__main__':
    main()
