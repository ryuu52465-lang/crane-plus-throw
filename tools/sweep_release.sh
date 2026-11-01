#!/bin/bash
# 離す角度(release_joint2)を変えて投げ、着地位置を記録する
for r in "$@"; do
  echo "== release_joint2=$r"
  bash /home/ubuntu/throw_ws/tools/trace_ball.sh -p release_joint2:=$r | grep -vE "完了"
done
