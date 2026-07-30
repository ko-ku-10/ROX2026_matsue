"""HONSEN ROX の中央設定と座標管理。

このファイルだけを編集すれば、フィールド配置、タグ座標、
ボール追従のしきい値、ソレノイドのピン設定をまとめて変更できます。
"""
from __future__ import annotations

from dataclasses import asdict, dataclass
from pathlib import Path
import argparse
import json
import os
import time


ROOT = Path(__file__).resolve().parent


def _env_flag(name: str, default: str = "0") -> bool:
    value = os.getenv(name, default).strip().lower()
    return value in {"1", "true", "yes", "on", "y"}


@dataclass(frozen=True)
class Pose2D:
    x: float
    y: float
    theta: float = 0.0

    def as_dict(self) -> dict[str, float]:
        return {"x": self.x, "y": self.y, "theta": self.theta}


TAG_POSE_FILE = Path(os.getenv("TAG_POSE_FILE", str(ROOT / "tag_pose.json")))
BALL_POSE_FILE = Path(os.getenv("BALL_POSE_FILE", str(ROOT / "ball_pose.json")))
CONTROL_STATE_FILE = Path(os.getenv("CONTROL_STATE_FILE", str(ROOT / "control_state.json")))
DRIVE_COMMAND_FILE = Path(os.getenv("DRIVE_COMMAND_FILE", str(ROOT / "drive_command.json")))

VISION_CAMERA_INDEX = int(os.getenv("VISION_CAMERA_INDEX", "0"))
APRILTAG_CAMERA_INDEX = int(os.getenv("APRILTAG_CAMERA_INDEX", "0"))
VISION_FPS = max(1.0, float(os.getenv("VISION_FPS", "15")))
APRILTAG_FPS = max(1.0, float(os.getenv("APRILTAG_FPS", "15")))

FIELD_WIDTH_M = float(os.getenv("FIELD_WIDTH_M", "6.0"))
FIELD_HEIGHT_M = float(os.getenv("FIELD_HEIGHT_M", "4.0"))

HOME_POSE = Pose2D(float(os.getenv("HOME_X", "0.40")), float(os.getenv("HOME_Y", "0.55")), 0.0)
SEARCH_POSE = Pose2D(float(os.getenv("SEARCH_X", "1.20")), float(os.getenv("SEARCH_Y", "1.20")), 0.0)
BALL_APPROACH_POSE = Pose2D(float(os.getenv("BALL_APPROACH_X", "1.80")), float(os.getenv("BALL_APPROACH_Y", "1.05")), 0.0)
GOAL_POSE = Pose2D(float(os.getenv("GOAL_X", "4.75")), float(os.getenv("GOAL_Y", "0.55")), 0.0)
TAG_STANDOFF_POSE = Pose2D(float(os.getenv("TAG_STANDOFF_X", "0.90")), float(os.getenv("TAG_STANDOFF_Y", "0.55")), 0.0)

APRILTAG_TARGETS: dict[int, Pose2D] = {
    1: Pose2D(0.90, 0.55, 0.0),
    2: Pose2D(2.20, 0.55, 0.0),
    3: Pose2D(3.50, 0.55, 0.0),
    4: Pose2D(4.80, 0.55, 0.0),
}

BALL_HSV_LOWER = tuple(int(v) for v in os.getenv("BALL_HSV_LOWER", "5,80,80").split(","))
BALL_HSV_UPPER = tuple(int(v) for v in os.getenv("BALL_HSV_UPPER", "30,255,255").split(","))
BALL_MIN_AREA = max(0.0, float(os.getenv("BALL_MIN_AREA", "300.0")))
BALL_TARGET_RADIUS_PX = max(1.0, float(os.getenv("BALL_TARGET_RADIUS_PX", "90.0")))
BALL_MAX_SPEED = max(0.0, min(1.0, float(os.getenv("BALL_MAX_SPEED", "0.40"))))
BALL_MAX_ROTATE = max(0.0, min(1.0, float(os.getenv("BALL_MAX_ROTATE", "0.45"))))
BALL_FORWARD_GAIN = max(0.0, float(os.getenv("BALL_FORWARD_GAIN", "0.010")))
BALL_ROTATE_GAIN = max(0.0, float(os.getenv("BALL_ROTATE_GAIN", "0.60")))

TAG_TARGET_DISTANCE_M = max(0.05, float(os.getenv("TAG_TARGET_DISTANCE_M", "0.35")))
TAG_FORWARD_GAIN = max(0.0, float(os.getenv("TAG_FORWARD_GAIN", "0.80")))
TAG_ROTATE_GAIN = max(0.0, float(os.getenv("TAG_ROTATE_GAIN", "0.80")))
TAG_MAX_SPEED = max(0.0, min(1.0, float(os.getenv("TAG_MAX_SPEED", "0.45"))))
TAG_MAX_ROTATE = max(0.0, min(1.0, float(os.getenv("TAG_MAX_ROTATE", "0.45"))))
TAG_POSE_STALE_SEC = max(0.0, float(os.getenv("TAG_POSE_STALE_SEC", "0.25")))

MOTOR_IDS = {
    "FL": int(os.getenv("MOTOR_ID_FL", "0x0C"), 0),
    "FR": int(os.getenv("MOTOR_ID_FR", "0x14"), 0),
    "RL": int(os.getenv("MOTOR_ID_RL", "0x1C"), 0),
    "RR": int(os.getenv("MOTOR_ID_RR", "0x24"), 0),
}

