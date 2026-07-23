# 🛠️ 詳細技術仕様書 (TECHNICAL.md)

本ドキュメントは、**Tukinoma Bot** のシステムアーキテクチャ、データ構造、および各モジュール（特に `cogs` や `web_server` 配下）の内部実装仕様を詳細に定義した設計書です。  
開発者がソースコードの挙動を完全に理解し、メンテナンスや新機能追加をスムーズに行えるレベルの記述を行っています。

---

## 1. 全体アーキテクチャ（設計思想）

Bot全体の基本構造は**「機能ごとの完全分離（疎結合）」**、**「データアクセスのカプセル化」**、および**「Discord BotとWebUIの非同期並列起動」**を軸に設計されています。

### 💡 設計方針とメリット

1. **Cogによる機能のコンポーネント化 (`discord.ext.commands.Cog`)**
   - VC通知機能、モデレーション機能、アラーム再生機能をそれぞれ独立したクラス（Cog）として実装。
2. **データ管理層の抽象化 (`ConfigManager`)**
   - 各CogおよびWebサーバーはファイル（`data/*.json`）へ直接アクセスせず、必ず `ConfigManager` を経由する。
3. **WebUIとの非同期並列プロセス (`FastAPI` + `uvicorn`)**
   - Discord Bot (Asyncio Loop) と並行して FastAPI サーバーを起動。
   - `.env` の `PORT` 環境変数でバインドポートを動的に変更可能。

---

## 2. データ構造仕様 (Data Schemas)

### 📦 1. `data/vc_notifier.json` (VC通知設定)
```json
{
  "111111111111111111": {
    "222222222222222222": {
      "notify_channel_id": 333333333333333333,
      "mention_type": "role",
      "mention_role_id": 999888777666555444
    },
    "444444444444444444": {
      "notify_channel_id": 333333333333333333,
      "mention_type": "none",
      "mention_role_id": null
    }
  }
}

```

#### 🔍 フィールド定義一覧

| 階層 / フィールド名 | 型 | 必須 | 説明・制約 |
| --- | --- | --- | --- |
| **ルート (Key)** | `string` | Yes | **Guild ID (サーバーID)**。文字列型。 |
| **第2階層 (Key)** | `string` | Yes | **Target VC Channel ID**。監視対象のボイスチャンネルID。 |
| └ `notify_channel_id` | `integer` | Yes | **Notify Text Channel ID**。通知を出力するテキストチャンネルID。 |
| └ `mention_type` | `string` | Yes | メンション種別 (`"none"`, `"user"`, `"everyone"`, `"role"`) |
| └ `mention_role_id` | `integer | null` | Yes | ロールメンション時のロールID（指定なし・ロール以外は `null`）。 |

---

### 📦 2. `data/alarms.json` (アラーム設定)

```json
{
  "111111111111111111": [
    {
      "id": "alarm_a1b2c3d4",
      "time": "07:30",
      "vc_channel_id": 222222222222222222,
      "local_file_path": "data/audio/alarm_a1b2c3d4.mp3",
      "enabled": true
    }
  ]
}

```

---

## 3. モジュール内部仕様 (Internal Module Specifications)

---

### 3.1 `main.py` (エントリーポイント)

Botのブートストラップ処理、Intentsの設定、Cogの動的ロード、およびWebUIサーバーの並列起動を行います。

* **`main()` 関数**:
* `asyncio.create_task(run_web_server())` を呼び出し、Botの接続処理 (`bot.start`) と同時にWebUIサーバーを非同期タスクとして立ち上げる。


* **環境変数**:
* `DISCORD_TOKEN`: Discord Bot Token
* `PORT`: WebUIサーバーのポート番号（未指定時: `8000`）



---

### 3.2 `web_server.py` & `templates/index.html` (WebUI & API)

FastAPI を使用した設定画面およびリクエスト受付APIです。

* **`run_web_server()`**: `.env` から `PORT` を読み込み、`uvicorn.Server` を非同期実行。
* **`GET /`**: `templates/index.html` をレンダリングし、現在登録されているアラーム一覧を表示。
* **`POST /api/alarm/add`**:
* フォームデータ (`guild_id`, `vc_id`, `time_str`, `youtube_url`, `audio_file`) を受信。
* `audio_file` 添付時は `data/audio/` へ直接保存。
* `youtube_url` 指定時は `AudioDownloader` を使用して mp3 に変換保存。
* 設定を `data/alarms.json` へ追記保存。



---

### 3.3 `utils/audio_downloader.py` (YouTube音声抽出)

`yt-dlp` をカプセル化した音声ダウンロードモジュールです。

* **`download_youtube_audio(url: str, alarm_id: str) -> str`**:
* `FFmpegExtractAudio` ポストプロセッサを使用し、YouTube動画から 192kbps の MP3 を抽出。
* 出力パス `data/audio/{alarm_id}.mp3` を返却。



---

### 3.4 `cogs/alarm.py` (アラーム監視・自動再生)

指定時刻にボイスチャンネルへ接続して音声を再生する Cog です。

* **`check_alarms` タスク (`@tasks.loop(seconds=30)`)**:
* 毎分、現在時刻 (`HH:MM`) と一致する有効なアラームを走査。


* **`play_alarm(guild, alarm)`**:
* 指定された `vc_channel_id` へ Bot が接続（接続済みの場合は移動）。
* `discord.FFmpegPCMAudio` を用いてローカルファイルを再生。
* 再生終了時に自動で VC から切断 (`voice_client.disconnect()`)。
### 3.4 `cogs/alarm.py` (アラーム機能)
- **親コマンド**: `/alarm`
- **サブコマンド**:
  - `add`: `vc`, `time_str` (HH:MM), `youtube_url` または `audio_file` (Attachment) を受け取り登録。
  - `list`: 現在のサーバーのアラーム一覧と ID を表示。
  - `remove`: `alarm_id` を指定して設定および実体ファイル (`data/audio/*`) を削除。
- **タスク処理**: `@tasks.loop(seconds=30)` で毎分 `HH:MM` を判定し、VCへ接続して `FFmpegPCMAudio` で自動再生。


---

### 3.5 `cogs/vc_notifier.py` (VC通知機能)

ボイスチャンネルへの接続・切断イベントを検知し、通知を出力する Cog です。

* **親コマンド**: `/vc`
* **サブコマンド**: `add`, `list`, `remove`, `clear`
* **`on_voice_state_update`**: `before` と `after` の状態変化を検証し、接続（緑Embed）/切断（赤Embed）をリアルタイム出力。

---

### 3.6 `cogs/moderation.py` (モデレーション機能)

* **コマンド**: `/clear <amount: int>` (1〜100件)
* **内部処理**: 権限検証・範囲チェック後、`channel.purge()` でメッセージを一括削除し、実行ユーザーにのみ見える形式（`ephemeral`）で応答。

---

## 4. 拡張時の開発ルール

1. **音声再生依存関係**:
実行環境に `ffmpeg` コマンドがインストールされている必要があります。
2. **非同期ブロッキング回避**:
YouTubeからのダウンロード処理などの重い処理は、非同期APIハンドラー内で適切にハンドリングすること。
3. **ポート競合**:
`.env` で指定する `PORT` 番号が他サービスと衝突しないよう注意すること。