import asyncio
import datetime
import os
import uuid
import discord
from discord import app_commands
from discord.ext import commands, tasks

# JST (日本時間) の定義
try:
    import zoneinfo
    JST = zoneinfo.ZoneInfo("Asia/Tokyo")
except ImportError:
    import pytz
    JST = pytz.timezone("Asia/Tokyo")

from utils.audio_downloader import AudioDownloader


# ----------------------------------------------------
# 1. アラーム停止用 UI ボタン (Discord Message Component)
# ----------------------------------------------------
class AlarmStopView(discord.ui.View):

    def __init__(self, cog: "Alarm", guild: discord.Guild, timeout: float = 300):
        super().__init__(timeout=timeout)
        self.cog = cog
        self.guild = guild

    @discord.ui.button(
        label="アラームを止める",
        style=discord.ButtonStyle.danger,
        emoji="🛑",
    )
    async def stop_button(
        self, interaction: discord.Interaction, button: discord.ui.Button
    ):
        stopped = await self.cog.stop_alarm_for_guild(self.guild)

        button.disabled = True
        button.label = "停止済み"
        button.style = discord.ButtonStyle.secondary

        if stopped:
            await interaction.response.edit_message(
                content=f"⏹️ **{interaction.user.display_name}** がアラームを停止しました。",
                view=self,
            )
        else:
            await interaction.response.edit_message(
                content="⚠️ 既にアラームは停止されています。", view=self
            )


