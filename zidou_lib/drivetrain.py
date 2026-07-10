"""メカナム動作ライブラリ。

このモジュールは、足回りの逆運動学と、AprilTag の位置から
自動追従用の速度指令を作る最小限のロジックをまとめています。
"""
from __future__ import annotations

from pathlib import Path
from typing import Sequence, Tuple
import json
import os
import time


WHEEL_NAMES = ("FL", "FR", "RL", "RR")

AUTO_NAV_TARGET_DISTANCE_M = max(0.05, float(os.getenv("AUTO_NAV_TARGET_DISTANCE_M", "0.35")))
AUTO_NAV_FORWARD_GAIN = max(0.0, float(os.getenv("AUTO_NAV_FORWARD_GAIN", "0.8")))
AUTO_NAV_ROTATE_GAIN = max(0.0, float(os.getenv("AUTO_NAV_ROTATE_GAIN", "0.8")))
AUTO_NAV_MAX_SPEED = max(0.0, min(1.0, float(os.getenv("AUTO_NAV_MAX_SPEED", "0.45"))))
AUTO_NAV_MAX_ROTATE = max(0.0, min(1.0, float(os.getenv("AUTO_NAV_MAX_ROTATE", "0.45"))))
TAG_POSE_FILE = Path(os.getenv("TAG_POSE_FILE", str(Path(__file__).with_name("tag_pose.json"))))
TAG_POSE_STALE_SEC = max(0.0, float(os.getenv("TAG_POSE_STALE_SEC", "0.25")))


def _clamp(value: float, low: float = -1.0, high: float = 1.0) -> float:
    return max(low, min(high, value))


def mecanum_ik(vx: float, vy: float, omega: float, L: float = 0.12, W: float = 0.10) -> Tuple[float, float, float, float]:
    """メカナムの逆運動学を返す。"""
    v_fl = vx - vy - omega * (L + W)
    v_fr = vx + vy + omega * (L + W)
    v_rl = vx + vy - omega * (L + W)
    v_rr = vx - vy + omega * (L + W)

    maxv = max(abs(v_fl), abs(v_fr), abs(v_rl), abs(v_rr), 1.0)
    return (v_fl / maxv, v_fr / maxv, v_rl / maxv, v_rr / maxv)


def blend_commands(a: Sequence[float], b: Sequence[float], alpha: float) -> Tuple[float, ...]:
    """2つのコマンドを線形ブレンドする。"""
    alpha = max(0.0, min(1.0, alpha))
    if len(a) != len(b):
        raise ValueError("length mismatch")
    return tuple((1.0 - alpha) * float(x) + alpha * float(y) for x, y in zip(a, b))


def read_latest_tag_pose(path: Path | None = None) -> dict[str, float] | None:
    """tag_pose.json 互換の単一タグ情報を読み取る。"""
    target_path = path or TAG_POSE_FILE
    if target_path is None or not target_path.exists():
        return None

    try:
        payload = json.loads(target_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None

    if not payload.get("detected", False):
        return None

    now = time.time()
    updated_at = float(payload.get("updated_at", 0.0))
    if TAG_POSE_STALE_SEC > 0.0 and (now - updated_at) > TAG_POSE_STALE_SEC:
        return None

    return {
        "id": payload.get("id"),
        "x": float(payload.get("x", 0.0)),
        "z": float(payload.get("z", 0.0)),
        "updated_at": updated_at,
    }


def best_tag_from_list(tags: Sequence[dict]) -> dict | None:
    """複数タグの候補から最短距離の 1 件を選ぶ。"""
    if not tags:
        return None
    return min(tags, key=lambda tag: float(tag.get("x", 0.0)) ** 2 + float(tag.get("z", 0.0)) ** 2)


class AutoNavigator:
    """タグ位置に向かうための単純な追従器。"""

    def __init__(self):
        self.target_distance_m = AUTO_NAV_TARGET_DISTANCE_M
        self.forward_gain = AUTO_NAV_FORWARD_GAIN
        self.rotate_gain = AUTO_NAV_ROTATE_GAIN
        self.max_speed = AUTO_NAV_MAX_SPEED
        self.max_rotate = AUTO_NAV_MAX_ROTATE

    def compute_cmd(self, x: float | None, z: float | None) -> tuple[float, float, float]:
        if x is None or z is None:
            return 0.0, 0.0, 0.0

        if abs(z) < 1e-4:
            vx = 0.0
        else:
            forward_error = self.target_distance_m - z
            vx = _clamp(forward_error * self.forward_gain, -self.max_speed, self.max_speed)
            if abs(forward_error) < 0.03:
                vx = 0.0

        omega = _clamp(x * self.rotate_gain, -self.max_rotate, self.max_rotate)
        if abs(x) < 0.03:
            omega = 0.0

        return vx, 0.0, omega
