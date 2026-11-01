#!/bin/bash
# ホスト(Git Bash)からコンテナへソースを送り、colcon buildする
set -e
export MSYS_NO_PATHCONV=1
HERE="$(cygpath -w "$(cd "$(dirname "$0")/.." && pwd)")"
docker exec pai_ros2 rm -rf /home/ubuntu/throw_ws/src /home/ubuntu/throw_ws/tools
docker cp "$HERE/src" pai_ros2:/home/ubuntu/throw_ws/src
docker cp "$HERE/tools" pai_ros2:/home/ubuntu/throw_ws/tools
docker exec pai_ros2 chown -R ubuntu:ubuntu /home/ubuntu/throw_ws
docker exec -u ubuntu pai_ros2 bash -c 'source /opt/ros/humble/setup.bash && source /home/ubuntu/airobot_ws/install/setup.bash && cd /home/ubuntu/throw_ws && colcon build --symlink-install 2>&1 | tail -5'
