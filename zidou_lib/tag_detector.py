"""AprilTag 検出器 (TagDetector)

カメラ入力から AprilTag を検出し、各タグの推定位置を継続的に保持します。
実機用の `hobot_vio.libsrcampy` を優先し、無ければ OpenCV `VideoCapture` を使います。
"""
from __future__ import annotations

import time
import threading
import json
from pathlib import Path
from typing import List, Dict, Optional

import numpy as np
import cv2

try:
    from hobot_vio import libsrcampy
except Exception:
    libsrcampy = None


class TagDetector:
    """AprilTag を検出して最新のタグリストを保持するシンプルなクラス。

    メソッド:
    - start(): 背景スレッドを開始
    - stop(): 停止
    - get_latest_tags(): 最新の検出リストを取得
    - write_pose_file(path): 最新検出を JSON で書き出す
    """

    def __init__(
        self,
        camera_index: int = 0,
        width: int = 1920,
        height: int = 1080,
        marker_length_m: float = 0.10,
        camera_matrix: Optional[np.ndarray] = None,
        dist_coeffs: Optional[np.ndarray] = None,
    ) -> None:
        self.camera_index = camera_index
        self.width = width
        self.height = height
        self.marker_length = float(marker_length_m)

        if camera_matrix is None:
            focal = max(width, height) * 0.5
            self.camera_matrix = np.array([[focal, 0, width / 2.0], [0, focal, height / 2.0], [0, 0, 1]], dtype=np.float32)
        else:
            self.camera_matrix = camera_matrix

        if dist_coeffs is None:
            self.dist_coeffs = np.zeros((5, 1), dtype=np.float32)
        else:
            self.dist_coeffs = dist_coeffs

        self._detector = cv2.aruco.ArucoDetector(
            cv2.aruco.getPredefinedDictionary(cv2.aruco.DICT_APRILTAG_16h5),
            cv2.aruco.DetectorParameters()
        )

        # object points for solvePnP (marker corners in marker frame)
        m = self.marker_length / 2.0
        self._obj_points = np.array([[-m, m, 0.0], [m, m, 0.0], [m, -m, 0.0], [-m, -m, 0.0]], dtype=np.float32)

        self._latest: List[Dict] = []
        self._lock = threading.Lock()
        self._running = False
        self._thread: Optional[threading.Thread] = None

        # camera pipeline
        self._cap = None
        self._use_libsrc = False

    def _open_camera(self):
        if libsrcampy is not None:
            try:
                disp = libsrcampy.Display()
                disp.display(0, self.width, self.height)
                cam = libsrcampy.Camera()
                if cam.open_cam(self.camera_index, -1, 30, self.width, self.height):
                    cam = None
                else:
                    libsrcampy.bind(cam, disp)
                    self._cap = (cam, disp)
                    self._use_libsrc = True
                    return
            except Exception:
                self._cap = None

        # fallback to OpenCV VideoCapture
        try:
            cap = cv2.VideoCapture(self.camera_index)
            cap.set(cv2.CAP_PROP_FRAME_WIDTH, self.width)
            cap.set(cv2.CAP_PROP_FRAME_HEIGHT, self.height)
            if cap.isOpened():
                self._cap = cap
                self._use_libsrc = False
            else:
                self._cap = None
        except Exception:
            self._cap = None

    def _close_camera(self):
        if self._cap is None:
            return
        if self._use_libsrc:
            cam, disp = self._cap
            try:
                libsrcampy.unbind(cam, disp)
                disp.close()
                cam.close_cam()
            except Exception:
                pass
        else:
            try:
                self._cap.release()
            except Exception:
                pass
        self._cap = None

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

    def _worker(self) -> None:
        while self._running:
            frame = None
            try:
                if self._cap is None:
                    time.sleep(0.1)
                    continue

                if self._use_libsrc:
                    cam, _ = self._cap
                    nv12 = cam.get_img(2)
                    if nv12 is None:
                        time.sleep(0.005)
                        continue
                    yuv = np.frombuffer(nv12, dtype=np.uint8)
                    h = self.height if yuv.size == int(self.width * self.height * 1.5) else int((yuv.size / 1.5) / self.width)
                    frame = cv2.cvtColor(yuv.reshape((int(h * 1.5), self.width)), cv2.COLOR_YUV2BGR_NV12)
                else:
                    cap = self._cap
                    ret, frame = cap.read()
                    if not ret or frame is None:
                        time.sleep(0.02)
                        continue

                corners, ids, _ = self._detector.detectMarkers(frame)
                detected = []
                if ids is not None and len(ids) > 0:
                    for i in range(len(ids)):
                        try:
                            # solvePnP expects object points (4,3) and image points (4,2)
                            img_pts = corners[i][0].astype(np.float32)
                            success, rvec, tvec = cv2.solvePnP(self._obj_points, img_pts, self.camera_matrix, self.dist_coeffs, flags=cv2.SOLVEPNP_ITERATIVE)
                            if not success:
                                continue
                            tag = {
                                "id": int(ids[i][0]),
                                "rvec": [float(x) for x in rvec.flatten().tolist()],
                                "tvec": [float(x) for x in tvec.flatten().tolist()],
                                "x": float(tvec[0][0]),
                                "y": float(tvec[1][0]),
                                "z": float(tvec[2][0]),
                            }
                            detected.append(tag)
                        except Exception:
                            continue

                with self._lock:
                    self._latest = detected

            except Exception:
                time.sleep(0.05)

        # worker exiting

    def get_latest_tags(self) -> List[Dict]:
        with self._lock:
            return json.loads(json.dumps(self._latest))

    def write_pose_file(self, path: Path | str) -> None:
        path = Path(path)
        payload = {"detected": bool(self.get_latest_tags()), "tags": self.get_latest_tags(), "updated_at": time.time()}
        try:
            path.write_text(json.dumps(payload), encoding="utf-8")
        except Exception:
            pass

    def iter_tag_events(self, poll_interval: float = 0.1):
        """ジェネレータ: 定期的に最新タグリストを返す（Ctrl-C まで）"""
        try:
            while True:
                yield {"time": time.time(), "tags": self.get_latest_tags()}
                time.sleep(poll_interval)
        except GeneratorExit:
            return
