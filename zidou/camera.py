import json
import sys
import time
import threading
from pathlib import Path

import cv2
import numpy as np
from flask import Flask, Response

try:
    # RDK X5 公式カメラライブラリ
    from hobot_vio import libsrcampy
except Exception:  # pragma: no cover - runtime environment may not have the SDK
    libsrcampy = None

app = Flask(__name__)

# --- AprilTag / カメラ設定 ---
MARKER_LENGTH = 0.10  # メートル（17cm）
focal_length = 960.0  # 調整済みの焦点距離

cam_width = 1920
cam_height = 1080

camera_matrix = np.array([
    [focal_length, 0, cam_width / 2],
    [0, focal_length, cam_height / 2],
    [0, 0, 1]
], dtype=np.float32)
dist_coeffs = np.zeros((5, 1), dtype=np.float32)

obj_points = np.array([
    [-MARKER_LENGTH / 2,  MARKER_LENGTH / 2, 0],
    [ MARKER_LENGTH / 2,  MARKER_LENGTH / 2, 0],
    [ MARKER_LENGTH / 2, -MARKER_LENGTH / 2, 0],
    [-MARKER_LENGTH / 2, -MARKER_LENGTH / 2, 0]
], dtype=np.float32)

detector = cv2.aruco.ArucoDetector(
    cv2.aruco.getPredefinedDictionary(cv2.aruco.DICT_APRILTAG_16h5),
    cv2.aruco.DetectorParameters()
)

# 配信用の画像バイトデータとスレッドセーフのためのロック
latest_map_bytes = None
latest_video_bytes = None
latest_pose = {"detected": False, "id": None, "x": 0.0, "z": 0.0, "updated_at": 0.0}
frame_lock = threading.Lock()
TAG_POSE_FILE = Path(__file__).with_name("tag_pose.json")

# --- カメラ初期化 ---
if libsrcampy is None:
    print("[WARN] hobot_vio が見つからないため、カメラ入力は無効化します。")
    disp = None
    cam = None
else:
    disp = libsrcampy.Display()
    disp.display(0, cam_width, cam_height)
    cam = libsrcampy.Camera()
    if cam.open_cam(0, -1, 30, cam_width, cam_height):
        print("カメラオープン失敗")
        sys.exit(1)
    libsrcampy.bind(cam, disp)


# --- 2D疑似マップを描画する関数 ---
def draw_radar_map(detected_tags):
    # 500x500ピクセルの黒いマップ土台
    map_img = np.zeros((500, 500, 3), dtype=np.uint8)
    
    # ロボット（自分）の位置を下側中央に固定
    robot_pos = (250, 450)
    cv2.circle(map_img, robot_pos, 8, (0, 0, 255), -1) 
    cv2.putText(map_img, "ROBOT", (225, 480), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 0, 255), 1)

    # 距離の目安となる同心円（1m, 2m, 3m）
    scale = 1.5
    cv2.circle(map_img, robot_pos, int(100 * scale), (40, 40, 40), 1)  
    cv2.circle(map_img, robot_pos, int(200 * scale), (40, 40, 40), 1)  
    cv2.circle(map_img, robot_pos, int(300 * scale), (40, 40, 40), 1)  

    # 見つかったすべてのタグをループ処理でひとつずつ描画
    for tag in detected_tags:
        tag_x = tag['x']
        tag_z = tag['z']
        tag_id = tag['id']

        # カメラ座標系からマップのピクセル座標へ変換
        map_x = int(robot_pos[0] + (tag_x * 100 * scale))
        map_y = int(robot_pos[1] - (tag_z * 100 * scale))

        # マップの範囲内（500x500）に収まっている場合だけ描画
        if 0 <= map_x < 500 and 0 <= map_y < 500:
            cv2.circle(map_img, (map_x, map_y), 10, (0, 255, 0), -1)
            
            # 直線距離を計算
            dist_cm = np.sqrt(tag_x**2 + tag_z**2) * 100
            cv2.putText(map_img, f"ID:{tag_id} ({dist_cm:.1f}cm)", (map_x + 15, map_y + 5), 
                        cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 0), 1)
            
            # ロボットから各タグへの線を結ぶ
            cv2.line(map_img, robot_pos, (map_x, map_y), (0, 100, 0), 1)

    return map_img


