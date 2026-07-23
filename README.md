# Tukinoma Bot

Discordサーバーのボイスチャンネル（VC）入退室通知、各種サーバー管理、およびWeb連動アラーム再生を行う多機能Discordボットです。

## 主な機能

- **Web連動VCアラーム機能**
  - Webダッシュボード（`http://0.0.0.0:PORT`）から指定時刻・VC・再生曲を設定可能。
  - 音源は **YouTube URL** または **音声ファイル（MP3等）の直接アップロード** に対応。
  - 時間になるとBotが自動で指定VCへ接続し、音楽を再生。
- **VC入退室通知 (`/vc`)**
  - ボイスチャンネルへの接続・切断をリアルタイム通知。
  - 複数VCの個別設定（通知先チャンネル・メンション指定）に対応。
- **メッセージ管理 (`/clear`)**
  - チャンネル内のメッセージを指定件数（1〜100件）一括削除。

## 🛠️ コマンド一覧

### 1. VC通知コマンドグループ (`/vc`)
| サブコマンド | 説明 | 実行権限 |
| :--- | :--- | :--- |
| `/vc add` | 監視するVCと通知先チャンネル、メンション設定を追加・更新 | 管理者 |
| `/vc list` | 登録されているVC通知設定の一覧を表示 | 全員 |
| `/vc remove` | 指定したVCの通知設定を1つ削除 | 管理者 |
| `/vc clear` | サーバー内のVC通知設定を全削除 | 管理者 |

### 2. 管理コマンド (`/clear`)
| コマンド | 説明 | 実行権限 |
| :--- | :--- | :--- |
| `/clear <件数>` | 指定した件数のメッセージを一括削除 | メッセージの管理 |

## ディレクトリ構造

```text
tukinoma_bot/
├── main.py              # アプリケーション起動・WebUI並行起動
├── web_server.py        # Webダッシュボード用API (FastAPI)
├── requirements.txt     # 依存ライブラリ一覧
├── .env                 # 環境変数設定
├── .gitignore           # Git除外設定
├── cogs/                # 各機能モジュール (Cog)
│   ├── vc_notifier.py   # VC通知機能 (/vc)
│   ├── moderation.py    # 管理機能 (/clear)
│   └── alarm.py         # アラーム自動再生Cog
├── utils/               # ユーティリティ
│   ├── config_manager.py# データ管理マネージャー
│   └── audio_downloader.py # YouTube音声抽出ダウンロード
├── data/                # 設定データ保存先 (Git除外)
│   ├── vc_notifier.json # VC通知の設定ファイル
│   ├── alarms.json      # アラームの設定ファイル
│   └── audio/           # 保存済み音声ファイル (.mp3)
├── templates/           # WebUIテンプレート
│   └── index.html       # ダッシュボード画面
└── docs/                # ドキュメント類
    └── TECHNICAL.md     # 詳細技術仕様書

```

## 動作環境・セットアップ

1. **必要環境**: Python 3.10 以上, **FFmpeg**（音声再生用）
2. **依存ライブラリのインストール**:
```bash
pip install -r requirements.txt
```


3. **環境変数の設定**:
`.env` ファイルを作成し、Bot Token と WebUI のポート番号を設定します。
```env
DISCORD_TOKEN=your_bot_token_here
PORT=8080
```


4. **起動**:
```bash
python main.py
```