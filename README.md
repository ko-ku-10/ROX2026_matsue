# ROX2026ベースキット　サンプルプログラム　セットアップ手順書

---

## 📦 このプログラムでできること

DualSense（PS5コントローラー）を使って、メカナムホイール搭載の 4WD ロボットを  
Bluetooth で無線操縦するプログラムです。

| 操作 | 動作 |
|---|---|
| L2を押しながら  左スティック 上下 | 前進 / 後退 |
| L2を押しながら  左スティック 左右 | 横移動（ストレーフ） |
| R2を押しながら  右スティック 左右 | その場での旋回 |
| OPTIONS ボタン                  | プログラム終了 |

【メカナムホイール配置】
  [ID1 前左 FL] -------- [ID2 前右 FR]
      |                  |
  [ID3 後左 RL] -------- [ID4 後右 RR]

---

## 🛒 用意するもの（ハードウェア）

| 品目 | 備考 |
|---|---|
| RDK X5 | Ubuntu がインストール済みのもの |
| Robstride EDULITE05 | メカナムホイール用モーター × 4 |
| DualSense コントローラー | 充電切れに注意 |
| USB シリアル変換ケーブル | モーター制御用（/dev/ttyUSB に認識されるもの） |

---

## 🖥️ セットアップ手順

### ステップ 1 : RDK X5に必要なパッケージをインストール

RDK X5 にSSH またはモニター接続し、ターミナルを開いて以下を実行してください。

```bash
# システムパッケージを最新化
sudo apt update && sudo apt upgrade -y

# Bluetooth / シリアル通信 / pygame ビルドに必要なパッケージ
sudo apt install -y \
  can-utils bluez bluez-tools expect \
  build-essential pkg-config python3-dev \
  libsdl2-dev libsdl2-image-dev libsdl2-mixer-dev libsdl2-ttf-dev \
  libportmidi-dev libfreetype6-dev libjpeg-dev libpng-dev libasound2-dev
```

---

### ステップ 2 : Python 環境の準備（uv を使います）

このプロジェクトでは **uv**（高速な Python パッケージマネージャー）を使います。

```bash
# uv のインストール
curl -LsSf https://astral.sh/uv/install.sh | sh

# インストールを反映（ターミナルを再起動するか、以下を実行）
source $HOME/.local/bin/env
```

> **uv とは?**  
> `pip` + `venv` をまとめて高速化したツールです。`uv run` で実行すると  
> 仮想環境の作成・依存パッケージのインストールを自動で行ってくれます。

続けて、このプロジェクト用に Python 3.12 を用意します。

```bash
# Python 3.12 をインストール
uv python install 3.12

# 依存関係を Python 3.12 で構築
uv sync --python 3.12
```


---

### ステップ 3 : プログラムのダウンロード（コピー）

配布された `ROX2026_Sample` フォルダをRDK X5の任意のディレクトリに配置します。

```bash
# 例: ホームディレクトリに配置した場合
cd ~/ROX2026_Sample
ls
# mecanum_rc.py  pair_dualsense.sh  pyproject.toml  README.md
```

---

### ステップ 4 : DualSense を Bluetooth でペアリング

> **初回のみ必要です。** 一度ペアリングすれば次回以降は PS ボタンで自動接続できます。

#### 4-1. DualSense をペアリングモードにする

1. DualSense の電源を完全に切る  
   （PS ボタンを **10秒長押し** → ライトが消えるまで）

2. **PS ボタン + SHARE ボタン** を同時に約 3秒長押しする  
   → ライトバーが **チカチカ点滅** したらペアリングモード

#### 4-2. スクリプトを実行する

```bash
cd ~/ROX2026_Sample
bash pair_dualsense.sh
```

スクリプトが MAC アドレスの候補を表示するので、DualSense の MAC を入力します。

