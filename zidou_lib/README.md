# zidou_lib

`zidou_lib` は、AprilTag 読み取りとメカナム制御を分離した小さなライブラリです。実装の役割は次の 3 つに分かれています。

- [tag_detector.py](tag_detector.py): カメラ入力から AprilTag を検出して最新状態を保持する
- [drivetrain.py](drivetrain.py): メカナム逆運動学と自動追従の計算を行う
- [examples/list_tags.py](examples/list_tags.py): 上記 2 つを組み合わせるサンプル

`run_all.py` は既存の `zidou` プログラムをまとめて起動する互換ランナーです。

---

## 依存関係

- Python 3.12 想定
- `numpy`
- `opencv-python`
- 実機では `hobot_vio.libsrcampy` があれば優先利用

開発用には、プロジェクトルートで次のように入れると扱いやすいです。

```bash
pip install -e .
```

---

## 使い方

### 1. AprilTag を読む

```python
from zidou_lib.tag_detector import TagDetector

detector = TagDetector()
detector.start()
tags = detector.get_latest_tags()
pose = detector.legacy_pose()
detector.stop()
```

`get_latest_tags()` は検出された全タグを返します。各要素は `id`, `x`, `y`, `z`, `rvec`, `tvec` を持ちます。

### 2. メカナム指令を作る

```python
from zidou_lib.drivetrain import AutoNavigator, mecanum_ik

navigator = AutoNavigator()
vx, vy, omega = navigator.compute_cmd(x=0.2, z=0.6)
wheels = mecanum_ik(vx, vy, omega)
```

`AutoNavigator` はタグの横ずれ `x` と距離 `z` から、前進・旋回の簡単な指令を作ります。

### 3. サンプルを動かす

```bash
python -m zidou_lib.examples.list_tags
```

このサンプルは、検出されたタグ一覧、最良タグ、`tag_pose.json` 互換の姿勢、さらにメカナムのホイール指令まで標準出力へ出します。

### 4. 既存の `zidou` 起動をまとめる

```bash
python -m zidou_lib.run_all
```

---

## API 一覧

### `zidou_lib.tag_detector.TagDetector`

- `start()` / `stop()` で背景スレッドを制御する
- `get_latest_tags()` で最新の検出タグ一覧を取得する
- `get_best_tag()` で最も近いタグ 1 件を取る
- `legacy_pose()` で `tag_pose.json` 互換の 1 件情報を返す
- `write_pose_file(path)` で互換 JSON を保存する

### `zidou_lib.drivetrain`

- `mecanum_ik(vx, vy, omega, L=0.12, W=0.10)`
- `blend_commands(a, b, alpha)`
- `best_tag_from_list(tags)`
- `read_latest_tag_pose(path=None)`
- `AutoNavigator`

---

## 実装の意図

`zidou` 側の既存コードは、`tag_pose.json` に単一タグの結果を保存して読んでいました。`zidou_lib` ではタグ検出を複数件保持できるようにしつつ、`legacy_pose()` と `read_latest_tag_pose()` で古い流れもそのまま動くようにしています。

必要なら次に、`zidou` 側のコードもこのライブラリ API を直接使う形へ寄せられます。
