"""カメラ画像から物体を見つけ、学習した投げモデルで箱へ投げ入れるノード.

1. 俯瞰カメラの画像をYOLOで推論し、sports ballを見つける
2. 青い箱は色で見つける
3. 箱までの距離から、学習したThrowModelで振る速さを逆算する
4. ボールをつかんで、箱の方向へ投げる

evaluate:=true のときは、箱とボールをランダムに置いて episodes 回試し、成功率を出す.
demo_distances:=[0.17,0.21,0.25] のときは、箱を正面のその距離に順に置いて投げる(動画用).
record_dir を指定すると、1投ごとにGazeboの3Dビューの録画とAIの判断画像を保存する.
(ランダム配置と成否判定にはGazeboの真の位置を使うが、AIの入力には使わない)
"""
import os
import random
import shutil
import subprocess
import time
from math import atan2, cos, hypot, sin, tan

import cv2
import numpy as np
import rclpy
from cv_bridge import CvBridge
from sensor_msgs.msg import Image
from ultralytics import YOLO

from crane_plus_throw.collect_data import BALL_REST_Z, TABLE_Z, Collector, set_model_pose
from crane_plus_throw.throw_model import load
from crane_plus_throw.throw_node import spin_in_background

# 俯瞰カメラ(throw_world.sdfと合わせる)。画像の上がワールド+x、右がワールド-y
CAM_X, CAM_Y, CAM_Z = 0.17, 0.0, 1.615
CAM_HFOV = 1.0
IMG_W, IMG_H = 640, 480
FOCAL = (IMG_W / 2) / tan(CAM_HFOV / 2)

BOX_INNER = 0.04        # 箱の内寸の半分
BOX_CENTER_Z = 1.035    # 箱を上から見たときの見かけの高さ(底と壁の間)


def pixel_to_world(u, v, z):
    """画像座標(u, v)を、高さzの水平面上のワールド座標(x, y)に変換する."""
    h = CAM_Z - z
    return CAM_X - (v - IMG_H / 2) * h / FOCAL, CAM_Y - (u - IMG_W / 2) * h / FOCAL


def world_to_pixel(x, y, z):
    h = CAM_Z - z
    return int(IMG_W / 2 - (y - CAM_Y) * FOCAL / h), int(IMG_H / 2 - (x - CAM_X) * FOCAL / h)