# ----------------------------------------------------
# 2. /alarm コマンドグループ
# ----------------------------------------------------
class AlarmGroup(app_commands.Group):

    def __init__(self, cog: "Alarm"):
        super().__init__(
            name="alarm", description="アラーム設定に関するコマンド群"
        )
        self.cog = cog
        self.downloader = AudioDownloader()

    @app_commands.command(
        name="add", description="指定時間にVCで音楽を流すアラームを追加します"
    )
    @app_commands.describe(
        vc="アラームを鳴らすボイスチャンネル",
        time_str="鳴らす時刻 (例: 07:30)",
        mode="再生モード (repeat: 繰り返し, once: 1回のみ)",
        youtube_url="再生したいYouTubeのURL",
        audio_file="再生したい音声ファイル (MP3等)",
    )
    @app_commands.choices(
        mode=[
            app_commands.Choice(name="繰り返し（毎日）", value="repeat"),
            app_commands.Choice(name="1回のみ（再生後自動削除）", value="once"),
        ]
    )
    async def add(
        self,
        interaction: discord.Interaction,
        vc: discord.VoiceChannel,
        time_str: str,
        mode: str = "repeat",
        youtube_url: str = None,
        audio_file: discord.Attachment = None,
    ):
        if not interaction.user.guild_permissions.administrator:
            await interaction.response.send_message(
                "❌ 管理者権限が必要です。", ephemeral=True
            )
            return

        if not youtube_url and not audio_file:
            await interaction.response.send_message(
                "⚠️ `youtube_url` または `audio_file` のどちらかを指定してください。",
                ephemeral=True,
            )
            return

        try:
            datetime.datetime.strptime(time_str, "%H:%M")
        except ValueError:
            await interaction.response.send_message(
                "⚠️ 時刻は `07:30` のように `HH:MM` 形式で指定してください。",
                ephemeral=True,
            )
            return

        await interaction.response.defer(ephemeral=True)

        alarm_id = f"alarm_{uuid.uuid4().hex[:8]}"
        local_path = ""

        if audio_file:
            local_path = f"data/audio/{alarm_id}_{audio_file.filename}"
            os.makedirs(os.path.dirname(local_path), exist_ok=True)
            await audio_file.save(local_path)
        elif youtube_url:
            local_path = self.downloader.download_youtube_audio(
                youtube_url, alarm_id
            )

        guild_id = str(interaction.guild_id)
        data = self.cog.get_data()
        if guild_id not in data:
            data[guild_id] = []

        data[guild_id].append(
            {
                "id": alarm_id,
                "time": time_str,
                "mode": mode,
                "vc_channel_id": vc.id,
                "local_file_path": local_path,
                "enabled": True,
                "last_triggered": None,
            }
        )
        self.cog.save_data(data)

        mode_text = "🔄 繰り返し" if mode == "repeat" else "1️⃣ 1回のみ"
        embed = discord.Embed(
            title="⏰ アラームを設定しました", color=0x57F287
        )
        embed.add_field(name="時刻", value=f"`{time_str}`", inline=True)
        embed.add_field(name="モード", value=mode_text, inline=True)
        embed.add_field(name="対象VC", value=f"<#{vc.id}>", inline=False)
        embed.add_field(name="ID", value=f"`{alarm_id}`", inline=False)
        await interaction.followup.send(embed=embed, ephemeral=True)

    @app_commands.command(
        name="list", description="設定されているアラーム一覧を表示します"
    )
    async def list(self, interaction: discord.Interaction):
        guild_id = str(interaction.guild_id)
        data = self.cog.get_data()

        if guild_id not in data or not data[guild_id]:
            await interaction.response.send_message(
                "⚠️ 設定されているアラームはありません。", ephemeral=True
            )
            return

        embed = discord.Embed(
            title="⏰ アラーム設定一覧", color=0x3498DB
        )

        for alarm in data[guild_id]:
            file_name = os.path.basename(alarm.get("local_file_path", ""))
            mode_str = "🔄 繰り返し" if alarm.get("mode", "repeat") == "repeat" else "1️⃣ 1回のみ"
            embed.add_field(
                name=f"🕒 {alarm.get('time')} ({mode_str})",
                value=(
                    f"└ **ID**: `{alarm.get('id')}`\n"
                    f"└ **VC**: <#{alarm.get('vc_channel_id')}>\n"
                    f"└ **音源**: `{file_name}`"
                ),
                inline=False,
            )

        await interaction.response.send_message(embed=embed)

    @app_commands.command(
        name="remove", description="指定したIDのアラームを削除します"
    )
    @app_commands.describe(alarm_id="削除するアラームのID (/alarm listで確認)")
    async def remove(
        self, interaction: discord.Interaction, alarm_id: str
    ):
        if not interaction.user.guild_permissions.administrator:
            await interaction.response.send_message(
                "❌ 管理者権限が必要です。", ephemeral=True
            )
            return

        guild_id = str(interaction.guild_id)
        data = self.cog.get_data()

        if guild_id not in data or not data[guild_id]:
            await interaction.response.send_message(
                "⚠️ 削除対象のアラームが存在しません。", ephemeral=True
            )
            return

        target_alarm = None
        new_list = []
        for alarm in data[guild_id]:
            if alarm.get("id") == alarm_id:
                target_alarm = alarm
            else:
                new_list.append(alarm)

        if not target_alarm:
            await interaction.response.send_message(
                f"⚠️ ID `{alarm_id}` のアラームが見つかりませんでした。",
                ephemeral=True,
            )
            return

        data[guild_id] = new_list
        self.cog.save_data(data)

        audio_path = target_alarm.get("local_file_path", "")
        if audio_path and os.path.exists(audio_path):
            try:
                os.remove(audio_path)
            except Exception as e:
                print(f"⚠️ ファイル削除エラー: {e}")

        await interaction.response.send_message(
            f"🗑️ アラーム `{alarm_id}` ({target_alarm.get('time')}) を削除しました。"
        )

    @app_commands.command(
        name="stop", description="現在再生中のアラームを停止してVCから退出します"
    )
    async def stop(self, interaction: discord.Interaction):
        guild = interaction.guild
        if not guild:
            return

        stopped = await self.cog.stop_alarm_for_guild(guild)
        if stopped:
            await interaction.response.send_message(
                "⏹️ アラームを停止し、VCから切断しました。"
            )
        else:
            await interaction.response.send_message(
                "⚠️ 現在再生中のアラームはありません。", ephemeral=True
            )