SERIAL_PORT = os.getenv("SERIAL_PORT", "/dev/ttyUSB0").strip()
SERIAL_BAUD = int(os.getenv("SERIAL_BAUD", "921600"))
SERIAL_ENABLE = _env_flag("SERIAL_ENABLE", "0")
SERIAL_WRITE_INTERVAL = float(os.getenv("SERIAL_WRITE_INTERVAL", "0.02"))
CONTROL_HZ = int(os.getenv("CONTROL_HZ", "20"))

SOLENOID_PIN = int(os.getenv("SOLENOID_PIN", "12"))
SOLENOID_GPIO_MODE = os.getenv("SOLENOID_GPIO_MODE", "BOARD").strip().upper()
SOLENOID_ACTIVE_HIGH = _env_flag("SOLENOID_ACTIVE_HIGH", "1")

STATE_REFRESH_SEC = max(0.1, float(os.getenv("STATE_REFRESH_SEC", "0.25")))


def clamp(value: float, low: float, high: float) -> float:
    return max(low, min(high, value))


def pose_to_dict(pose: Pose2D | None) -> dict[str, float] | None:
    return pose.as_dict() if pose is not None else None


def read_json_file(path: Path) -> dict | None:
    if not path.exists():
        return None
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None


def write_json_file(path: Path, payload: dict) -> None:
    try:
        path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    except OSError:
        pass


def latest_tag_pose(path: Path | None = None) -> dict[str, float] | None:
    target_path = path or TAG_POSE_FILE
    payload = read_json_file(target_path)
    if not payload or not payload.get("detected", False):
        return None

    updated_at = float(payload.get("updated_at", 0.0))
    if TAG_POSE_STALE_SEC > 0.0 and (time.time() - updated_at) > TAG_POSE_STALE_SEC:
        return None

    return {
        "id": float(payload.get("id", 0.0)) if payload.get("id") is not None else None,
        "x": float(payload.get("x", 0.0)),
        "z": float(payload.get("z", 0.0)),
        "updated_at": updated_at,
    }


def latest_ball_pose(path: Path | None = None) -> dict[str, float] | None:
    target_path = path or BALL_POSE_FILE
    payload = read_json_file(target_path)
    if not payload or not payload.get("detected", False):
        return None
    return {
        "x": float(payload.get("x", 0.0)),
        "y": float(payload.get("y", 0.0)),
        "radius": float(payload.get("radius", 0.0)),
        "offset_x": float(payload.get("offset_x", 0.0)),
        "updated_at": float(payload.get("updated_at", 0.0)),
    }


def select_target(tag_pose: dict[str, float] | None, ball_pose: dict[str, float] | None) -> dict:
    if ball_pose is not None:
        return {
            "mode": "ball",
            "name": "ball_approach",
            "target": pose_to_dict(BALL_APPROACH_POSE),
            "source": "vision",
        }

    if tag_pose is not None:
        tag_id = int(tag_pose.get("id", 0) or 0)
        target_pose = APRILTAG_TARGETS.get(tag_id, TAG_STANDOFF_POSE)
        return {
            "mode": "apriltag",
            "name": f"tag_{tag_id}" if tag_id else "tag_default",
            "target": pose_to_dict(target_pose),
            "source": "apriltag",
        }

    return {
        "mode": "idle",
        "name": "search",
        "target": pose_to_dict(SEARCH_POSE),
        "source": "default",
    }


def build_state_snapshot() -> dict:
    tag_pose = latest_tag_pose()
    ball_pose = latest_ball_pose()
    selection = select_target(tag_pose, ball_pose)
    return {
        "updated_at": time.time(),
        "field": {
            "width_m": FIELD_WIDTH_M,
            "height_m": FIELD_HEIGHT_M,
            "home": pose_to_dict(HOME_POSE),
            "search": pose_to_dict(SEARCH_POSE),
            "ball_approach": pose_to_dict(BALL_APPROACH_POSE),
            "goal": pose_to_dict(GOAL_POSE),
            "tag_standoff": pose_to_dict(TAG_STANDOFF_POSE),
            "apriltag_targets": {str(key): pose_to_dict(value) for key, value in APRILTAG_TARGETS.items()},
        },
        "sensors": {
            "tag_pose": tag_pose,
            "ball_pose": ball_pose,
        },
        "selection": selection,
        "hardware": {
            "serial_port": SERIAL_PORT,
            "serial_baud": SERIAL_BAUD,
            "motor_ids": MOTOR_IDS,
            "solenoid_pin": SOLENOID_PIN,
            "solenoid_gpio_mode": SOLENOID_GPIO_MODE,
        },
    }


def refresh_state() -> dict:
    snapshot = build_state_snapshot()
    write_json_file(CONTROL_STATE_FILE, snapshot)
    return snapshot


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="HONSEN ROX central control/config loop")
    parser.add_argument("--once", action="store_true", help="write the state file once and exit")
    parser.add_argument("--interval", type=float, default=STATE_REFRESH_SEC, help="refresh interval in seconds")
    args = parser.parse_args(argv)

    if args.once:
        snapshot = refresh_state()
        print(json.dumps(snapshot, ensure_ascii=False, indent=2))
        return 0

    interval = max(0.1, float(args.interval))
    print(f"[all_control] state file: {CONTROL_STATE_FILE}")
    print("[all_control] running; edit all_control.py to change field layout and mission policy")

    try:
        while True:
            snapshot = refresh_state()
            selection = snapshot.get("selection", {})
            print(f"[all_control] mode={selection.get('mode')} target={selection.get('name')}")
            time.sleep(interval)
    except KeyboardInterrupt:
        print("[all_control] stopped")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