class AiThrower(Collector):

    def __init__(self):
        super().__init__()
        self.declare_parameter('model_path', '/home/ubuntu/throw_ws/data/throw_model.pt')
        self.declare_parameter('yolo_model', 'yolov8n.pt')
        self.declare_parameter('episodes', 1)
        self.declare_parameter('evaluate', False)
        self.declare_parameter('demo_distances', [0.0])   # 動画用: 箱を置く距離[m]の列。[0.0]なら使わない
        self.declare_parameter('record_dir', '')          # 指定すると1投ごとにGazeboの3Dビューを録画
        self.throw_model = load(self.p('model_path'))
        self.yolo = YOLO(self.p('yolo_model'))
        self.bridge = CvBridge()
        self.image = None
        self.create_subscription(Image, '/overhead_camera/image', self.on_image, 1)
        self.debug_pub = self.create_publisher(Image, '/ai_throw/debug_image', 1)
        lo, hi = self.throw_model.reachable()
        self.get_logger().info(f'学習モデルで届く距離: {lo:.3f}〜{hi:.3f} m')

    def on_image(self, msg):
        self.image = self.bridge.imgmsg_to_cv2(msg, 'bgr8')

    def latest_image(self):
        self.image = None
        while self.image is None:
            time.sleep(0.05)
        return self.image

    def detect_ball(self, img):
        """YOLOでsports ballを探し、最も確からしいものの(画素中心, 信頼度)を返す."""
        result = self.yolo(img, verbose=False)[0]
        best = None
        for box in result.boxes:
            if self.yolo.names[int(box.cls)] != 'sports ball':
                continue
            conf = float(box.conf)
            if best is None or conf > best[2]:
                x1, y1, x2, y2 = box.xyxy[0].tolist()
                best = ((x1 + x2) / 2, (y1 + y2) / 2, conf, (x1, y1, x2, y2))
        return best

    def detect_box(self, img):
        """青い領域のうち最大のものを箱とみなし、その中心画素を返す."""
        hsv = cv2.cvtColor(img, cv2.COLOR_BGR2HSV)
        mask = cv2.inRange(hsv, (100, 120, 80), (130, 255, 255))
        contours, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        if not contours:
            return None
        c = max(contours, key=cv2.contourArea)
        if cv2.contourArea(c) < 500:
            return None
        m = cv2.moments(c)
        return m['m10'] / m['m00'], m['m01'] / m['m00'], cv2.boundingRect(c)

    def perceive(self):
        img = self.latest_image()
        ball = self.detect_ball(img)
        box = self.detect_box(img)
        debug = img.copy()
        result = {}
        if ball:
            u, v, conf, (x1, y1, x2, y2) = ball
            result['ball'] = pixel_to_world(u, v, BALL_REST_Z)
            cv2.rectangle(debug, (int(x1), int(y1)), (int(x2), int(y2)), (0, 255, 255), 2)
            cv2.putText(debug, f'YOLO: sports ball {conf:.2f}', (int(x1) - 40, int(y1) - 8),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 255), 2)
        if box:
            u, v, (bx, by, bw, bh) = box
            result['box'] = pixel_to_world(u, v, BOX_CENTER_Z)
            cv2.rectangle(debug, (bx, by), (bx + bw, by + bh), (255, 255, 0), 2)
            cv2.putText(debug, 'target box', (bx, by - 8),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 0), 2)
        return result, debug

    def publish_debug(self, debug, lines, landing=None):
        if landing:
            cv2.drawMarker(debug, world_to_pixel(*landing, TABLE_Z), (0, 0, 255),
                           cv2.MARKER_CROSS, 24, 2)
        for i, text in enumerate(lines):
            cv2.putText(debug, text, (10, 25 + 22 * i), cv2.FONT_HERSHEY_SIMPLEX, 0.6,
                        (255, 255, 255), 2)
        self.debug_pub.publish(self.bridge.cv2_to_imgmsg(debug, 'bgr8'))
        cv2.imwrite('/tmp/ai_throw_debug.png', debug)

    def episode(self):
        """見る → 狙いを決める → つかむ → 投げる を1回行う. 投げた狙いの情報を返す."""
        seen, debug = self.perceive()
        if 'ball' not in seen or 'box' not in seen:
            self.publish_debug(debug, ['ball or box not found'])
            self.get_logger().warn(f'見つからない: {list(seen)}')
            return None
        bx, by = seen['ball']
        tx, ty = seen['box']
        distance = hypot(tx, ty)
        speed, pred = self.throw_model.speed_for(distance)
        yaw = atan2(ty, tx)
        landing = (pred * cos(yaw), pred * sin(yaw))
        self.get_logger().info(
            f'ball=({bx:.3f},{by:.3f}) box=({tx:.3f},{ty:.3f}) 距離{distance:.3f}m '
            f'→ speed {speed:.3f}rad/s (予測着地 {pred:.3f}m)')
        self.publish_debug(debug, [
            f'ball  ({bx:+.3f}, {by:+.3f}) m',
            f'box   ({tx:+.3f}, {ty:+.3f}) m  dist {distance * 100:.1f} cm',
            f'model: speed {speed:.2f} rad/s -> {pred * 100:.1f} cm',
        ], landing)
        self.pick(bx, by, BALL_REST_Z - TABLE_Z)
        self.throw(tx, ty, 0.0, speed)
        self.go_home()
        return {'speed': speed, 'pred': pred, 'box': (tx, ty)}

    def random_scene(self):
        """評価用: 届く範囲に箱を、つかめる範囲にボールを置く(真の位置を返す)."""
        lo, hi = self.throw_model.reachable()
        r = random.uniform(lo + 0.02, hi - 0.02)
        yaw = random.uniform(-0.5, 0.5)
        box = (r * cos(yaw), r * sin(yaw))
        set_model_pose('target_box', box[0], box[1], TABLE_Z)
        # ボールは箱の反対側(y)の、真上からつかめる範囲(base_linkから約14cm以内)に置く
        side = -1.0 if box[1] >= 0 else 1.0
        ball = (random.uniform(0.02, 0.06), side * random.uniform(0.11, 0.125))
        self.reset_ball(*ball)
        time.sleep(1.0)
        return box, ball

    def ball_in_box(self, box):
        _, x, y, z = self.ball
        return abs(x - box[0]) < BOX_INNER and abs(y - box[1]) < BOX_INNER and z < TABLE_Z + 0.05

    def demo_scene(self, distance):
        """動画用: 箱を正面(+x方向)のdistance[m]に、ボールを決まった位置に置く."""
        box = (distance, 0.0)
        set_model_pose('target_box', box[0], box[1], TABLE_Z)
        self.reset_ball(0.04, -0.12)
        time.sleep(1.0)
        return box


