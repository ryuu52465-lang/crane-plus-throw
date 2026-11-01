#!/bin/bash
# ボールを初期位置(ワールド座標)に戻す
# set_poseは位置しか変えず速度が残るため、ボールが止まってから戻し、戻した後も動かないことを確認する
X=${1:-0.05}
Y=${2:--0.13}
Z=${3:-1.035}

ball_pos() {
  timeout 5 ign model -m ball -p | grep -A1 XYZ | tail -1 | tr -d '[]'
}

wait_still() {
  for i in $(seq 1 20); do
    a=$(ball_pos); sleep 0.5; b=$(ball_pos)
    python3 -c "import sys; a=list(map(float,'$a'.split())); b=list(map(float,'$b'.split())); sys.exit(0 if max(abs(p-q) for p,q in zip(a,b)) < 0.001 else 1)" && return 0
  done
  echo 'ボールが止まらない' >&2
  return 1
}

# 手先に固定されたままだと戻せないので、先に解放する
ign topic -t /throw/detach -m ignition.msgs.Empty -p " "
for attempt in 1 2 3; do
  wait_still
  ign service -s /world/default/set_pose --reqtype ignition.msgs.Pose --reptype ignition.msgs.Boolean \
    --timeout 2000 --req "name: \"ball\", position: {x: $X, y: $Y, z: $Z}, orientation: {w: 1}" > /dev/null
  sleep 0.5
  if wait_still; then
    p=$(ball_pos)
    python3 -c "import sys; p=list(map(float,'$p'.split())); sys.exit(0 if abs(p[0]-$X)<0.005 and abs(p[1]-($Y))<0.005 else 1)" && exit 0
  fi
done
echo 'ボールを初期位置に戻せない' >&2
exit 1
