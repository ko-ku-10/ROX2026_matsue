"""サンプル: AprilTag 検出結果とメカナム指令をまとめて表示する。"""
from __future__ import annotations

import argparse
import json
from pathlib import Path
import time

from zidou_lib.drivetrain import AutoNavigator, best_tag_from_list, mecanum_ik
from zidou_lib.tag_detector import TagDetector


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--camera", type=int, default=0)
    parser.add_argument("--width", type=int, default=1920)
    parser.add_argument("--height", type=int, default=1080)
    parser.add_argument("--marker", type=float, default=0.10, help="marker length [m]")
    parser.add_argument("--out", type=str, default="", help="JSON で保存するパス")
    parser.add_argument("--interval", type=float, default=0.2, help="更新間隔 [s]")
    args = parser.parse_args()

    detector = TagDetector(camera_index=args.camera, width=args.width, height=args.height, marker_length_m=args.marker)
    navigator = AutoNavigator()
    detector.start()

    out_path = Path(args.out) if args.out else None
    try:
        print("Starting combined tag/navigation sample (Ctrl-C to stop)")
        while True:
            tags = detector.get_latest_tags()
            best = best_tag_from_list(tags)
            pose = detector.legacy_pose()
            vx, vy, omega = navigator.compute_cmd(pose.get("x"), pose.get("z"))
            wheels = mecanum_ik(vx, vy, omega)

            payload = {
                "ts": time.time(),
                "tags": tags,
                "best": best,
                "legacy_pose": pose,
                "cmd": {"vx": vx, "vy": vy, "omega": omega},
                "wheels": {name: value for name, value in zip(("FL", "FR", "RL", "RR"), wheels)},
            }
            print(json.dumps(payload, ensure_ascii=False))

            if out_path is not None:
                try:
                    out_path.write_text(json.dumps(payload, ensure_ascii=False), encoding="utf-8")
                except OSError:
                    pass

            time.sleep(max(0.01, float(args.interval)))
    except KeyboardInterrupt:
        print("Stopping...")
    finally:
        detector.stop()


if __name__ == "__main__":
    main()
