import asyncio
import datetime
import os
import discord
from discord.ext import commands, tasks


class Alarm(commands.Cog):
    FEATURE_NAME = "alarms"

    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.check_alarms.start()

    def cog_unload(self):
        self.check_alarms.cancel()

    def get_data(self) -> dict:
        return self.bot.config_manager.load(self.FEATURE_NAME)

    # ----------------------------------------------------
    # アラーム監視タスク（毎分00秒に判定）
    # ----------------------------------------------------
    @tasks.loop(seconds=30)
    async def check_alarms(self):
        now = datetime.datetime.now()
        current_time = now.strftime("%H:%M")
        current_weekday = now.weekday()  # 0:月 ~ 6:日

        data = self.get_data()
        for guild_id, alarm_list in data.items():
            guild = self.bot.get_guild(int(guild_id))
            if not guild:
                continue

            for alarm in alarm_list:
                if not alarm.get("enabled", True):
                    continue

                # 曜日指定がある場合の判定
                repeat_days = alarm.get("repeat_days", [])
                if repeat_days and current_weekday not in repeat_days:
                    continue

                # 時刻一致でアラーム再生
                if alarm.get("time") == current_time:
                    self.bot.loop.create_task(
                        self.play_alarm(guild, alarm)
                    )

    @check_alarms.before_loop
    async def before_check_alarms(self):
        await self.bot.wait_until_ready()

    # ----------------------------------------------------
    # VC接続 ＆ 再生ロジック
    # ----------------------------------------------------
    async def play_alarm(self, guild: discord.Guild, alarm: dict):
        vc_id = alarm.get("vc_channel_id")
        audio_path = alarm.get("local_file_path")

        if not vc_id or not audio_path or not os.path.exists(audio_path):
            return

        vc_channel = guild.get_channel(int(vc_id))
        if not isinstance(vc_channel, discord.VoiceChannel):
            return

        # VCに接続（すでに接続済みの場合は移動）
        voice_client = guild.voice_client
        if voice_client:
            if voice_client.channel.id != vc_channel.id:
                await voice_client.move_to(vc_channel)
        else:
            voice_client = await vc_channel.connect()

        # 音声再生 (FFmpeg)
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