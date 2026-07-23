# 🛠️ 詳細技術仕様書 (TECHNICAL.md)

本ドキュメントは、**Tukinoma Bot** のシステムアーキテクチャ、データ構造、および各モジュール（特に `cogs` 配下）の内部実装仕様を詳細に定義した設計書です。  
開発者がソースコードの挙動を完全に理解し、メンテナンスや新機能追加をスムーズに行えるレベルの記述を行っています。

---

## 1. 全体アーキテクチャ（設計思想）

Bot全体の基本構造は**「機能ごとの完全分離（疎結合）」**と**「データアクセスのカプセル化」**を軸に設計されています。

### 💡 設計方針とメリット

1. **Cogによる機能のコンポーネント化 (`discord.ext.commands.Cog`)**
   - VC通知機能やモデレーション機能をそれぞれ独立したクラス（Cog）として実装。
   - 各Cogは独立してロード/アンロードが可能で、特定機能のバグがBot全体をクラッシュさせない構造。

2. **データ管理層の抽象化 (`ConfigManager`)**
   - 各Cogはファイル（`data/*.json`）へ直接アクセスせず、必ず `self.bot.config_manager` を経由する。
   - 将来的に保存先を JSON から SQLite や Redis へ変更する場合も、`ConfigManager` クラスの内部実装を変更するだけで対応可能（Cog側のコード修正不要）。

3. **機能別データ空間の分離**
   - `data/` ディレクトリ内に `vc_notifier.json` や `moderation.json` のように機能単位でファイルを分離。
   - 1つのファイルの破損やバッティングが他機能に波及しないリスクヘッジ構造。

---

## 2. データ構造仕様 (Data Schemas)

### 📦 保存ファイル: `data/vc_notifier.json`

VC通知機能で保持する永続化データの完全な JSON スキーマ定義です。

```json
{
  "Guild ID": {
    "Target VC Channel ID": {
      "notify_channel_id": ,
      "mention_type": "",
      "mention_role_id": 
    }
  }
}

```

### 🔍 フィールド定義一覧

| 階層 / フィールド名 | 型 | 必須 | 説明・制約 |
| --- | --- | --- | --- |
| **ルート (Key)** | `string` | Yes | **Guild ID (サーバーID)**。文字列型（Python側で `str(guild.id)` 変換）。 |
| **第2階層 (Key)** | `string` | Yes | **Target VC Channel ID**。監視対象となるボイスチャンネルのID。 |
| └ `notify_channel_id` | `integer` | Yes | **Notify Text Channel ID**。通知を送信するテキストチャンネルのID。 |
| └ `mention_type` | `string` | Yes | メンション種別。許容値: `"none"`, `"user"`, `"everyone"`, `"role"` |
| └ `mention_role_id` | `integer` | Yes | メンション対象のロールID。`mention_type == "role"` のみ `int`、それ以外は `null`。 |

---

## 3. モジュール内部仕様 (Internal Module Specifications)

---

### 3.1 `main.py` (エントリーポイント)

Botのブートストラップ処理、Intentsの設定、依存オブジェクトの注入、Cogの動的ロードを行います。

#### 内部構造 & 処理フロー

1. **`MyBot(commands.Bot)` クラスの初期化**
* `__init__` 内で `self.config_manager = ConfigManager()` を生成し、Botインスタンスに保持させる。


2. **`on_ready()` イベント**
* ログイン成功時に発火。
* 参加中の全ギルドをループ処理し、`bot.tree.copy_global_to(guild=guild)` ➔ `bot.tree.sync(guild=guild)` を実行してギルドごとのコマンド即時反映を行う。


3. **`load_extensions()` 関数**
* `./cogs` ディレクトリ内の `.py` ファイルを走査し、`bot.load_extension(f"cogs.{filename[:-3]}")` で動的にロード。



---

### 3.2 `utils/config_manager.py` (データアクセス層)

