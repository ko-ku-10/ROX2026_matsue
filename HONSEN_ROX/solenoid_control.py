"""ソレノイド制御。"""
from __future__ import annotations

from pathlib import Path
import argparse
import time

try:
    from evdev import InputDevice, ecodes, list_devices
except Exception:  # pragma: no cover - optional dependency
    InputDevice = None
    ecodes = None

    def list_devices() -> list[str]:
        return []

try:
    import Hobot.GPIO as GPIO
except Exception:  # pragma: no cover - optional dependency
    GPIO = None

import all_control


def find_gamepad() -> object | None:
    if InputDevice is None:
        return None

    for path in list_devices():
        try:
            device = InputDevice(path)
        except Exception:
            continue
        name = (device.name or "").lower()
        if any(keyword in name for keyword in ("gamepad", "controller", "joystick", "dualshock", "xbox")):
            return device
    return None


def _setup_gpio() -> None:
    if GPIO is None:
        raise RuntimeError("Hobot.GPIO is not available")
    mode_name = all_control.SOLENOID_GPIO_MODE
    if mode_name == "BOARD":
        GPIO.setmode(GPIO.BOARD)
    else:
        GPIO.setmode(GPIO.BCM)
    GPIO.setup(all_control.SOLENOID_PIN, GPIO.OUT, initial=GPIO.LOW)


def _set_solenoid(active: bool) -> None:
    if GPIO is None:
        return
    output_high = active if all_control.SOLENOID_ACTIVE_HIGH else not active
    GPIO.output(all_control.SOLENOID_PIN, GPIO.HIGH if output_high else GPIO.LOW)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="HONSEN ROX solenoid control")
    parser.add_argument("--button", default="BTN_SOUTH", help="gamepad button name to drive the solenoid")
    args = parser.parse_args(argv)

    if GPIO is None:
        print("[solenoid] GPIO が使えないため待機状態で継続します")
        while True:
            time.sleep(1.0)

    _setup_gpio()
    gamepad = find_gamepad()
    if gamepad is None:
        print("[solenoid] gamepad が見つかりません。待機状態で継続します")
        try:
            while True:
                time.sleep(1.0)
        finally:
            GPIO.cleanup()

    button_code = getattr(ecodes, args.button, ecodes.BTN_SOUTH if ecodes is not None else 304)
    print(f"[solenoid] device={gamepad.path} name={gamepad.name} pin={all_control.SOLENOID_PIN}")
    try:
        for event in gamepad.read_loop():
            if event.type != ecodes.EV_KEY:
                continue
            if event.code == button_code:
                _set_solenoid(event.value == 1)
                state = "ON" if event.value == 1 else "OFF"
                print(f"[solenoid] {state}")
    except KeyboardInterrupt:
        print("[solenoid] stopped")
    finally:
        _set_solenoid(False)
        GPIO.cleanup()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
