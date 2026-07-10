"""zidou フォルダの自動化プログラムをまとめて起動するランナー。"""
from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = [
    ROOT / "zidou" / "mecanum.py",
    ROOT / "zidou" / "camera.py",
]


def run_script(script_path: Path):
    print(f"[{script_path.name}] 起動中...")
    result = subprocess.run([sys.executable, str(script_path)], capture_output=True, text=True)
    return script_path.name, result.returncode, result.stdout, result.stderr


def main() -> None:
    with ThreadPoolExecutor(max_workers=len(SCRIPTS)) as executor:
        results = executor.map(run_script, SCRIPTS)

    print("\n--- 実行結果の確認 ---")
    for name, code, stdout, stderr in results:
        print(f"\n[{name}] 終了コード: {code}")
        if stdout:
            print(f"--- 標準出力 ---\n{stdout}")
        if stderr:
            print(f"--- エラー出力 ---\n{stderr}")


if __name__ == "__main__":
    main()
