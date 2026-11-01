"""振る速さを変えて試投を繰り返し、着地位置を記録するデータ収集ノード.

離すのは常に真上(joint2=0). 離す角度を変える方式も試したが、着地距離が20〜25cmしか変わらなかった.

ボールの真の位置(Gazeboの/model/ball/odometry)は、ここでは学習データのラベルとしてだけ使う.
"""
import csv
import os
import random
import subprocess
import sys
import time
from math import hypot

import rclpy
from nav_msgs.msg import Odometry
from std_msgs.msg import Empty

from crane_plus_throw.throw_node import ThrowNode, spin_in_background

TABLE_Z = 1.015          # 机の天板の高さ(=base_linkのワールドz)
BALL_REST_Z = 1.035      # 机に置いたボール中心の高さ


def set_model_pose(name, x, y, z):
    req = f'name: "{name}", position: {{x: {x}, y: {y}, z: {z}}}, orientation: {{w: 1}}'
    subprocess.run(['ign', 'service', '-s', '/world/default/set_pose',
                    '--reqtype', 'ignition.msgs.Pose', '--reptype', 'ignition.msgs.Boolean',
                    '--timeout', '3000', '--req', req],
                   stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)


class Collector(ThrowNode):

    def __init__(self):
        super().__init__()
        self.ball = None          # (sim時刻, x, y, z)
        self.track = None         # 記録中ならリスト
        self.create_subscription(Odometry, '/model/ball/odometry', self.on_pose, 100)

    def on_pose(self, msg):
        t = msg.header.stamp.sec + msg.header.stamp.nanosec * 1e-9
        p = msg.pose.pose.position
        self.ball = (t, p.x, p.y, p.z)
        if self.track is not None:
            self.track.append(self.ball)

    def wait_still(self, timeout=10.0):
        """0.5秒間で1mm以上動かなければ止まったとみなす."""
        end = time.time() + timeout
        while time.time() < end:
            a = self.ball
            time.sleep(0.5)
            b = self.ball
            if a and b and max(abs(p - q) for p, q in zip(a[1:], b[1:])) < 0.001:
                return True
        return False

    def kill_ball_motion(self):
        """静止したアームにボールを一瞬固定して、速度と回転を0にする.

        set_poseは位置しか変えないため、転がり続けるボールはそのまま戻しても動き続ける.
        """
        self.detach_pub.publish(Empty())
        time.sleep(0.2)
        self.attach_pub.publish(Empty())
        time.sleep(0.3)
        self.detach_pub.publish(Empty())
        time.sleep(0.2)

    def reset_ball(self, x, y):
        for _ in range(3):
            self.kill_ball_motion()
            set_model_pose('ball', x, y, BALL_REST_Z)
            time.sleep(0.5)
            if self.wait_still(3.0) and hypot(self.ball[1] - x, self.ball[2] - y) < 0.005:
                return True
        return False

    def trial(self, speed, ball_xy):
        if not self.reset_ball(*ball_xy):
            self.get_logger().warn('ボールを初期位置に戻せない')
            return None
        self.pick(ball_xy[0], ball_xy[1], BALL_REST_Z - TABLE_Z)
        self.track = []
        self.throw(1.0, 0.0, 0.0, speed)   # データ収集は+x方向にだけ投げる
        self.wait_still(5.0)
        track, self.track = self.track, None
        self.go_home()
        self.trial_count = getattr(self, 'trial_count', 0) + 1
        with open(f'/tmp/track_{self.trial_count}.csv', 'w') as f:   # 失敗の調査用に軌跡を残す
            f.writelines(f'{t:.3f},{x:.4f},{y:.4f},{z:.4f}\n' for t, x, y, z in track)
        return summarize(track)


def summarize(track):
    """軌跡から 最高点z, 最初の着地点, 最終位置 を求める."""
    if not track:
        return None
    peak = max(track, key=lambda r: r[3])
    touch = next((r for r in track if r[0] > peak[0] and r[3] < BALL_REST_Z + 0.01), None)
    final = track[-1]
    return {
        'peak_z': peak[3],
        'touch_x': touch[1] if touch else None,
        'touch_y': touch[2] if touch else None,
        'final_x': final[1],
        'final_y': final[2],
    }


def main():
    # 使い方: collect_data 出力CSV 試投回数 [振る速さの最小 最大]
    out = sys.argv[1]
    n = int(sys.argv[2])
    lo, hi = (float(sys.argv[3]), float(sys.argv[4])) if len(sys.argv) > 4 else (0.8, 2.0)
    rclpy.init()
    node = Collector()
    spin_in_background(node)
    node.setup()
    # 箱は投げる方向(y=0)から外しておく
    set_model_pose('target_box', 0.30, 0.6, TABLE_Z)

    new = not os.path.exists(out)
    with open(out, 'a', newline='') as f:
        w = csv.writer(f)
        if new:
            w.writerow(['swing_speed', 'peak_z', 'touch_x', 'touch_y', 'final_x', 'final_y'])
        for i in range(n):
            speed = random.uniform(lo, hi)
            r = node.trial(speed, (0.05, -0.13))
            if r is None:
                continue
            row = [f'{speed:.4f}'] + [
                '' if r[k] is None else f'{r[k]:.4f}'
                for k in ['peak_z', 'touch_x', 'touch_y', 'final_x', 'final_y']]
            w.writerow(row)
            f.flush()
            print(f'[{i + 1}/{n}] ' + ','.join(row), flush=True)
    node.destroy_node()
    rclpy.shutdown()


if __name__ == '__main__':
    main()