# ----------------------------------------------------
# 3. Cog本体 (監視 & 再生 & 制御)
# ----------------------------------------------------
class Alarm(commands.Cog):
    FEATURE_NAME = "alarms"

    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.alarm_group = AlarmGroup(self)
        self.bot.tree.add_command(self.alarm_group)
        self.active_alarms = {}
        self.check_alarms.start()

    def cog_unload(self):
        self.bot.tree.remove_command(self.alarm_group.name)
        self.check_alarms.cancel()

    def get_data(self) -> dict:
        return self.bot.config_manager.load(self.FEATURE_NAME)

    def save_data(self, data: dict) -> None:
        self.bot.config_manager.save(self.FEATURE_NAME, data)

    async def stop_alarm_for_guild(self, guild: discord.Guild) -> bool:
        guild_id = guild.id
        self.active_alarms[guild_id] = False

        voice_client = guild.voice_client
        if voice_client:
            if voice_client.is_playing():
                voice_client.stop()
            await voice_client.disconnect()
            return True
        return False

    # ====================================================
    # 🔑 アラーム監視・自動削除・重複発火防止ループ（JST固定版）
    # ====================================================
    @tasks.loop(seconds=5)
    async def check_alarms(self):
        # 🔑 日本時間 (JST) で現在時刻を取得
        now = datetime.datetime.now(JST)
        current_time = now.strftime("%H:%M")     # 例: "14:30"
        current_date = now.strftime("%Y-%m-%d") # 例: "2026-07-23"

        data = self.get_data()
        updated = False

        for guild_id_str, alarm_list in data.items():
            guild = self.bot.get_guild(int(guild_id_str))
            if not guild:
                continue

            new_alarm_list = []
            guild_updated = False

            for alarm in alarm_list:
                if not alarm.get("enabled", True):
                    new_alarm_list.append(alarm)
                    continue

                alarm_time = alarm.get("time")
                alarm_mode = alarm.get("mode", "repeat")
                last_triggered = alarm.get("last_triggered")

                # 【トリガー判定】
                # 時刻が一致し、かつ本日の日付と last_triggered が異なる場合のみ発火
                if current_time == alarm_time and last_triggered != current_date:
                    if not self.active_alarms.get(guild.id, False):
                        self.bot.loop.create_task(
                            self.play_alarm_loop(guild, alarm)
                        )

                    # 発火済みフラグとして「今日の日付 (YYYY-MM-DD)」をセット
                    alarm["last_triggered"] = current_date
                    guild_updated = True
                    updated = True

                    # 1回のみ（once）の場合は保存リストから外す（削除）
                    if alarm_mode == "once":
                        audio_path = alarm.get("local_file_path")
                        if audio_path and os.path.exists(audio_path):
                            try:
                                os.remove(audio_path)
                            except Exception as e:
                                print(f"⚠️ 1回きりアラーム音声ファイル削除エラー: {e}")
                        continue  # 新しいリストに入れないことで削除

                new_alarm_list.append(alarm)

            if guild_updated:
                data[guild_id_str] = new_alarm_list

        if updated:
            self.save_data(data)

    @check_alarms.before_loop
    async def before_check_alarms(self):
        await self.bot.wait_until_ready()

    # 🛑 対象VC内テキストチャットへ停止ボタンメッセージを送信
    async def send_alarm_message(self, guild: discord.Guild, vc_channel: discord.VoiceChannel, alarm: dict):
        try:
            embed = discord.Embed(
                title="⏰ アラームが鳴っています！",
                description=f"<#{vc_channel.id}> で指定時刻 (`{alarm.get('time')}`) の音楽を再生中です。\n下のボタンを押すとアラームを停止します。",
                color=0xED4245,
            )
            view = AlarmStopView(cog=self, guild=guild)
            await vc_channel.send(embed=embed, view=view)
        except Exception as e:
            print(f"⚠️ VCテキストメッセージ送信エラー: {e}")

    # 無限ループ再生ロジック
    async def play_alarm_loop(self, guild: discord.Guild, alarm: dict):
        vc_id = alarm.get("vc_channel_id")
        audio_path = alarm.get("local_file_path")

        if not vc_id or not audio_path or not os.path.exists(audio_path):
            return

        vc_channel = guild.get_channel(int(vc_id))
        if not isinstance(vc_channel, discord.VoiceChannel):
            return

        voice_client = guild.voice_client
        if voice_client:
            if voice_client.channel.id != vc_channel.id:
                await voice_client.move_to(vc_channel)
        else:
            voice_client = await vc_channel.connect()

        self.active_alarms[guild.id] = True

        # 対象VCのチャット欄にボタンを送信
        await self.send_alarm_message(guild, vc_channel, alarm)

        while self.active_alarms.get(guild.id, False) and voice_client.is_connected():
            if not voice_client.is_playing():
                audio_source = discord.FFmpegPCMAudio(audio_path)
                voice_client.play(audio_source)

            await asyncio.sleep(1)

        self.active_alarms[guild.id] = False


async def setup(bot: commands.Bot):
    await bot.add_cog(Alarm(bot))