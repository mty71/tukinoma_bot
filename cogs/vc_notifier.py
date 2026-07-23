import json
import os
import time
import discord
from discord import app_commands
from discord.ext import commands

CONFIG_FILE = "config.json"


class VCNotifier(commands.Cog):

    def __init__(self, bot: commands.Bot):
        self.bot = bot

    def load_config(self) -> dict:
        if os.path.exists(CONFIG_FILE):
            with open(CONFIG_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        return {}

    def save_config(self, config: dict):
        with open(CONFIG_FILE, "w", encoding="utf-8") as f:
            json.dump(config, f, indent=4)

    @app_commands.command(
        name="vc_setup", description="VC通知の接続先と通知チャンネルを設定します"
    )
    @app_commands.describe(
        vc="監視したいボイスチャンネル",
        text_channel="通知を送信するテキストチャンネル",
    )
    async def vc_setup(
        self,
        interaction: discord.Interaction,
        vc: discord.VoiceChannel,
        text_channel: discord.TextChannel,
    ):
        if not interaction.user.guild_permissions.administrator:
            await interaction.response.send_message(
                "❌ 管理者権限が必要です。", ephemeral=True
            )
            return

        guild_id = str(interaction.guild_id)
        config = self.load_config()

        config[guild_id] = {
            "target_vc_id": vc.id,
            "notify_channel_id": text_channel.id,
        }
        self.save_config(config)

        embed = discord.Embed(
            title="⚙️ VC通知設定を更新しました", color=0x57F287
        )
        embed.add_field(name="監視対象VC", value=f"<#{vc.id}>", inline=False)
        embed.add_field(
            name="通知先チャンネル", value=f"<#{text_channel.id}>", inline=False
        )

        await interaction.response.send_message(embed=embed)

    @commands.Cog.listener()
    async def on_voice_state_update(
        self,
        member: discord.Member,
        before: discord.VoiceState,
        after: discord.VoiceState,
    ):
        if member.bot:
            return

        guild_id = str(member.guild.id)
        config = self.load_config()

        if guild_id not in config:
            return

        target_vc_id = config[guild_id].get("target_vc_id")
        notify_channel_id = config[guild_id].get("notify_channel_id")

        if (before.channel is None or before.channel.id != target_vc_id) and (
            after.channel and after.channel.id == target_vc_id
        ):
            notify_channel = member.guild.get_channel(notify_channel_id)
            if notify_channel:
                avatar_url = (
                    member.display_avatar.url
                    if member.display_avatar
                    else member.default_avatar.url
                )
                now_timestamp = int(time.time())

                embed = discord.Embed(
                    title="VCに接続しました",
                    description=(
                        f"**{member.display_name}**\n"
                        f"<#{after.channel.id}> に参加しました\n\n"
                        f"<t:{now_timestamp}:F>"
                    ),
                    color=0x57F287,
                )
                embed.set_thumbnail(url=avatar_url)

                await notify_channel.send(embed=embed)


async def setup(bot: commands.Bot):
    await bot.add_cog(VCNotifier(bot))