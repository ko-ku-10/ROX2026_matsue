# HONSEN_ROX

ROX2026_Sample を参考にした、HONSEN ROX 用の分割構成です。

## まずやること

1. まず [all_control.py](all_control.py) を開いて、フィールド配置やタグ位置、ソレノイドのピン番号を必要に応じて編集します。
2. 次に [run_all.py](run_all.py) を起動して、各プログラムをまとめて動かします。
3. 実機でカメラやGPIOを使う場合は、必要な依存関係が入っている状態で実行します。

## 役割

- `run_all.py`: `all_control.py` / `mecanum_control.py` / `vision.py` / `solenoid_control.py` / `apriltag.py` をまとめて起動します。
- `all_control.py`: 座標、フィールド配置、タグの待避位置、ボール追従しきい値を集約します。通常ここだけ編集します。
- `mecanum_control.py`: `all_control.py` の設定とセンサファイルを読んで足回り指令を作ります。
- `vision.py`: ボール検出結果を `ball_pose.json` に書き込みます。
- `apriltag.py`: AprilTag 検出結果を `tag_pose.json` に書き込みます。
- `solenoid_control.py`: ゲームパッド入力でソレノイドを制御します。

## 使い方

### 1. 全部まとめて起動する

```bash
cd /home/sunrise/Desktop/HONSEN_ROX
python run_all.py
```

このコマンドで、`all_control.py`、`mecanum_control.py`、`vision.py`、`solenoid_control.py`、`apriltag.py` を同時に起動します。

### 2. 座標や配置だけを編集する

編集するのは基本的に [all_control.py](all_control.py) です。

- フィールド全体のサイズ: `FIELD_WIDTH_M` / `FIELD_HEIGHT_M`
- 初期位置や待機位置: `HOME_POSE` / `SEARCH_POSE`
- ボール追従時の目標位置: `BALL_APPROACH_POSE`
- AprilTag ごとの狙い位置: `APRILTAG_TARGETS`
- ソレノイドのピン設定: `SOLENOID_PIN` / `SOLENOID_GPIO_MODE`

たとえば、AprilTag の待避位置を変えたい場合は、`APRILTAG_TARGETS` の座標を変えるだけで反映できます。

### 3. 各機能を個別に起動する

必要なものだけ試したいときは、個別に起動できます。

```bash
python all_control.py
python mecanum_control.py
python vision.py
python apriltag.py
python solenoid_control.py
```

### 4. 設定をファイルで確認する

各プログラムは、状態を JSON ファイルに出します。

- `tag_pose.json`: AprilTag の最新検出結果
- `ball_pose.json`: ボール検出結果
- `control_state.json`: 現在の判断モードや選択中の目標
- `drive_command.json`: 足回りに出した指令

### 5. 実機につなぐときの考え方

- カメラの入力元は `VISION_CAMERA_INDEX` と `APRILTAG_CAMERA_INDEX` で変えられます。
- ソレノイドのピンは `SOLENOID_PIN` で変えられます。
- 足回りをシリアル接続で動かす場合は `SERIAL_ENABLE=1` にしてから使います。

## 実行例

```bash
cd /home/sunrise/Desktop/HONSEN_ROX
python run_all.py
```

OpenCV や GPIO などの実機依存ライブラリがない場合は、各プロセスは待機モードで起動します。

## 使い分けの目安

- まず配置を決めたい: [all_control.py](all_control.py)
- ボール認識を試したい: [vision.py](vision.py)
- AprilTag で自分位置を取りたい: [apriltag.py](apriltag.py)
- 足回りの動作を確認したい: [mecanum_control.py](mecanum_control.py)
- ソレノイドを試したい: [solenoid_control.py](solenoid_control.py)
