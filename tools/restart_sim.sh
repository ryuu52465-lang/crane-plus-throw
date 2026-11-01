#!/bin/bash
# コンテナ内で実行: シミュレーション関連のプロセスをすべて止めてから起動し直す
# pkill -f のパターンに[]を入れて、このスクリプト自身にマッチしないようにしている
for pat in '[r]os2 launch' '[i]gn gazebo' '[p]arameter_bridge' '[s]pawner' \
           '[r]obot_state_publisher' '[s]tatic_transform_publisher' '[r]os_gz_sim create' '[t]hrow_node'; do
  pkill -9 -f "$pat"
done
sleep 2
if pgrep -f '[i]gn gazebo' > /dev/null; then
  echo 'gazeboが止まらない' >&2
  exit 1
fi

source /opt/ros/humble/setup.bash
source /home/ubuntu/airobot_ws/install/setup.bash
source /home/ubuntu/throw_ws/install/setup.bash
export DISPLAY=:0
nohup ros2 launch crane_plus_throw throw_sim.launch.py > /tmp/throw_sim.log 2>&1 &

for i in $(seq 1 30); do
  sleep 2
  if [ "$(grep -c 'Configured and activated' /tmp/throw_sim.log)" -ge 3 ]; then
    echo "起動完了 (${i}x2秒)"
    exit 0
  fi
done
echo 'コントローラが起動しない' >&2
exit 1