# --- バックグラウンド・カメラ処理スレッド ---
def camera_worker():
    global latest_map_bytes, latest_video_bytes, latest_pose
    while True:
        if cam is None:
            time.sleep(0.1)
            continue

        nv12_data = cam.get_img(2)
        if nv12_data is None:
            time.sleep(0.005)
            continue

        try:
            # バイナリデータをnumpy配列に変換
            yuv = np.frombuffer(nv12_data, dtype=np.uint8)
            current_h = cam_height if yuv.size == 3110400 else int((yuv.size / 1.5) / cam_width)
            frame_raw = cv2.cvtColor(yuv.reshape((int(current_h * 1.5), cam_width)), cv2.COLOR_YUV2BGR_NV12)

            # AprilTagの検出
            corners, ids, rejected = detector.detectMarkers(frame_raw)

            # 今回見つかったすべてのタグ情報を格納する空リスト
            detected_tags = []

            if ids is not None:
                # 検出されたタグの枠線をライブ映像用フレームに描画
                cv2.aruco.drawDetectedMarkers(frame_raw, corners, ids)
                
                # 見つかった個数分だけループを回して位置計算
                for i in range(len(ids)):
                    success, rvec, tvec = cv2.solvePnP(
                        obj_points, corners[i][0], camera_matrix, dist_coeffs, flags=cv2.SOLVEPNP_ITERATIVE
                    )
                    if success:
                        tag_data = {
                            'id': ids[i][0],
                            'x': tvec[0][0],
                            'z': tvec[2][0]
                        }
                        detected_tags.append(tag_data)

            best_tag = None
            if detected_tags:
                best_tag = min(detected_tags, key=lambda tag: tag["x"] ** 2 + tag["z"] ** 2)

            latest_pose = {
                "detected": best_tag is not None,
                "id": int(best_tag["id"]) if best_tag else None,
                "x": float(best_tag["x"]) if best_tag else 0.0,
                "z": float(best_tag["z"]) if best_tag else 0.0,
                "updated_at": time.time(),
            }
            try:
                TAG_POSE_FILE.write_text(json.dumps(latest_pose), encoding="utf-8")
            except OSError as exc:
                print(f"[WARN] tag pose の保存に失敗しました: {exc}")

            # 1. レーダーマップの生成とエンコード
            map_image = draw_radar_map(detected_tags)
            ret_map, map_buffer = cv2.imencode('.jpg', map_image)

            # 2. ライブ映像の軽量化（サイズ縮小 480x270 ＋ JPEGクオリティ 40）
            stream_w, stream_h = 480, 270
            frame_resized = cv2.resize(frame_raw, (stream_w, stream_h))
            encode_param = [int(cv2.IMWRITE_JPEG_QUALITY), 40]
            ret_video, video_buffer = cv2.imencode('.jpg', frame_resized, encode_param)

            # データの安全な更新
            with frame_lock:
                if ret_map:
                    latest_map_bytes = map_buffer.tobytes()
                if ret_video:
                    latest_video_bytes = video_buffer.tobytes()

        except Exception as e:
            print(f"フレーム処理エラー: {e}")
            pass
        time.sleep(0.01)

# スレッドの開始
t = threading.Thread(target=camera_worker, daemon=True)
t.start()


# --- Flask配信セクション ---
def generate_map_frames():
    while True:
        with frame_lock:
            frame_bytes = latest_map_bytes
        if frame_bytes is not None:
            yield (b'--frame\r\n'
                   b'Content-Type: image/jpeg\r\n\r\n' + frame_bytes + b'\r\n')
        time.sleep(0.04)

def generate_video_frames():
    while True:
        with frame_lock:
            frame_bytes = latest_video_bytes
        if frame_bytes is not None:
            yield (b'--frame\r\n'
                   b'Content-Type: image/jpeg\r\n\r\n' + frame_bytes + b'\r\n')
        time.sleep(0.03) # 約30fps

@app.route('/map_feed')
def map_feed():
    return Response(generate_map_frames(), mimetype='multipart/x-mixed-replace; boundary=frame')

@app.route('/video_feed')
def video_feed():
    return Response(generate_video_frames(), mimetype='multipart/x-mixed-replace; boundary=frame')

@app.route('/')
def index():
    # レーダーとカメラ映像をサイバー風のデザインで横並び（レスポンシブ）に配置
    return """
    <html>
    <head>
        <title>RDK X5 - Radar & Live Stream</title>
        <style>
            body { margin:0; background:#0a0d14; display:flex; flex-direction:column; justify-content:center; align-items:center; min-height:100vh; font-family:sans-serif; color:#00ff66; }
            h1 { font-size: 22px; letter-spacing: 2px; margin-bottom: 20px; text-transform: uppercase; }
            .container { display: flex; flex-wrap: wrap; justify-content: center; gap: 30px; padding: 20px; }
            .card { text-align: center; }
            .card h2 { font-size: 14px; color: #88aaff; letter-spacing: 1px; margin-bottom: 10px; }
            .radar-screen { border: 2px solid #00ff66; border-radius: 50%; overflow: hidden; box-shadow: 0 0 20px rgba(0,255,102,0.2); width:500px; height:500px; background:#000; }
            .video-screen { border: 2px solid #00ff66; overflow: hidden; box-shadow: 0 0 20px rgba(0,255,102,0.2); width:480px; height:270px; background:#000; display: flex; align-items: center; }
            img { width:100%; height:100%; object-fit: contain; }
        </style>
    </head>
    <body>
        <h1>RDK X5 Tactical HUD</h1>
        <div class="container">
            <div class="card">
                <h2>2D TARGET RADAR</h2>
                <div class="radar-screen">
                    <img src="/map_feed">
                </div>
            </div>
            <div class="card">
                <h2>LIVE CAMERA STREAM</h2>
                <div class="video-screen">
                    <img src="/video_feed">
                </div>
            </div>
        </div>
    </body>
    </html>
    """

if __name__ == "__main__":
    try:
        app.run(host='0.0.0.0', port=5000, debug=False, threaded=True)
    finally:
        print("\nリソースを解放中...")
        libsrcampy.unbind(cam, disp)
        disp.close()
        cam.close_cam()
        print("終了しました。")