```
スキャン結果（候補MACアドレス）:
    1) AA:BB:CC:DD:EE:FF

使いたい MAC アドレスを手入力してください（例: AA:BB:CC:DD:EE:FF）
MACアドレス: AA:BB:CC:DD:EE:FF   
→ 表示された候補で良ければ　 y　を入力してEnterで確定
→ 表示された候補以外のアドレスを使いたい場合は　n　を入力してアドレスを手入力
```
途中でライトバーが消えた場合は再度**ペアリングモード**にしてください

「✅ ペアリング完了！」と表示されれば成功です。

---

### ステップ 5 : USB シリアルを接続する

モーター制御用の USB シリアルケーブルをRDK X5に接続します。  
デフォルトでは `/dev/ttyUSB1` を使います。

```bash
# 接続後、デバイスが認識されているか確認
ls /dev/ttyUSB*
# /dev/ttyUSB0  /dev/ttyUSB1  など表示されれば OK
```

> 別のポート番号（`ttyUSB0` など）に繋がった場合は、  
> 後述の「パラメータ調整」で `SERIAL_PORT` を変更してください。

---

### ステップ 6 : プログラムを起動する

```bash
cd ~/ROX2026_Sample
uv run python mecanum_rc.py
```

以下のようなメッセージが表示されれば正常起動です。

```
シリアル接続完了: /dev/ttyUSB1 @ 921600
DualSense を検出中...
DualSense 接続完了
全モーター イネーブル完了
操縦開始！（OPTIONS で終了）
```

---

## 🎮 操縦方法まとめ

| 操作 | 動き |
|---|---|
| 左スティック ↑ | 前進 |
| 左スティック ↓ | 後退 |
| 左スティック ← | 左に平行移動 |
| 左スティック → | 右に平行移動 |
| 右スティック ← | 左旋回（その場） |
| 右スティック → | 右旋回（その場） |
| OPTIONS ボタン | 終了 |

---

## ⚙️ パラメータ調整ガイド（主なもの）

`mecanum_rc.py` の先頭付近にある設定を変えることで、操縦感を調整できます。

```python
# 最高速度の上限 [%]（0〜100）— 最初は低めから試す
AT_SPEED_PERCENT = 40

# スティックの遊び（小さくすると反応が敏感になる）
DEADZONE = 0.08

# 移動の効き（大きいほど素早く動く）
TRANSLATION_GAIN = 1.0

# 旋回の効き（大きいほど素早く回る）
ROTATION_GAIN = 1.0

# スティック曲線（1.0 = リニア、大きいほど中心付近がマイルド）
INPUT_CURVE_EXPONENT = 1.0

# 急加速制限（0.0 = 無効、0.5 などを試してみる）
INPUT_SLEW_RATE = 0.0
```


環境変数で変更することもできます:

```bash
AT_SPEED_PERCENT=60 uv run python mecanum_rc.py
```


---

## 🧭 EDULITE05 のロータリーエンコーダを使った PID 速度制御

このブランチでは EDULITE05 へ送る速度指令の手前に PID 補正レイヤを追加し、`PID_ENABLE=1` のときは EDULITE05 のロータリーエンコーダ値から推定したホイール速度をフィードバックに使います。

既定では、EDULITE05 が返す `AT 10` ステータスフレームを読み取り、データ先頭の `uint16` 角度カウント差分から回転速度を計算します。エンコーダ値が読めない場合は警告を出し、従来の開ループ速度指令へフォールバックします。

起動例:

```bash
PID_ENABLE=1 \
PID_KP=0.08 PID_KI=0.0 PID_KD=0.0 \
EDULITE05_ENCODER_MAX_RPS=20.0 \
uv run python mecanum_rc.py
```

主な PID パラメータ:

```python
PID_ENABLE = 0                 # 1でPID補正を有効化
PID_KP = 0.08                  # 比例ゲイン（最初は低め）
PID_KI = 0.0                   # 積分ゲイン
PID_KD = 0.0                   # 微分ゲイン
PID_OUTPUT_LIMIT = 0.12        # PID補正量の上限
PID_INTEGRAL_LIMIT = 0.5       # 積分項の上限
PID_CORRECTION_DEADBAND = 0.12 # 小さい指令ではPID補正しない
```

