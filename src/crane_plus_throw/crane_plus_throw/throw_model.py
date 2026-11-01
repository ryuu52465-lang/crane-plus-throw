"""試投データから学習する「振る速さ → 着地距離」の順モデル.

小さなMLPで順モデルを学習し、狙う距離に対しては振る速さを総当たりして逆算する.
"""
import torch
from torch import nn

SPEED_RANGE = (0.8, 2.0)      # [rad/s] 学習データを集めた範囲。この外は外挿になるので使わない


class ThrowModel(nn.Module):

    def __init__(self):
        super().__init__()
        self.net = nn.Sequential(
            nn.Linear(1, 16), nn.Tanh(),
            nn.Linear(16, 16), nn.Tanh(),
            nn.Linear(16, 1))
        # 入出力の正規化(学習時に決める)
        self.register_buffer('x_mean', torch.zeros(1))
        self.register_buffer('x_std', torch.ones(1))
        self.register_buffer('y_mean', torch.zeros(1))
        self.register_buffer('y_std', torch.ones(1))

    def forward(self, speed):
        x = (speed - self.x_mean) / self.x_std
        return self.net(x) * self.y_std + self.y_mean

    @torch.no_grad()
    def predict(self, speed):
        """振る速さ[rad/s] → 着地距離[m]."""
        return float(self(torch.tensor([[float(speed)]])))

    @torch.no_grad()
    def speed_for(self, distance):
        """着地距離distance[m]に最も近くなる振る速さと、その予測距離を返す."""
        cand = torch.linspace(*SPEED_RANGE, 801).unsqueeze(1)
        pred = self(cand).squeeze(1)
        i = int(torch.argmin((pred - distance).abs()))
        return float(cand[i]), float(pred[i])

    def reachable(self):
        """学習範囲で届く着地距離の(最小, 最大)."""
        with torch.no_grad():
            pred = self(torch.linspace(*SPEED_RANGE, 801).unsqueeze(1))
        return float(pred.min()), float(pred.max())


def load(path):
    model = ThrowModel()
    model.load_state_dict(torch.load(path))
    model.eval()
    return model
