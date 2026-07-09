# zidou_lib — AprilTag 検出とメカナム足回りユーティリティ

このパッケージは、カメラからの AprilTag 検出を行う `TagDetector` と、メカナム足回りの小さなユーティリティ関数群を提供します。ライブラリ化することで、既存の制御プログラムに組み込みやすく、テストやモックがしやすくなっています。

この README はエンジニア向けを想定しており、すぐに試せるコード例や統合の手順を中心に記載しています。

---

## 必要条件

- Python 3.10+（プロジェクトは pyproject.toml で Python 3.12 を想定）
- 必須パッケージ: `numpy`, `opencv-python`（import 時に必要）
- 実機: RDK X5 の `hobot_vio.libsrcampy` があれば優先して使用します。無い場合は OpenCV の `VideoCapture` にフォールバックします。

推奨インストール（プロジェクトルートで実行）:

```bash
# 依存のインストール（仮想環境推奨）
pip install -r requirements.txt  # または pip install numpy opencv-python

# 開発中はパッケージを編集可能インストール
pip install -e .
```

---

## すばやく試す（クイックスタート）

1) プロジェクトルートに移動して、`zidou_lib` をインポートできる状態にします（`pip install -e .` または `PYTHONPATH=. python ...`）。

2) 付属の CLI サンプルで検出結果をストリーム出力:

```bash
cd ROX2026_Sample
python -m zidou_lib.examples.list_tags
# または出力をファイルへ
python -m zidou_lib.examples.list_tags --out zidou/tag_pose.json
```

---

## 主要 API

### `zidou_lib.tag_detector.TagDetector`

主なメソッド:

- `TagDetector(camera_index=0, width=1920, height=1080, marker_length_m=0.10, ...)`
  - コンストラクタ。カメラやマーカーサイズ等を指定できます。
- `start()` / `stop()`
  - 背景スレッドでカメラ読み取り・タグ検出を開始/停止します。
- `get_latest_tags() -> list[dict]`
  - 現在保持している検出タグのリストを返します。各要素の例:

```json
{
  "id": 5,
  "rvec": [..],
  "tvec": [..],
  "x": 0.12,
  "y": -0.03,
  "z": 0.87
}
```

- `write_pose_file(path)`
  - 最新検出を JSON で書き出します（パッケージ付属の `list_tags.py` も利用）。
- `iter_tag_events(poll_interval=0.1)`
  - ジェネレータ: 定期的に検出結果を返します（CLI 用に便利）。

注意: `TagDetector` は実機用 SDK（`hobot_vio.libsrcampy`）を優先使用します。SDK が無い環境では `VideoCapture` を使いますが、環境に依存するためカメラ権限やデバイス番号に注意してください。

### `zidou_lib.drivetrain`

- `mecanum_ik(vx, vy, omega, L=0.12, W=0.10) -> (v_fl, v_fr, v_rl, v_rr)`
  - メカナムの逆運動学。出力は正規化済み（最大絶対値が1になる）。
- `blend_commands(a, b, alpha)`
  - 2つのコマンドベクトルを線形ブレンドします（alpha=0 → a, alpha=1 → b）。

---

## 統合サンプル（既存コードとの互換）

既存リポジトリの `zidou` は `tag_pose.json` に単一の「最良タグ」情報を保存する形式を使っています（`{"detected": bool, "id": int, "x": float, "z": float, "updated_at": float}`）。`TagDetector` は複数タグ情報を保持するため、互換レイヤを挟む例を示します:

```python
from pathlib import Path
from zidou_lib.tag_detector import TagDetector
import time, json

det = TagDetector()
det.start()
time.sleep(0.5)  # カメラのウォームアップ

tags = det.get_latest_tags()
best = None
if tags:
    # 距離が近いものを選ぶ（例）
    best = min(tags, key=lambda t: t['x']**2 + t['z']**2)

legacy = {
    'detected': bool(best),
    'id': int(best['id']) if best else None,
    'x': float(best['x']) if best else 0.0,
    'z': float(best['z']) if best else 0.0,
    'updated_at': time.time(),
}

Path('zidou/tag_pose.json').write_text(json.dumps(legacy), encoding='utf-8')
det.stop()
```

この方法で既存の `zidou` 側コードを変更せずに `zidou_lib` を組み込めます。

---

## サンプル: メカナム指令への利用例

```python
from zidou_lib.tag_detector import TagDetector
from zidou_lib.drivetrain import mecanum_ik

det = TagDetector(); det.start()
tags = det.get_latest_tags()
if tags:
    best = min(tags, key=lambda t: t['x']**2 + t['z']**2)
    # 例: タグの z が目標距離より離れていれば前進指令
    vx = max(-0.5, min(0.5, 0.35 - best['z']))
    vy = 0.0
    omega = max(-0.3, min(0.3, best['x']))
    wheels = mecanum_ik(vx, vy, omega)
    print(wheels)
det.stop()
```

---

## テスト & モック

- `TagDetector` はカメラ依存を内部で扱っているため、ユニットテストではカメラ呼び出しをモックするか、`get_latest_tags()` に手動データを注入してテストするのが簡単です。
- 付属サンプル `zidou_lib/examples/list_tags.py` は簡易的な動作確認として利用できます。

---

## トラブルシューティング

- `cv2` や `numpy` の import エラー: 必要パッケージをインストールしてください。
- カメラが開けない: `hobot_vio` SDK を使用する場合は SDK のドキュメントに従ってセットアップしてください。OpenCV の場合は `VideoCapture(0)` の代替インデックスを試してください。

---

必要であれば、次の追加を行います:
- `tag_pose.json` の互換性を常に保つためのヘルパ関数の追加（ワンライナーで可能）
- 単体テスト（pytest）を追加して CI で回せるようにする

どれを追加しますか？
