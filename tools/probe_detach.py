"""DetachableJointにattach/detachを順に送り、状態トピックの変化を記録する調査用スクリプト."""
import time

import rclpy
from rclpy.node import Node
from std_msgs.msg import Empty, String


def main():
    rclpy.init()
    node = Node('probe_detach')
    attach = node.create_publisher(Empty, '/throw/attach', 10)
    detach = node.create_publisher(Empty, '/throw/detach', 10)
    log = []
    node.create_subscription(String, '/model/ball/detachable_joint/state',
                             lambda m: log.append((time.time(), m.data)), 10)
    while attach.get_subscription_count() == 0 or detach.get_subscription_count() == 0:
        rclpy.spin_once(node, timeout_sec=0.1)
    t0 = time.time()

    def send(pub, name, wait=1.0):
        print(f'{time.time() - t0:5.1f}s send {name}')
        pub.publish(Empty())
        end = time.time() + wait
        while time.time() < end:
            rclpy.spin_once(node, timeout_sec=0.05)
        while log:
            t, s = log.pop(0)
            print(f'{t - t0:5.1f}s   state={s}')

    # 1) 普通の切り替え  2) 外れている時にdetachを送った後のattach
    for pub, name in [(detach, 'detach'), (attach, 'attach'), (detach, 'detach'),
                      (detach, 'detach(余分)'), (detach, 'detach(余分)'),
                      (attach, 'attach'), (attach, 'attach(余分)'), (detach, 'detach'),
                      (attach, 'attach')]:
        send(pub, name)
    send(detach, 'detach', 2.0)
    rclpy.shutdown()


if __name__ == '__main__':
    main()
