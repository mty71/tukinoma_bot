import asyncio
import datetime
import os
import uuid
import discord
from discord import app_commands
from discord.ext import commands, tasks
from utils.audio_downloader import AudioDownloader


# /alarm コマンドグループ
class AlarmGroup(app_commands.Group):

    def __init__(self, cog: "Alarm"):
        super().__init__(
            name="alarm", description="アラーム設定に関するコマンド群"
        )
        self.cog = cog
        self.downloader = AudioDownloader()

    # 1. アラーム追加 (/alarm add)
    @app_commands.command(
        name="add", description="指定時間にVCで音楽を流すアラームを追加します"
    )
    @app_commands.describe(
        vc="アラームを鳴らすボイスチャンネル",
        time_str="鳴らす時刻 (例: 07:30)",
        youtube_url="再生したいYouTubeのURL",
        audio_file="再生したい音声ファイル (MP3等)",
    )
    async def add(
        self,
        interaction: discord.Interaction,
        vc: discord.VoiceChannel,
        time_str: str,
        youtube_url: str = None,
        audio_file: discord.Attachment = None,
    ):
        if not interaction.user.guild_permissions.administrator:
            await interaction.response.send_message(
                "❌ 管理者権限が必要です。", ephemeral=True
            )
            return

        # 音源チェック
        if not youtube_url and not audio_file:
            await interaction.response.send_message(
                "⚠️ `youtube_url` または `audio_file` のどちらかを指定してください。",
                ephemeral=True,
            )
            return

        # 時刻フォーマットチェック (HH:MM)
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

        # 音源のダウンロード・保存
        if audio_file:
            local_path = f"data/audio/{alarm_id}_{audio_file.filename}"
            await audio_file.save(local_path)
        elif youtube_url:
            local_path = self.downloader.download_youtube_audio(
                youtube_url, alarm_id
            )

        # データの保存
        guild_id = str(interaction.guild_id)
        data = self.cog.get_data()
        if guild_id not in data:
            data[guild_id] = []

        data[guild_id].append(
            {
                "id": alarm_id,
                "time": time_str,
                "vc_channel_id": vc.id,
                "local_file_path": local_path,
                "enabled": True,
            }
        )
        self.cog.save_data(data)

        embed = discord.Embed(
            title="⏰ アラームを設定しました", color=0x57F287
        )
        embed.add_field(name="時刻", value=f"`{time_str}`", inline=True)
        embed.add_field(name="対象VC", value=f"<#{vc.id}>", inline=True)
        embed.add_field(name="ID", value=f"`{alarm_id}`", inline=False)
        await interaction.followup.send(embed=embed, ephemeral=True)

    # 2. アラーム一覧 (/alarm list)
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
            embed.add_field(
                name=f"🕒 {alarm.get('time')} (ID: `{alarm.get('id')}`)",
                value=(
                    f"└ **VC**: <#{alarm.get('vc_channel_id')}>\n"
                    f"└ **音源**: `{file_name}`"
                ),
                inline=False,
            )

        await interaction.response.send_message(embed=embed)

    # 3. アラーム削除 (/alarm remove)
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

        # 指定IDを検索して削除
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

        # ローカル音源ファイルの削除
        audio_path = target_alarm.get("local_file_path", "")
        if audio_path and os.path.exists(audio_path):
            try:
                os.remove(audio_path)
            except Exception as e:
                print(f"⚠️ ファイル削除エラー: {e}")

        await interaction.response.send_message(
            f"🗑️ アラーム `{alarm_id}` ({target_alarm.get('time')}) を削除しました。"
        )


# Cog本体
class Alarm(commands.Cog):
    FEATURE_NAME = "alarms"

    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.alarm_group = AlarmGroup(self)
        self.bot.tree.add_command(self.alarm_group)
        self.check_alarms.start()

    def cog_unload(self):
        self.bot.tree.remove_command(self.alarm_group.name)
        self.check_alarms.cancel()

    def get_data(self) -> dict:
        return self.bot.config_manager.load(self.FEATURE_NAME)

    def save_data(self, data: dict) -> None:
        self.bot.config_manager.save(self.FEATURE_NAME, data)

    # アラーム監視ループ
    @tasks.loop(seconds=30)
    async def check_alarms(self):
        now = datetime.datetime.now()
        current_time = now.strftime("%H:%M")

        data = self.get_data()
        for guild_id, alarm_list in data.items():
            guild = self.bot.get_guild(int(guild_id))
            if not guild:
                continue

            for alarm in alarm_list:
                if not alarm.get("enabled", True):
                    continue

                if alarm.get("time") == current_time:
                    self.bot.loop.create_task(
                        self.play_alarm(guild, alarm)
                    )

    @check_alarms.before_loop
    async def before_check_alarms(self):
        await self.bot.wait_until_ready()

    async def play_alarm(self, guild: discord.Guild, alarm: dict):
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

        if not voice_client.is_playing():
            audio_source = discord.FFmpegPCMAudio(audio_path)
            voice_client.play(
                audio_source,
                after=lambda e: asyncio.run_coroutine_threadsafe(
                    voice_client.disconnect(), self.bot.loop
                ),
            )


async def setup(bot: commands.Bot):
    await bot.add_cog(Alarm(bot))