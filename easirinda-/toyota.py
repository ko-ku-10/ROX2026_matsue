import time
import Hobot.GPIO as GPIO

# ピン番号の指定方法を「ボード上の物理ピン番号」に設定
GPIO.setmode(GPIO.BOARD)

# 使用する物理ピン番号（例: 12番ピン）
# ※ボードのピンアサインを確認し、安全なGPIOピンを指定してください
LED_PIN = 12  #12番ピンで設定したくせにGPIO18番ピンから出力されるよーーー

# ピンを出力モードに設定
GPIO.setup(LED_PIN, GPIO.OUT, initial=GPIO.LOW)

print("RDK X5 でLチカを開始します（Ctrl+Cで終了）")

try:
    while True:
        GPIO.output(LED_PIN, GPIO.HIGH)  # 点灯 (3.3V)
        time.sleep(1)
        
        GPIO.output(LED_PIN, GPIO.LOW)   # 消灯 (0V)
        time.sleep(1)

except KeyboardInterrupt:
    print("\n終了処理中...")

finally:
    # 使用したGPIOピンを解放（必須）
    GPIO.cleanup()
    print("Lチカを終了しました")