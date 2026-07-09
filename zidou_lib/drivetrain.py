"""メカナム足回りユーティリティ

関数:
- mecanum_ik(vx, vy, omega, L, W): 4輪の速度（正規化）を返す
- blend_commands(cmd_a, cmd_b, alpha): 2つのコマンドを線形ブレンド
"""
from __future__ import annotations

from typing import Tuple, Sequence
import math


def mecanum_ik(vx: float, vy: float, omega: float, L: float = 0.12, W: float = 0.10) -> Tuple[float, float, float, float]:
    """メカナムの逆運動学。

    入力: 前方vx, 右方向vy, 回転omega（正負は呼び手で揃えてください）。
    出力: (v_fl, v_fr, v_rl, v_rr) 正規化されたホイール速度（最大絶対値が1になるよう正規化）。
    """
    # 基本式（ROX の実装に合わせる）
    v_fl = vx - vy - omega * (L + W)
    v_fr = vx + vy + omega * (L + W)
    v_rl = vx + vy - omega * (L + W)
    v_rr = vx - vy + omega * (L + W)

    maxv = max(abs(v_fl), abs(v_fr), abs(v_rl), abs(v_rr), 1.0)
    return (v_fl / maxv, v_fr / maxv, v_rl / maxv, v_rr / maxv)


def blend_commands(a: Sequence[float], b: Sequence[float], alpha: float) -> Tuple[float, ...]:
    """2つのコマンドを線形ブレンドする。alpha=0 -> a, alpha=1 -> b"""
    alpha = max(0.0, min(1.0, alpha))
    if len(a) != len(b):
        raise ValueError("length mismatch")
    return tuple((1.0 - alpha) * float(x) + alpha * float(y) for x, y in zip(a, b))
