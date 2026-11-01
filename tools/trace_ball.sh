#!/bin/bash
# 1回投げる間のボール軌跡(Gazeboのpose/info)を記録して、要約を表示する
source /opt/ros/humble/setup.bash
source /home/ubuntu/airobot_ws/install/setup.bash
source /home/ubuntu/throw_ws/install/setup.bash
bash /home/ubuntu/throw_ws/tools/reset_ball.sh > /dev/null
sleep 1
timeout 16 ign topic -e -t /world/default/pose/info > /tmp/poseinfo.txt 2>/dev/null &
ros2 run crane_plus_throw throw_node --ros-args "$@" 2>&1 | grep -E "release|完了"
wait
python3 /home/ubuntu/throw_ws/tools/parse_trace.py /tmp/poseinfo.txt
