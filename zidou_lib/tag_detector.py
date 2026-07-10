"""AprilTag 読み取りライブラリ。

カメラから AprilTag を継続的に検出し、最新のタグ一覧と
既存コード互換の単一 pose JSON を取り出せるようにします。
"""
from __future__ import annotations

from pathlib import Path
from typing import Optional
import json
import threading
import time

import cv2
import numpy as np

try:
    from hobot_vio import libsrcampy
except Exception:  # pragma: no cover - SDK is optional in development environments
    libsrcampy = None


DEFAULT_WIDTH = 1920
DEFAULT_HEIGHT = 1080
DEFAULT_MARKER_LENGTH_M = 0.10
DEFAULT_FOCAL_LENGTH = 960.0


class TagDetector:
    """AprilTag を背景スレッドで検出する。"""

    def __init__(
        self,
        camera_index: int = 0,
        width: int = DEFAULT_WIDTH,
        height: int = DEFAULT_HEIGHT,
        marker_length_m: float = DEFAULT_MARKER_LENGTH_M,
        camera_matrix: Optional[np.ndarray] = None,
        dist_coeffs: Optional[np.ndarray] = None,
    ) -> None:
        self.camera_index = camera_index
        self.width = width
        self.height = height
        self.marker_length = float(marker_length_m)
        self.camera_matrix = camera_matrix if camera_matrix is not None else np.array(
            [
                [DEFAULT_FOCAL_LENGTH, 0, width / 2.0],
                [0, DEFAULT_FOCAL_LENGTH, height / 2.0],
                [0, 0, 1],
            ],
            dtype=np.float32,
        )
        self.dist_coeffs = dist_coeffs if dist_coeffs is not None else np.zeros((5, 1), dtype=np.float32)
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

        self._latest_tags: list[dict] = []
        self._latest_pose: dict[str, float] = {
            "detected": False,
            "id": None,
            "x": 0.0,
            "z": 0.0,
            "updated_at": 0.0,
        }
        self._lock = threading.Lock()
        self._running = False
        self._thread: threading.Thread | None = None
        self._camera = None
        self._display = None
        self._use_libsrcampy = False

    def _open_camera(self) -> None:
        if libsrcampy is not None:
            try:
                display = libsrcampy.Display()
                display.display(0, self.width, self.height)
                camera = libsrcampy.Camera()
                if camera.open_cam(self.camera_index, -1, 30, self.width, self.height):
                    camera = None
                else:
                    libsrcampy.bind(camera, display)
                    self._camera = camera
                    self._display = display
                    self._use_libsrcampy = True
                    return
            except Exception:
                self._camera = None
                self._display = None
                self._use_libsrcampy = False

        try:
            camera = cv2.VideoCapture(self.camera_index)
            camera.set(cv2.CAP_PROP_FRAME_WIDTH, self.width)
            camera.set(cv2.CAP_PROP_FRAME_HEIGHT, self.height)
            if camera.isOpened():
                self._camera = camera
                self._use_libsrcampy = False
            else:
                self._camera = None
        except Exception:
            self._camera = None

    def _close_camera(self) -> None:
        if self._camera is None:
            return
        if self._use_libsrcampy:
            try:
                libsrcampy.unbind(self._camera, self._display)
                self._display.close()
                self._camera.close_cam()
            except Exception:
                pass
        else:
            try:
                self._camera.release()
            except Exception:
                pass
        self._camera = None
        self._display = None
        self._use_libsrcampy = False

    def start(self) -> None:
        if self._running:
            return
        self._running = True
        self._open_camera()
        self._thread = threading.Thread(target=self._worker, daemon=True)
        self._thread.start()

    def stop(self) -> None:
        self._running = False
        if self._thread is not None:
            self._thread.join(timeout=1.0)
        self._close_camera()

    def _read_frame(self):
        if self._camera is None:
            return None

        if self._use_libsrcampy:
            nv12_data = self._camera.get_img(2)
            if nv12_data is None:
                return None
            yuv = np.frombuffer(nv12_data, dtype=np.uint8)
            height = self.height if yuv.size == int(self.width * self.height * 1.5) else int((yuv.size / 1.5) / self.width)
            return cv2.cvtColor(yuv.reshape((int(height * 1.5), self.width)), cv2.COLOR_YUV2BGR_NV12)

        success, frame = self._camera.read()
        if not success or frame is None:
            return None
        return frame

    def _worker(self) -> None:
        while self._running:
            try:
                frame = self._read_frame()
                if frame is None:
                    time.sleep(0.01)
                    continue

                corners, ids, _ = self.detector.detectMarkers(frame)
                detected_tags: list[dict] = []

                if ids is not None:
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
                        detected_tags.append(
                            {
                                "id": int(ids[index][0]),
                                "rvec": [float(value) for value in rvec.flatten().tolist()],
                                "tvec": [float(value) for value in tvec.flatten().tolist()],
                                "x": float(tvec[0][0]),
                                "y": float(tvec[1][0]),
                                "z": float(tvec[2][0]),
                            }
                        )

                best_tag = self._select_best_tag(detected_tags)
                latest_pose = {
                    "detected": best_tag is not None,
                    "id": int(best_tag["id"]) if best_tag else None,
                    "x": float(best_tag["x"]) if best_tag else 0.0,
                    "z": float(best_tag["z"]) if best_tag else 0.0,
                    "updated_at": time.time(),
                }

                with self._lock:
                    self._latest_tags = detected_tags
                    self._latest_pose = latest_pose
            except Exception:
                time.sleep(0.05)

    @staticmethod
    def _select_best_tag(tags: list[dict]) -> dict | None:
        if not tags:
            return None
        return min(tags, key=lambda tag: float(tag.get("x", 0.0)) ** 2 + float(tag.get("z", 0.0)) ** 2)

    def get_latest_tags(self) -> list[dict]:
        with self._lock:
            return json.loads(json.dumps(self._latest_tags))

    def get_best_tag(self) -> dict | None:
        tags = self.get_latest_tags()
        return self._select_best_tag(tags)

    def get_latest_pose(self) -> dict[str, float]:
        with self._lock:
            return json.loads(json.dumps(self._latest_pose))

    def legacy_pose(self) -> dict[str, float]:
        """既存の zidou 系が読む 1 件分の tag_pose 形式を返す。"""
        return self.get_latest_pose()

    def write_pose_file(self, path: Path | str) -> None:
        path = Path(path)
        payload = self.legacy_pose()
        try:
            path.write_text(json.dumps(payload), encoding="utf-8")
        except OSError:
            pass

    def iter_tag_events(self, poll_interval: float = 0.1):
        """定期的に最新タグ一覧を返すジェネレータ。"""
        try:
            while True:
                yield {"time": time.time(), "tags": self.get_latest_tags(), "pose": self.get_latest_pose()}
                time.sleep(poll_interval)
        except GeneratorExit:
            return
