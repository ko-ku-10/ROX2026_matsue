"""足回り制御。

all_control.py の設定とセンサファイルを読んで、メカナムの移動指令を作ります。
必要なら AT フレームで実機にも送れます。
"""
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import argparse
import json
import math
import os
import time

try:
    import serial
except Exception:  # pragma: no cover - optional dependency
    serial = None

import all_control


AT_NEUTRAL_VALUE = 0x7FFF
AT_SPEED_PERCENT = max(0.0, min(100.0, float(os.getenv("AT_SPEED_PERCENT", "50"))))
AT_SPEED_SPAN = int(round(AT_NEUTRAL_VALUE * (AT_SPEED_PERCENT / 100.0)))


@dataclass(frozen=True)
class DriveCommand:
    vx: float
    vy: float
    omega: float

    def as_dict(self) -> dict[str, float]:
        return {"vx": self.vx, "vy": self.vy, "omega": self.omega}


def _clamp(value: float, low: float = -1.0, high: float = 1.0) -> float:
    return max(low, min(high, value))


def mecanum_ik(vx: float, vy: float, omega: float, wheel_base_half_l: float = 0.12, wheel_base_half_w: float = 0.10) -> tuple[float, float, float, float]:
    v_fl = vx - vy - omega * (wheel_base_half_l + wheel_base_half_w)
    v_fr = vx + vy + omega * (wheel_base_half_l + wheel_base_half_w)
    v_rl = vx + vy - omega * (wheel_base_half_l + wheel_base_half_w)
    v_rr = vx - vy + omega * (wheel_base_half_l + wheel_base_half_w)
    max_value = max(abs(v_fl), abs(v_fr), abs(v_rl), abs(v_rr), 1.0)
    return (v_fl / max_value, v_fr / max_value, v_rl / max_value, v_rr / max_value)


def _wrap_angle(angle: float) -> float:
    return math.atan2(math.sin(angle), math.cos(angle))


def compute_ball_command(ball_pose: dict[str, float]) -> DriveCommand:
    offset_x = float(ball_pose.get("offset_x", 0.0))
    radius = float(ball_pose.get("radius", 0.0))
    radius_error = all_control.BALL_TARGET_RADIUS_PX - radius
    vx = _clamp(radius_error * all_control.BALL_FORWARD_GAIN, -all_control.BALL_MAX_SPEED, all_control.BALL_MAX_SPEED)
    omega = _clamp(offset_x * all_control.BALL_ROTATE_GAIN, -all_control.BALL_MAX_ROTATE, all_control.BALL_MAX_ROTATE)
    if abs(radius_error) < 10.0:
        vx = 0.0
    if abs(offset_x) < 0.03:
        omega = 0.0
    return DriveCommand(vx=vx, vy=0.0, omega=omega)


def compute_tag_command(tag_pose: dict[str, float]) -> DriveCommand:
    x = float(tag_pose.get("x", 0.0))
    z = float(tag_pose.get("z", 0.0))
    if abs(z) < 1e-4:
        vx = 0.0
    else:
        forward_error = all_control.TAG_TARGET_DISTANCE_M - z
        vx = _clamp(forward_error * all_control.TAG_FORWARD_GAIN, -all_control.TAG_MAX_SPEED, all_control.TAG_MAX_SPEED)
        if abs(forward_error) < 0.03:
            vx = 0.0

    omega = _clamp(x * all_control.TAG_ROTATE_GAIN, -all_control.TAG_MAX_ROTATE, all_control.TAG_MAX_ROTATE)
    if abs(x) < 0.03:
        omega = 0.0
    return DriveCommand(vx=vx, vy=0.0, omega=omega)


def load_control_state(path: Path | None = None) -> dict | None:
    target_path = path or all_control.CONTROL_STATE_FILE
    return all_control.read_json_file(target_path)


def compute_drive_command(control_state: dict | None, tag_pose: dict[str, float] | None, ball_pose: dict[str, float] | None) -> DriveCommand:
    mode = (control_state or {}).get("selection", {}).get("mode") if control_state else None
    if mode == "ball" and ball_pose is not None:
        return compute_ball_command(ball_pose)
    if mode == "apriltag" and tag_pose is not None:
        return compute_tag_command(tag_pose)
    if ball_pose is not None:
        return compute_ball_command(ball_pose)
    if tag_pose is not None:
        return compute_tag_command(tag_pose)
    return DriveCommand(0.0, 0.0, 0.0)


