"""サンプル: 検出された全タグの位置を標準出力へ JSON ラインで出力するプログラム

使い方:
    python list_tags.py
オプション: 環境によっては `python -m zidou_lib.examples.list_tags` として実行できます。
"""
from __future__ import annotations

import time
import json
import argparse
from pathlib import Path

from zidou_lib.tag_detector import TagDetector


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--camera", type=int, default=0)
    parser.add_argument("--width", type=int, default=1920)
    parser.add_argument("--height", type=int, default=1080)
    parser.add_argument("--marker", type=float, default=0.10, help="marker length [m]")
    parser.add_argument("--out", type=str, default="", help="オプションで検出結果JSONファイルを書き出すパス")
    args = parser.parse_args()

    det = TagDetector(camera_index=args.camera, width=args.width, height=args.height, marker_length_m=args.marker)
    det.start()

    out_path = Path(args.out) if args.out else None
    try:
        print("Starting tag stream (Ctrl-C to stop)")
        for ev in det.iter_tag_events(poll_interval=0.2):
            line = {"ts": ev["time"], "tags": ev["tags"]}
            print(json.dumps(line, ensure_ascii=False))
            if out_path is not None:
                try:
                    out_path.write_text(json.dumps(line), encoding="utf-8")
                except Exception:
                    pass
    except KeyboardInterrupt:
        print("Stopping...")
    finally:
        det.stop()


if __name__ == "__main__":
    main()
