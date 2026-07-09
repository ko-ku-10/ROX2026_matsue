# ROX2026ベースキット　サンプルプログラム　セットアップ手順書

# ROX2026_Sample — 説明書（簡潔版）

このリポジトリは、DualSense（PS5コントローラー）で操作するメカナムホイール搭載ロボット制御の参考実装です。主な機能は以下です。

- DualSense による手動操縦（`mecanum_rc.py`）
- カメラ映像と AprilTag 検出によるレーダーマップ表示（`camera.py`, `2camera.py`, `zidou/camera.py`）
- 簡易自動ナビゲータ（`zidou/mecanum.py` の `AutoNavigator`）
- ペアリング用スクリプト（`pair_dualsense.sh`）
- テスト（`tests/test_auto_navigation.py`）

---

## 目次

- 準備（依存・ハード）
- クイックスタート（起動コマンド）
- 各スクリプトの説明
- テストの実行方法
- 主要な環境変数（要調整項目）
- ファイル構成
- トラブルシューティング

---

## 準備（要点）

- 対応Python: 3.12（`pyproject.toml` に指定）
- システム依存パッケージ: Bluetooth やビルドツール、SDL 等が必要（`pair_dualsense.sh` 内でも一部インストール処理あり）
- ハードウェア: RDK X5 等のカメラ SDK（`hobot_vio.libsrcampy`）や USB シリアル（モーター用）

推奨インストール手順（RDK上で例）:

```bash
# システムパッケージを更新・インストール（必要に応じて実行）
sudo apt update && sudo apt upgrade -y
sudo apt install -y bluez bluez-tools expect build-essential pkg-config python3-dev libsdl2-dev libasound2-dev

# uv を用いる場合（推奨の高速ツール）
curl -LsSf https://astral.sh/uv/install.sh | sh
source $HOME/.local/bin/env
uv python install 3.12
uv sync --python 3.12
```

---

## クイックスタート

1. DualSense をペアリング（初回のみ）:

```bash
cd ~/ROX2026_Sample
bash pair_dualsense.sh
```

2. USB シリアル（モーター制御）を接続し、認識ポートを確認:

```bash
ls /dev/ttyUSB*
```

3. 実行例:

- 手動操縦（DualSense）:

```bash
cd ~/ROX2026_Sample
uv run python mecanum_rc.py
```

- カメラ + レーダー（単体）:

```bash
uv run python camera.py
# または複数カメラ向け
uv run python 2camera.py
```

- プロセスをまとめて起動（ルートの `run_all.py` は `mecanum_rc.py` と `2camera.py` を並列実行します）:

```bash
uv run python run_all.py
```

- `zidou` ディレクトリ内の一括起動（`mecanum.py` と `camera.py`）:

```bash
cd zidou
uv run python run_all.py
```

---

## 各スクリプトの簡単な説明

- `mecanum_rc.py`: DualSense を受けて EDULITE05 モータへ AT コマンドで速度を送るメイン制御プログラム。PID フィードバックやダッシュボードを内蔵。
- `camera.py`, `2camera.py`: カメラ入力を受けて MJPEG ストリーミングと 2D レーダーマップを提供。`2camera.py` は複数カメラ想定の UI 構成。
- `pair_dualsense.sh`: DualSense の Bluetooth ペアリング（`bluetoothctl` + `expect` を利用）。
- `run_all.py`（ルート）: `mecanum_rc.py` と `2camera.py` を並列実行して出力を集約します。
- `zidou/mecanum.py`: 自動ナビゲーション用の `AutoNavigator`（タグ位置から `vx, vy, omega` を計算）。
- `tests/test_auto_navigation.py`: `AutoNavigator` の単体テスト（pytest）。

---

## テスト実行

このリポジトリには簡易テストが含まれます。テストは Python 実行環境で `pytest` を使って実行してください。

```bash
cd ~/ROX2026_Sample
uv run pytest
```

（テストは実機依存のモジュールを避けるように作られており、`zidou/mecanum.py` のロジック単体を検証します）

---

## 主要な環境変数（調整ポイント）

- `SERIAL_PORT` : デフォルトのシリアルポート（例: `/dev/ttyUSB1`）
- `AT_SPEED_PERCENT` : 最高速度（0〜100）
- `DEADZONE` : スティックのデッドゾーン
- `TRANSLATION_GAIN`, `ROTATION_GAIN` : 移動／旋回の感度
- `INPUT_SLEW_RATE` : 急加速抑制
- `PID_ENABLE`, `PID_KP`, `PID_KI`, `PID_KD` : PID 関連
- `DASHBOARD_ENABLE`, `DASHBOARD_PORT` : ダッシュボード（HTTP）設定
- `DUALSENSE_MAC_ADDRESS` : 固定でペアリングしたい場合に設定可能

設定は環境変数で渡すか、スクリプト先頭の定数を編集してください。例:

```bash
AT_SPEED_PERCENT=60 SERIAL_PORT=/dev/ttyUSB0 uv run python mecanum_rc.py
```

---

## ファイル構成（概要）

```
ROX2026_Sample/
├── mecanum_rc.py        # メイン: DualSense -> モーター制御（ダッシュボード/ PID）
├── pair_dualsense.sh    # DualSense ペアリング補助スクリプト
├── pyproject.toml       # プロジェクト設定 / 依存
├── run_all.py           # ルート: 複数スクリプトを並列実行するランナー
├── 2camera.py           # カメラ+レーダー表示（複数カメラ向けUI）
├── camera.py            # 単体カメラのストリーミング + レーダー
├── README.md            # （このファイル）
└── tests/               # pytest テスト
    └── test_auto_navigation.py

zidou/
├── camera.py            # カメラユーティリティ（タグ検出 + tag_pose.json 書き出し）
├── mecanum.py           # `AutoNavigator` 等の補助ロジック
└── run_all.py           # zidou 用の一括起動ランナー
```

---

## よくあるトラブルと対処

- シリアル接続エラー: `/dev/ttyUSB*` の一覧を確認し、`SERIAL_PORT` を合わせる。
- DualSense が見つからない: `pair_dualsense.sh` を再実行し、Bluetooth サービスを確認する（`bluetoothctl devices`）。
- カメラが初期化できない: `hobot_vio` SDK が利用可能か確認。開発環境では SDK が無くてもテストは一部実行できます。

---

もしこの README へ追加してほしい情報（例: 詳細なパラメータ一覧、起動時のログ例、開発向けのデバッグフロー）があれば教えてください。必要に応じてさらに追記して整備します。

├── camera.py            # 単一カメラ用のサンプルスクリプト
├── README.md            # セットアップ手順書
└── tests/               # テスト群（pytest で実行）
  └── test_auto_navigation.py

zidou/
├── camera.py            # zidou 向けカメラユーティリティ
├── mecanum.py           # zidou 向けメカナム制御ユーティリティ
└── run_all.py           # zidou フォルダ内での一括起動スクリプト

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