RECORD_TMP = '/tmp/gz_record_tmp.mp4'


def record_video(start, filename=''):
    """GazeboのGUIの3Dビューの録画を開始する(start)/停止してfilenameに保存する.

    Gazeboは次の録画を始めると前の録画ファイルを消すため、一時ファイルに撮ってからコピーする.
    """
    req = f'start: true, format: "mp4", save_filename: "{RECORD_TMP}"' if start else 'stop: true'
    if start and os.path.exists(RECORD_TMP):
        os.remove(RECORD_TMP)
    subprocess.run(['ign', 'service', '-s', '/gui/record_video',
                    '--reqtype', 'ignition.msgs.VideoRecord', '--reptype', 'ignition.msgs.Boolean',
                    '--timeout', '3000', '--req', req],
                   stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    if not start:
        # 書き終わる(ファイルサイズが変わらなくなる)のを待ってからコピーする
        last = -1
        for _ in range(50):
            time.sleep(0.2)
            size = os.path.getsize(RECORD_TMP) if os.path.exists(RECORD_TMP) else -1
            if size > 0 and size == last:
                shutil.copy(RECORD_TMP, filename)
                return
            last = size


def main():
    rclpy.init()
    node = AiThrower()
    spin_in_background(node)
    node.setup()
    evaluate = node.p('evaluate')
    demo = [d for d in node.p('demo_distances') if d > 0.0]
    record_dir = node.p('record_dir')
    if record_dir:
        os.makedirs(record_dir, exist_ok=True)
    results = []
    for i in range(len(demo) if demo else node.p('episodes')):
        if demo:
            box = node.demo_scene(demo[i])
        elif evaluate:
            box, ball = node.random_scene()
        node.kill_ball_motion()
        clip = os.path.join(record_dir, f'throw_{i + 1}.mp4') if record_dir else ''
        if record_dir:
            record_video(True)
            time.sleep(1.0)
        info = node.episode()
        if evaluate or demo or record_dir:
            node.wait_still(5.0)
        if record_dir:
            time.sleep(1.0)
            record_video(False, clip)
            cv2.imwrite(os.path.join(record_dir, f'debug_{i + 1}.png'),
                        cv2.imread('/tmp/ai_throw_debug.png'))
        if evaluate or demo:
            ok = info is not None and node.ball_in_box(box)
            results.append(ok)
            node.get_logger().info(
                f'[{i + 1}] 箱の真の位置 ({box[0]:.3f},{box[1]:.3f}) → {"成功" if ok else "失敗"}')
    if results:
        node.get_logger().info(f'成功率 {sum(results)}/{len(results)}')
    node.destroy_node()
    rclpy.shutdown()


if __name__ == '__main__':
    main()
