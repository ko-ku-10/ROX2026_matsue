"""ボール位置の画像認識。

OpenCV が使える環境ではカメラ映像から色抽出してボール候補を探し、
ball_pose.json に結果を書き込みます。
"""
from __future__ import annotations

from pathlib import Path
import argparse
import time

try:
    import cv2
    import numpy as np
except Exception:  # pragma: no cover - optional dependency
    cv2 = None
    np = None

import all_control


class BallDetector:
    def __init__(self) -> None:
        if cv2 is None or np is None:
            raise RuntimeError("opencv-python is not available")
        self.lower = np.array(all_control.BALL_HSV_LOWER, dtype=np.uint8)
        self.upper = np.array(all_control.BALL_HSV_UPPER, dtype=np.uint8)

    def detect(self, frame) -> dict | None:
        hsv = cv2.cvtColor(frame, cv2.COLOR_BGR2HSV)
        mask = cv2.inRange(hsv, self.lower, self.upper)
        mask = cv2.medianBlur(mask, 5)
        contours, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        if not contours:
            return None

        contour = max(contours, key=cv2.contourArea)
        area = float(cv2.contourArea(contour))
        if area < all_control.BALL_MIN_AREA:
            return None

        (center_x, center_y), radius = cv2.minEnclosingCircle(contour)
        if radius <= 1.0:
            return None

        image_height, image_width = frame.shape[:2]
        offset_x = ((center_x - (image_width / 2.0)) / (image_width / 2.0)) if image_width else 0.0
        return {
            "detected": True,
            "x": float(center_x),
            "y": float(center_y),
            "radius": float(radius),
            "area": area,
            "offset_x": float(offset_x),
            "image_width": int(image_width),
            "image_height": int(image_height),
            "updated_at": time.time(),
        }


def _write_ball_pose(payload: dict) -> None:
    all_control.write_json_file(all_control.BALL_POSE_FILE, payload)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="HONSEN ROX vision loop")
    parser.add_argument("--camera", type=int, default=all_control.VISION_CAMERA_INDEX)
    parser.add_argument("--interval", type=float, default=1.0 / all_control.VISION_FPS)
    args = parser.parse_args(argv)

    if cv2 is None or np is None:
        print("[vision] OpenCV が使えないため、検出は待機状態で継続します")
        while True:
            _write_ball_pose({"detected": False, "updated_at": time.time()})
            time.sleep(max(0.2, float(args.interval)))

    detector = BallDetector()
    capture = cv2.VideoCapture(args.camera)
    capture.set(cv2.CAP_PROP_FRAME_WIDTH, 1280)
    capture.set(cv2.CAP_PROP_FRAME_HEIGHT, 720)

    if not capture.isOpened():
        print(f"[vision] camera {args.camera} を開けませんでした。待機状態に入ります")
        while True:
            _write_ball_pose({"detected": False, "updated_at": time.time()})
            time.sleep(max(0.2, float(args.interval)))

    try:
        while True:
            success, frame = capture.read()
            if not success or frame is None:
                _write_ball_pose({"detected": False, "updated_at": time.time()})
                time.sleep(max(0.2, float(args.interval)))
                continue

            payload = detector.detect(frame)
            if payload is None:
                payload = {"detected": False, "updated_at": time.time()}
            _write_ball_pose(payload)
            print(f"[vision] detected={payload.get('detected')} radius={payload.get('radius', 0.0):.1f}")
            time.sleep(max(0.02, float(args.interval)))
    except KeyboardInterrupt:
        print("[vision] stopped")
    finally:
        capture.release()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