設定データの読み込み・保存を一括管理するユーティリティクラスです。

#### クラス定義: `ConfigManager`

* **属性**:
* `data_dir` (`Path`): データ保存用ディレクトリのパス（既定値: `"data"`）。インスタンス化時に自動作成される。



#### メソッド詳細

* **`load(feature_name: str) -> dict`**
* **処理**: `data/{feature_name}.json` を検索。存在すれば JSON 形式で読み込んで辞書で返す。存在しない、またはファイル読み込みエラー時は空辞書 `{}` を返す。


* **`save(feature_name: str, data: dict) -> None`**
* **処理**: 渡された辞書データを `data/{feature_name}.json` へ UTF-8 エンコード・インデント 4 スペースでアトミックに保存する。



---

### 3.3 `cogs/vc_notifier.py` (VC通知機能)

ボイスチャンネルへの接続・切断イベントを検知し、埋め込みメッセージ（Embed）およびメンションを出力するメイン Cog です。

#### クラス構成

1. **`VCGroup(app_commands.Group)`**: `/vc` スラッシュコマンドグループの定義
2. **`VCNotifier(commands.Cog)`**: イベントリスナーとデータ操作の実装

---

#### 1. `VCGroup(app_commands.Group)` コマンド内部仕様

* **親コマンド**: `/vc`
* **初期化**: `__init__(self, cog: VCNotifier)` で親 Cog の参照（`self.cog`）を保持。

##### ① `add` サブコマンド (`/vc add`)

* **シグネチャ**: `add(interaction, vc: VoiceChannel, text_channel: TextChannel, mention_type: str = "none", role_to_mention: Role = None)`
* **処理フロー**:
1. `interaction.user.guild_permissions.administrator` を検証。権限なしならエラー応答して終了。
2. `self.cog.get_data()` で現在の設定を取得。
3. `data[str(guild_id)][str(vc.id)]` に `notify_channel_id`, `mention_type`, `mention_role_id` をセット。
4. `self.cog.save_data(data)` でファイルへ保存。
5. 成功を知らせる Embed メッセージ（緑色: `#57F287`）を `interaction.response.send_message` で送信。



##### ② `list` サブコマンド (`/vc list`)

* **シグネチャ**: `list(interaction)`
* **処理フロー**:
1. 該当ギルドの設定データを参照。存在しない場合は「設定なし」の警告メッセージを返答。
2. 登録されている各 VC の「監視対象VC」「通知先チャンネル」「メンション設定」をループ処理で取得し、Embed 形式（青色: `#3498DB`）で一覧化して送信。



##### ③ `remove` サブコマンド (`/vc remove`)

* **シグネチャ**: `remove(interaction, vc: VoiceChannel)`
* **処理フロー**:
1. 管理者権限をチェック。
2. `data[str(guild_id)]` 内から指定された `str(vc.id)` のキーを削除（`del`）。
3. 変更後のデータを保存し、削除完了メッセージを送信。



##### ④ `clear` サブコマンド (`/vc clear`)

* **シグネチャ**: `clear(interaction)`
* **処理フロー**:
1. 管理者権限をチェック。
2. `data[str(guild_id)]` の要素を丸ごと削除し、全削除された件数を算出。
3. データを保存し、削除完了を伝える Embed メッセージ（赤色: `#ED4245`）を送信。



---

#### 2. `VCNotifier(commands.Cog)` イベント内部仕様

##### 定数 / 内部ヘルパーメソッド

* **`FEATURE_NAME = "vc_notifier"`**: `ConfigManager` が使用する識別子。
* **`get_data(self) -> dict`**: `self.bot.config_manager.load(self.FEATURE_NAME)` を呼んでデータを返却。
* **`save_data(self, data: dict) -> None`**: `self.bot.config_manager.save(self.FEATURE_NAME, data)` でデータを保存。
* **`get_mention_text(self, member: Member, vc_setting: dict) -> str`**:
* `mention_type` に基づいてメンション文字列を生成。
* `"user"` ➔ `<@member.id>`, `"everyone"` ➔ `@everyone`, `"role"` ➔ `<@&role_id>`, `"none"` ➔ `""`



