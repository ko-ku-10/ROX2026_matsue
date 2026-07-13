from evdev import InputDevice, ecodes, list_devices
from pathlib import Path
import Hobot.GPIO as GPIO

# コントローラーのイベントデバイス
# /dev/input/eventX は環境によって変わるため、自動検出します。

def find_gamepad():
    devices = []
    for path in list_devices():
        try:
            dev = InputDevice(path)
        except PermissionError:
            print(f'Permission denied: {path}')
            continue
        except FileNotFoundError:
            continue
        devices.append(dev)

    if not devices:
        print('evdev から入力デバイスを読み取れませんでした。')
        print('次を確認してください:')
        print('  1) /dev/input/event* にアクセスできるか')
        print('  2) sudo で実行するか、ユーザーを input グループに追加する')
        print('見つかった /dev/input/event* :')
        for p in sorted(Path('/dev/input').glob('event*')):
            print(f'  {p} {oct(p.stat().st_mode & 0o777)}')
        raise SystemExit('ゲームパッドが見つかりません。')

    gamepad = None
    for dev in devices:
        name = (dev.name or '').lower()
        if any(k in name for k in ['gamepad', 'controller', 'joystick', 'dualshock', 'xbox']):
            gamepad = dev
            break

    if gamepad is None:
        print('自動検出でゲームパッドが見つかりませんでした。')
        print('見つかった入力デバイス:')
        for dev in devices:
            print(f'  {dev.path}: {dev.name}')
        gamepad = devices[0]
        print(f'最初のデバイスを使用します: {gamepad.path} ({gamepad.name})')

    return gamepad

gamepad = find_gamepad()

# 電磁弁を接続したGPIO
VALVE_PIN = 27

GPIO.setmode(GPIO.BCM)
GPIO.setup(VALVE_PIN, GPIO.OUT)
GPIO.output(VALVE_PIN, GPIO.LOW)

print(f'使用するゲームパッド: {gamepad.path} ({gamepad.name})')
print('待機中... ○ボタンは BTN_SOUTH / BTN_EAST のどちらかです')

try:
    for event in gamepad.read_loop():
        if event.type == ecodes.EV_KEY:
            if event.code in (ecodes.BTN_SOUTH, ecodes.BTN_EAST):
                if event.value == 1:      # 押した
                    print("○ボタン ON")
                    GPIO.output(VALVE_PIN, GPIO.HIGH)
                elif event.value == 0:    # 離した
                    print("○ボタン OFF")
                    GPIO.output(VALVE_PIN, GPIO.LOW)
            elif event.value in (0, 1):
                print(f'KEY {event.code} value {event.value}')

except KeyboardInterrupt:
    pass
except OSError as exc:
    print(f'エラー: コントローラーの入力デバイスが切断されました: {exc}')
    print('コントローラーの接続状態を確認し、再度実行してください。')

GPIO.cleanup(VALVE_PIN)