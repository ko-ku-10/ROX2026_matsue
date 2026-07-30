"""HONSEN ROX の一括起動。"""
from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
import subprocess
import sys
import threading
import time


SCRIPTS = [
    "all_control.py",
    "mecanum_control.py",
    "vision.py",
    "solenoid_control.py",
    "apriltag.py",
]


def _stream_output(script_name: str, process: subprocess.Popen[str]) -> None:
    assert process.stdout is not None
    for line in process.stdout:
        print(f"[{script_name}] {line.rstrip()}")


def _run_script(script_name: str) -> tuple[str, int]:
    print(f"[{script_name}] 起動中...")
    process = subprocess.Popen(
        [sys.executable, str(Path(__file__).with_name(script_name))],
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        bufsize=1,
    )
    reader = threading.Thread(target=_stream_output, args=(script_name, process), daemon=True)
    reader.start()
    return_code = process.wait()
    reader.join(timeout=0.5)
    return script_name, return_code


def main() -> int:
    print("[run_all] HONSEN ROX を起動します")
    with ThreadPoolExecutor(max_workers=len(SCRIPTS)) as executor:
        futures = [executor.submit(_run_script, script_name) for script_name in SCRIPTS]
        try:
            while futures:
                remaining = []
                for future in futures:
                    if future.done():
                        script_name, return_code = future.result()
                        print(f"[run_all] {script_name} 終了コード: {return_code}")
                    else:
                        remaining.append(future)
                futures = remaining
                if futures:
                    time.sleep(0.5)
        except KeyboardInterrupt:
            print("[run_all] Ctrl+C で停止しました")
            return 0
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
