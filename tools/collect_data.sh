#!/bin/bash
# コンテナ内で実行: 離す角度を変えて試投を繰り返し、着地位置をCSVに追記する
# 使い方: collect_data.sh 出力CSV 角度1 角度2 ...
source /opt/ros/humble/setup.bash
source /home/ubuntu/airobot_ws/install/setup.bash
source /home/ubuntu/throw_ws/install/setup.bash
out=$1
shift
[ -f "$out" ] || echo 'release_joint2,peak_z,touch_x,touch_y,final_x,final_y' > "$out"
# 箱が着地の邪魔にならないよう、投げる方向(y=0)から外しておく
bash /home/ubuntu/throw_ws/tools/move_box.sh 0.30 0.6 > /dev/null
for r in "$@"; do
  bash /home/ubuntu/throw_ws/tools/reset_ball.sh > /dev/null
  sleep 1
  timeout 16 ign topic -e -t /world/default/pose/info > /tmp/poseinfo.txt 2>/dev/null &
  ros2 run crane_plus_throw throw_node --ros-args -p release_joint2:=$r > /tmp/throw.log 2>&1
  wait
  line="$r,$(python3 /home/ubuntu/throw_ws/tools/parse_trace.py /tmp/poseinfo.txt --csv)"
  echo "$line" | tee -a "$out"
done