def _normalized_to_at_value(normalized_speed: float) -> int:
    speed = _clamp(normalized_speed)
    delta = int(round(speed * AT_SPEED_SPAN))
    return max(0x0000, min(0xFFFF, AT_NEUTRAL_VALUE + delta))


def _build_enable_cmd(motor_addr: int) -> bytes:
    return bytes([
        0x41, 0x54, 0x20, 0x07, 0xE8, motor_addr,
        0x08, 0x00, 0xC4, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x0D, 0x0A,
    ])


def _build_velocity_cmd_value(motor_addr: int, at_value: int) -> bytes:
    value = max(0x0000, min(0xFFFF, int(at_value)))
    direction = 0x00 if value == AT_NEUTRAL_VALUE else 0x01
    return bytes([
        0x41, 0x54, 0x90, 0x07, 0xE8, motor_addr,
        0x08, 0x05, 0x70, 0x00, 0x00, 0x07, direction,
        (value >> 8) & 0xFF, value & 0xFF, 0x0D, 0x0A,
    ])


class SerialMotorDriver:
    def __init__(self, port: str, baudrate: int) -> None:
        if serial is None:
            raise RuntimeError("pyserial is not available")
        self.port = port
        self.baudrate = baudrate
        self._serial = serial.Serial(port=port, baudrate=baudrate, timeout=0.1)

    def enable(self) -> None:
        for motor_name, motor_addr in all_control.MOTOR_IDS.items():
            self._serial.write(_build_enable_cmd(motor_addr))
            self._serial.flush()
            print(f"[mecanum] enabled {motor_name}")

    def drive(self, command: DriveCommand) -> None:
        wheel_speeds = mecanum_ik(command.vx, command.vy, command.omega)
        for motor_name, speed in zip(all_control.MOTOR_IDS.keys(), wheel_speeds):
            motor_addr = all_control.MOTOR_IDS[motor_name]
            self._serial.write(_build_velocity_cmd_value(motor_addr, _normalized_to_at_value(speed)))
        self._serial.flush()

    def stop(self) -> None:
        self.drive(DriveCommand(0.0, 0.0, 0.0))

    def close(self) -> None:
        try:
            self._serial.close()
        except Exception:
            pass


def _write_drive_state(command: DriveCommand) -> None:
    all_control.write_json_file(all_control.DRIVE_COMMAND_FILE, {
        "updated_at": time.time(),
        **command.as_dict(),
    })


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="HONSEN ROX mecanum control")
    parser.add_argument("--once", action="store_true", help="compute one command and exit")
    parser.add_argument("--interval", type=float, default=1.0 / max(1, all_control.CONTROL_HZ), help="loop interval")
    args = parser.parse_args(argv)

    interval = max(0.02, float(args.interval))
    driver: SerialMotorDriver | None = None
    if all_control.SERIAL_ENABLE:
        try:
            driver = SerialMotorDriver(all_control.SERIAL_PORT, all_control.SERIAL_BAUD)
            driver.enable()
            print(f"[mecanum] serial ready on {all_control.SERIAL_PORT}")
        except Exception as exc:
            print(f"[mecanum] serial disabled: {exc}")
            driver = None

    try:
        while True:
            control_state = load_control_state()
            tag_pose = all_control.latest_tag_pose()
            ball_pose = all_control.latest_ball_pose()
            command = compute_drive_command(control_state, tag_pose, ball_pose)
            wheel_speeds = mecanum_ik(command.vx, command.vy, command.omega)
            _write_drive_state(command)
            print(
                f"[mecanum] mode={(control_state or {}).get('selection', {}).get('mode', 'idle')} "
                f"cmd={command.as_dict()} wheels={tuple(round(value, 3) for value in wheel_speeds)}"
            )
            if driver is not None:
                driver.drive(command)
            if args.once:
                break
            time.sleep(interval)
    except KeyboardInterrupt:
        print("[mecanum] stopped")
    finally:
        if driver is not None:
            try:
                driver.stop()
            finally:
                driver.close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