EDULITE05 エンコーダ読み取り設定:

```python
PID_FEEDBACK_SOURCE = "edulite05_encoder"  # 通常はこのまま
EDULITE05_ENCODER_FRAME = "status"         # AT 10 ステータスフレームを使用
EDULITE05_ENCODER_FORMAT = "uint16"         # ステータスデータ先頭2バイト
EDULITE05_ENCODER_VALUE_OFFSET = 0          # 応答データ内の値開始位置
EDULITE05_ENCODER_UNITS = "counts"          # 角度カウント値として扱う
EDULITE05_ENCODER_COUNTS_PER_REV = 65536    # 1回転あたりのカウント数
EDULITE05_ENCODER_MAX_RPS = 20.0            # 正規化速度1.0に相当する回転数[rev/s]
EDULITE05_ENCODER_SPEED_FILTER_ALPHA = 0.25 # 速度フィードバックの平滑化
EDULITE05_ENCODER_QUERY_INTERVAL = 0.02     # 読み取り周期[秒]
EDULITE05_ENCODER_STALE_SEC = 0.25          # 古いエンコーダ値を無効化する秒数
```

EDULITE05 のファームウェアやUSB-CAN変換器の応答形式が異なる場合は、まず `EDULITE05_ENCODER_FORMAT` と `EDULITE05_ENCODER_VALUE_OFFSET` を合わせてください。レジスタ読み取り応答を使う構成では `EDULITE05_ENCODER_FRAME=register EDULITE05_ENCODER_UNITS=radians EDULITE05_ENCODER_FORMAT=float32` のように指定できます。

テスト用に外部ファイルから正規化速度を入れる場合だけ、`PID_FEEDBACK_SOURCE=file PID_FEEDBACK_FILE=/tmp/edulite05_wheel_speed.json` を指定できます。

---

## 🔌 接続先を変える場合

```bash
# シリアルポートを変更する例
SERIAL_PORT=/dev/ttyUSB0 uv run python mecanum_rc.py
```

---

## 🐛 トラブルシューティング

### ❌ 「シリアルポートに接続できませんでした」と出る

- USB ケーブルが刺さっているか確認
- `ls /dev/ttyUSB*` でデバイスが認識されているか確認
- ポート番号が違う場合は `SERIAL_PORT=/dev/ttyUSB0` のように指定

### ❌ 「DualSense が見つかりません」と出る

- Bluetooth が繋がっているか確認: `bluetoothctl devices`
- 繋がっていなければ `pair_dualsense.sh` を再実行
- DualSense の PS ボタンを短く押して接続を試みる

### ❌ ペアリングスクリプトで MAC が候補に出ない

- DualSense が点滅しているか（ペアリングモード）確認
- RDK X5と DualSense を **1m 以内**に近づける
- 実行文を`SCAN_SEC=20 bash pair_dualsense.sh` でスキャン時間を延ばして再試行

### ❌ モーターが動かない

- USBシリアルの接続とポート番号を確認
- `AT_SPEED_PERCENT` が 0 になっていないか確認
- モーターへの電源供給を確認


---

## 📁 ファイル構成

```
ROX2026_Sample/
├── mecanum_rc.py        # メインプログラム（ここを読めば動作が分かる）
├── pair_dualsense.sh    # DualSense ペアリングスクリプト
├── pyproject.toml       # プロジェクト設定・依存関係
└── README.md            # セットアップ手順書

```

---

## 📖 メモ

```
# ホイール速度の計算式（メカナムホイールの運動学）
v_FL =  vx - vy - ω*(L+W)
v_FR =  vx + vy + ω*(L+W)
v_RL =  vx + vy - ω*(L+W)
v_RR =  vx - vy + ω*(L+W)
```

---
