#!/bin/bash
# 的の箱をワールド座標(x, y)へ動かす
ign service -s /world/default/set_pose --reqtype ignition.msgs.Pose --reptype ignition.msgs.Boolean \
  --timeout 2000 --req "name: \"target_box\", position: {x: $1, y: $2, z: 1.015}, orientation: {w: 1}"
