"""俯瞰カメラの画像を1枚受け取り、YOLOで推論して結果を表示・保存する確認用スクリプト."""
import sys

import cv2
import numpy as np
import rclpy
from rclpy.node import Node
from sensor_msgs.msg import Image
from ultralytics import YOLO

model_name = sys.argv[1] if len(sys.argv) > 1 else 'yolov8n.pt'


def main():
    rclpy.init()
    node = Node('yolo_check')
    got = []
    node.create_subscription(Image, '/overhead_camera/image', got.append, 1)
    while not got:
        rclpy.spin_once(node, timeout_sec=0.5)
    msg = got[0]
    img = np.frombuffer(msg.data, np.uint8).reshape(msg.height, msg.width, 3)
    bgr = cv2.cvtColor(img, cv2.COLOR_RGB2BGR)
    cv2.imwrite('/tmp/overhead.png', bgr)

    model = YOLO(model_name)
    result = model(bgr, conf=0.05, verbose=False)[0]
    for box in result.boxes:
        name = model.names[int(box.cls)]
        x1, y1, x2, y2 = box.xyxy[0].tolist()
        print(f'{name:15s} conf={float(box.conf):.2f}  center=({(x1 + x2) / 2:.0f},{(y1 + y2) / 2:.0f})')
    cv2.imwrite('/tmp/overhead_yolo.png', result.plot())
    node.destroy_node()
    rclpy.shutdown()


if __name__ == '__main__':
    main()
