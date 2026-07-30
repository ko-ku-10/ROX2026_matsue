"""AprilTag の認識と自己位置の近似出力。"""
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


DEFAULT_FOCAL_LENGTH = 960.0
DEFAULT_MARKER_LENGTH_M = 0.10


class TagDetector:
    def __init__(self, camera_index: int = 0, width: int = 1280, height: int = 720) -> None:
        if cv2 is None or np is None:
            raise RuntimeError("opencv-python is not available")
        if not hasattr(cv2, "aruco"):
            raise RuntimeError("cv2.aruco is not available")

        self.camera_index = camera_index
        self.width = width
        self.height = height
        self.marker_length = DEFAULT_MARKER_LENGTH_M
        self.camera_matrix = np.array(
            [
                [DEFAULT_FOCAL_LENGTH, 0, width / 2.0],
                [0, DEFAULT_FOCAL_LENGTH, height / 2.0],
                [0, 0, 1],
            ],
            dtype=np.float32,
        )
        self.dist_coeffs = np.zeros((5, 1), dtype=np.float32)
        self.detector = cv2.aruco.ArucoDetector(
            cv2.aruco.getPredefinedDictionary(cv2.aruco.DICT_APRILTAG_16h5),
            cv2.aruco.DetectorParameters(),
        )
        marker_half = self.marker_length / 2.0
        self._obj_points = np.array(
            [
                [-marker_half, marker_half, 0.0],
                [marker_half, marker_half, 0.0],
                [marker_half, -marker_half, 0.0],
                [-marker_half, -marker_half, 0.0],
            ],
            dtype=np.float32,
        )

    def detect(self, frame) -> dict | None:
        corners, ids, _ = self.detector.detectMarkers(frame)
        if ids is None:
            return None

        candidates: list[dict] = []
        for index in range(len(ids)):
            success, rvec, tvec = cv2.solvePnP(
                self._obj_points,
                corners[index][0],
                self.camera_matrix,
                self.dist_coeffs,
                flags=cv2.SOLVEPNP_ITERATIVE,
            )
            if not success:
                continue
            candidates.append(
                {
                    "id": int(ids[index][0]),
                    "rvec": [float(value) for value in rvec.flatten().tolist()],
                    "tvec": [float(value) for value in tvec.flatten().tolist()],
                    "x": float(tvec[0][0]),
                    "y": float(tvec[1][0]),
                    "z": float(tvec[2][0]),
                }
            )

        if not candidates:
            return None

        best_tag = min(candidates, key=lambda tag: float(tag.get("x", 0.0)) ** 2 + float(tag.get("z", 0.0)) ** 2)
        return {
            "detected": True,
            "id": best_tag["id"],
            "x": best_tag["x"],
            "y": best_tag["y"],
            "z": best_tag["z"],
            "updated_at": time.time(),
        }


def _write_tag_pose(payload: dict) -> None:
    all_control.write_json_file(all_control.TAG_POSE_FILE, payload)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="HONSEN ROX apriltag loop")
    parser.add_argument("--camera", type=int, default=all_control.APRILTAG_CAMERA_INDEX)
    parser.add_argument("--interval", type=float, default=1.0 / all_control.APRILTAG_FPS)
    args = parser.parse_args(argv)

    if cv2 is None or np is None or not hasattr(cv2, "aruco"):
        print("[apriltag] AprilTag 検出環境が無いため、待機状態で継続します")
        while True:
            _write_tag_pose({"detected": False, "updated_at": time.time()})
            time.sleep(max(0.2, float(args.interval)))

    detector = TagDetector(camera_index=args.camera)
    capture = cv2.VideoCapture(args.camera)
    capture.set(cv2.CAP_PROP_FRAME_WIDTH, detector.width)
    capture.set(cv2.CAP_PROP_FRAME_HEIGHT, detector.height)

    if not capture.isOpened():
        print(f"[apriltag] camera {args.camera} を開けませんでした。待機状態に入ります")
        while True:
            _write_tag_pose({"detected": False, "updated_at": time.time()})
            time.sleep(max(0.2, float(args.interval)))

    try:
        while True:
            success, frame = capture.read()
            if not success or frame is None:
                _write_tag_pose({"detected": False, "updated_at": time.time()})
                time.sleep(max(0.2, float(args.interval)))
                continue

            payload = detector.detect(frame)
            if payload is None:
                payload = {"detected": False, "updated_at": time.time()}
            _write_tag_pose(payload)
            print(f"[apriltag] detected={payload.get('detected')} id={payload.get('id')}")
            time.sleep(max(0.02, float(args.interval)))
    except KeyboardInterrupt:
        print("[apriltag] stopped")
    finally:
        capture.release()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
