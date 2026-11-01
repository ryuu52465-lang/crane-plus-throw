"""collect_dataで集めたCSVからThrowModelを学習し、モデルと学習結果のグラフを保存する.

使い方: train_model 入力CSV 出力モデル(.pt) [グラフ(.png)]
"""
import csv
import sys
from math import hypot

import torch

from crane_plus_throw.throw_model import ThrowModel

MIN_TOUCH_X = 0.05   # これより手前(後ろ)に落ちたのはつかみ損ね(外れ値)とみなす


def load_rows(path):
    used, dropped = [], 0
    with open(path) as f:
        for row in csv.DictReader(f):
            ok = row['touch_x'] and float(row['touch_x']) > MIN_TOUCH_X
            if not ok:
                dropped += 1
                continue
            used.append((float(row['swing_speed']),
                         hypot(float(row['touch_x']), float(row['touch_y']))))
    return used, dropped


def main():
    csv_path, model_path = sys.argv[1], sys.argv[2]
    plot_path = sys.argv[3] if len(sys.argv) > 3 else None
    rows, dropped = load_rows(csv_path)
    print(f'学習に使うデータ {len(rows)}件 (外れ値として除外 {dropped}件)')

    torch.manual_seed(0)
    x = torch.tensor([[r] for r, _ in rows])
    y = torch.tensor([[d] for _, d in rows])
    # 交差検証の代わりに、5件に1件を検証用に取っておく
    val = torch.arange(len(rows)) % 5 == 0
    model = ThrowModel()
    model.x_mean[:] = x.mean()
    model.x_std[:] = x.std()
    model.y_mean[:] = y.mean()
    model.y_std[:] = y.std()

    opt = torch.optim.Adam(model.parameters(), lr=1e-2)
    for epoch in range(2000):
        opt.zero_grad()
        loss = ((model(x[~val]) - y[~val]) ** 2).mean()
        loss.backward()
        opt.step()
    with torch.no_grad():
        train_err = (model(x[~val]) - y[~val]).abs().mean().item()
        val_err = (model(x[val]) - y[val]).abs().mean().item()
    print(f'平均誤差: 学習 {train_err * 100:.2f}cm / 検証 {val_err * 100:.2f}cm')
    print('届く距離: {:.3f}〜{:.3f} m'.format(*model.reachable()))

    torch.save(model.state_dict(), model_path)
    print(f'保存: {model_path}')

    if plot_path:
        import matplotlib
        matplotlib.use('Agg')
        import matplotlib.pyplot as plt
        grid = torch.linspace(x.min().item(), x.max().item(), 200).unsqueeze(1)
        with torch.no_grad():
            pred = model(grid)
        plt.figure(figsize=(6, 4))
        plt.scatter(x[~val].squeeze(), y[~val].squeeze() * 100, label='train', s=20)
        plt.scatter(x[val].squeeze(), y[val].squeeze() * 100, label='validation', s=20)
        plt.plot(grid.squeeze(), pred.squeeze() * 100, label='model', color='black')
        plt.xlabel('swing speed [rad/s]')
        plt.ylabel('landing distance [cm]')
        plt.legend()
        plt.grid(alpha=0.3)
        plt.tight_layout()
        plt.savefig(plot_path, dpi=120)
        print(f'グラフ: {plot_path}')


if __name__ == '__main__':
    main()
