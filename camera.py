import cv2
import numpy as np
import sys
import time
from flask import Flask, Response
# RDK X5の公式ライブラリ
from hobot_vio import libsrcampy

app = Flask(__name__)

# グローバルでカメラとディスプレイを初期化
cam_width = 1920
cam_height = 1080

disp = libsrcampy.Display()
disp.display(0, cam_width, cam_height)

cam = libsrcampy.Camera()
ret = cam.open_cam(0, -1, 30, 1920, 1080)
if ret:
    print("【エラー】カメラのオープンに失敗しました。")
    sys.exit(1)

libsrcampy.bind(cam, disp)
print("パイプラインの結合とカメラの初期化に成功しました。")

def generate_frames():
    while True:
        # 現像済み画像を取得
        nv12_data = cam.get_img(2)
        if nv12_data is None:
            time.sleep(0.03)  # 約30fpsを維持するための待機
            continue

        # バイナリデータをnumpy配列に変換
        yuv = np.frombuffer(nv12_data, dtype=np.uint8)
        
        # データサイズに応じて元サイズを特定
        if yuv.size == 3110400:
            current_w, current_h = 1920, 1080
        elif yuv.size == 4147200:
            current_w, current_h = 1920, 1440
        else:
            current_w = 640
            current_h = int((yuv.size / 1.5) / current_w)

        try:
            # NV12からBGRへ変換
            frame_raw = cv2.cvtColor(
                yuv.reshape((int(current_h * 1.5), current_w)), 
                cv2.COLOR_YUV2BGR_NV12
            )
            
            # --- 【軽量化ポイント1】配信サイズを小さくする (例: 480x270) ---
            # 解像度を大幅に下げることで、ネットワーク転送量と変換負荷を減らし動きを良くします
            stream_w, stream_h = 480, 270
            frame = cv2.resize(frame_raw, (stream_w, stream_h))

            # --- 【軽量化ポイント2】JPEGの品質（画質）を下げて圧縮する ---
            # [cv2.IMWRITE_JPEG_QUALITY, 40] で画質を40%に落として軽量化（標準は95）
            encode_param = [int(cv2.IMWRITE_JPEG_QUALITY), 40]
            ret, buffer = cv2.imencode('.jpg', frame, encode_param)
            
            if not ret:
                continue
                
            # バイナリデータに変換
            frame_bytes = buffer.tobytes()
            
            # MJPEG形式のフレームとして出力
            yield (b'--frame\r\n'
                   b'Content-Type: image/jpeg\r\n\r\n' + frame_bytes + b'\r\n')
                   
        except Exception as e:
            print(f"フレーム処理エラー: {e}")
            
        # 配信のループスピードを調整 (約30fps)
        time.sleep(0.03)

@app.route('/')
def index():
    # ブラウザに直接映像を表示するためのHTML
    return '''
    <html>
      <head>
        <title>RDK X5 Live Stream</title>
        <style>
          body { margin: 0; background-color: #333; display: flex; justify-content: center; align-items: center; height: 100vh; color: white; font-family: sans-serif; }
          .container { text-align: center; }
          img { border: 2px solid #fff; max-width: 100%; height: auto; }
        </style>
      </head>
      <body>
        <div class="container">
          <h1>RDK X5 リアルタイム映像</h1>
          <img src="/video_feed" />
        </div>
      </body>
    </html>
    '''

@app.route('/video_feed')
def video_feed():
    # MJPEGストリーミングのレスポンスを返す
    return Response(generate_frames(),
                    mimetype='multipart/x-mixed-replace; boundary=frame')

if __name__ == '__main__':
    try:
        # host='0.0.0.0' で同一ネットワーク内の他PCからのアクセスを許可
        # port=5000 で待ち受け
        app.run(host='0.0.0.0', port=5000, threaded=True)
    finally:
        print("\nリソースを解放中...")
        libsrcampy.unbind(cam, disp)
        disp.close()
        cam.close_cam()
        print("終了しました。")