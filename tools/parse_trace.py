"""ign topic -e の pose/info 出力から ball の (時刻, x, y, z) を抜き出して表示する."""
import re
import sys

text = open(sys.argv[1]).read()
rows = []
for msg in text.split('header {')[1:]:
    sec = re.search(r'sec: (\d+)', msg)
    nsec = re.search(r'nsec: (\d+)', msg)
    m = re.search(r'name: "ball".*?position \{(.*?)\}', msg, re.S)
    if not (sec and m):
        continue
    t = int(sec.group(1)) + (int(nsec.group(1)) if nsec else 0) * 1e-9
    pos = {k: float(v) for k, v in re.findall(r'(\w): ([-\d.e]+)', m.group(1))}
    rows.append((t, pos.get('x', 0.0), pos.get('y', 0.0), pos.get('z', 0.0)))

# 動いている区間だけを, 0.05秒ごとに間引いて表示
moving = [r for i, r in enumerate(rows)
          if i > 0 and any(abs(a - b) > 1e-4 for a, b in zip(r[1:], rows[i - 1][1:]))]
if not moving:
    print('ballは動いていない')
    sys.exit()
verbose = '-v' in sys.argv
t0 = moving[0][0]
last = -1.0
peak = max(rows, key=lambda r: r[3])
touchdown = None
for t, x, y, z in rows:
    if t < t0 - 0.1 or t > moving[-1][0] + 0.1:
        continue
    if verbose and t - last >= 0.05:
        print(f't={t - t0:6.2f}  x={x:+.3f} y={y:+.3f} z={z:.3f}')
        last = t
    # 最高点を過ぎてから机面(ボール中心1.035)付近まで下りた最初の点
    if touchdown is None and t > peak[0] and z < 1.045:
        touchdown = (x, y, z)
final = rows[-1]
if '--csv' in sys.argv:
    # 最高点z, 最初の着地x,y, 最終位置x,y (着地なしは空欄)
    tx, ty = (f'{touchdown[0]:.4f}', f'{touchdown[1]:.4f}') if touchdown else ('', '')
    print(f'{peak[3]:.4f},{tx},{ty},{final[1]:.4f},{final[2]:.4f}')
    sys.exit()
print(f'最高点 z={peak[3]:.3f}  最初の着地 x={touchdown[0]:+.3f} y={touchdown[1]:+.3f}'
      if touchdown else f'最高点 z={peak[3]:.3f}  着地なし(箱の中か机の外)')
print(f'最終位置 x={final[1]:+.3f} y={final[2]:+.3f} z={final[3]:.3f}')
