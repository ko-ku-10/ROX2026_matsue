import subprocess
import sys
from concurrent.futures import ThreadPoolExecutor

scripts = [
    "mecanum_rc.py",
    "2camera.py"
]

def run_script(script_name):
    print(f"[{script_name}] 起動中...")
    # 実行して終了を待つ
    result = subprocess.run([sys.executable, script_name], capture_output=True, text=True)
    return script_name, result.returncode, result.stdout, result.stderr

# max_workers をスクリプトの数に合わせることで同時実行になります
with ThreadPoolExecutor(max_workers=len(scripts)) as executor:
    results = executor.map(run_script, scripts)

print("\n--- 実行結果の確認 ---")
for name, code, stdout, stderr in results:
    print(f"\n[{name}] 終了コード: {code}")
    if stdout:
        print(f"--- 標準出力 ---\n{stdout}")
    if stderr:
        print(f"--- エラー出力 ---\n{stderr}")