##### イベントハンドラー: `on_voice_state_update(member, before, after)`

ユーザーのボイスチャンネル接続状態が変化した際に発火するコアリスナーです。

* **ガード文**: `member.bot` が `True` の場合は即座に処理をスキップ（Botの動作に反応させない）。
* **接続（参加）判定ロジック**:
* **条件**: `after.channel` が存在し、その ID が設定データ内に存在、かつ `before.channel != after.channel` であること。
* **処理**:
1. 該当する通知テキストチャンネルを取得 (`member.guild.get_channel(...)`)。
2. `get_mention_text()` でメンション文字列を生成。
3. 参加用 Embed（タイトル: 「VCに接続しました」、色: 緑 `#57F287`、アバター画像サムネイル付き、接続タイムスタンプ `<t:timestamp:F>`）を生成。
4. `notify_channel.send(content=mention_text, embed=embed)` でメッセージ送信。




* **切断（退出）判定ロジック**:
* **条件**: `before.channel` が存在し、その ID が設定データ内に存在、かつ `after.channel != before.channel` であること。
* **処理**:
1. 該当する通知テキストチャンネルを取得。
2. 退出用 Embed（タイトル: 「VCから切断しました」、色: 赤 `#ED4245`）を生成。
3. `notify_channel.send(content=mention_text, embed=embed)` でメッセージ送信。





---

### 3.4 `cogs/moderation.py` (モデレーション機能)

テキストチャンネル内のログ削除・管理を行う Cog です。

#### クラス定義: `Moderation(commands.Cog)`

##### スラッシュコマンド: `clear_messages` (`/clear`)

* **シグネチャ**: `clear_messages(interaction, amount: int)`
* **オプション**: `amount` (削除件数: 1〜100)
* **内部処理フロー**:
1. **権限検証**: `interaction.user.guild_permissions.manage_messages` をチェック。無ければ ❌ 警告を応答。
2. **範囲検証**: `amount < 1` または `amount > 100` の場合、警告を返答。
3. **非同期延期**: 削除処理に時間がかかる場合に備え、`await interaction.response.defer(ephemeral=True)` で応答時間を確保。
4. **一括削除実行**: `deleted = await interaction.channel.purge(limit=amount)` を呼び出し、実際に削除されたメッセージオブジェクトのリストを取得。
5. **レスポンス**: `interaction.followup.send()` を使用し、実行ユーザーにのみ見える形式（`ephemeral=True`）で「🧹 **X件** のメッセージを削除しました」と応答。



##### 例外処理ハンドリング

* **`discord.Forbidden`**: Bot自身に「メッセージの管理」や「メッセージ履歴の閲覧」権限が無い場合を捕捉し、エラー理由をユーザーへ表示。
* **`discord.HTTPException`**: 14日以上経過したメッセージの一括削除失敗など、Discord API 側のエラーを捕捉してメッセージを返答。

---

## 4. 拡張時の開発ルール

新しく機能を追加・改修する際は、以下の設計ルールに従ってください。

1. **データ構造の破壊的変更**:
スキーマ構造を変更する場合は、既存の `data/*.json` との互換性を考慮するか、自動データ移行（マイグレーション）スクリプトを用意すること。
2. **Discord API 制限対策**:
大量のメッセージ送信や一括削除を行う際は、`defer()` や `ephemeral` 応答を適切に組み込み、3秒タイムアウト制限（Discord Interaction Timeout）を回避すること。
3. **エラーの可視化**:
`Forbidden` や `HTTPException` などの主要例外は捕捉し、一般ユーザーおよび管理者へ直感的なエラーメッセージを返すこと。