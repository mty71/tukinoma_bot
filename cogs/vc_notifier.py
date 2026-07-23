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

    # ----------------------------------------------------
    # スラッシュコマンド: /vc_setup
    # ----------------------------------------------------
    @app_commands.command(
        name="vc_setup",
        description="VC通知の接続先・通知チャンネル・メンション設定を行います",
    )
    @app_commands.describe(
        vc="監視したいボイスチャンネル",
        text_channel="通知を送信するテキストチャンネル",
        mention_type="通知時のメンション種類を選んでください",
        role_to_mention="メンション対象に指定ロールを選んだ場合はここでロールを選択",
    )
    @app_commands.choices(
        mention_type=[
            app_commands.Choice(name="なし (メンションしない)", value="none"),
            app_commands.Choice(
                name="参加/切断した本人をメンション", value="user"
            ),
            app_commands.Choice(name="@everyone", value="everyone"),
            app_commands.Choice(name="特定のロールをメンション", value="role"),
        ]
    )
    async def vc_setup(
        self,
        interaction: discord.Interaction,
        vc: discord.VoiceChannel,
        text_channel: discord.TextChannel,
        mention_type: str = "none",
        role_to_mention: discord.Role = None,
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
            "mention_type": mention_type,
            "mention_role_id": (
                role_to_mention.id if role_to_mention else None
            ),
        }
        self.save_config(config)

        embed = discord.Embed(
            title="⚙️ VC通知設定を更新しました", color=0x57F287
        )
        embed.add_field(name="監視対象VC", value=f"<#{vc.id}>", inline=False)
        embed.add_field(
            name="通知先チャンネル", value=f"<#{text_channel.id}>", inline=False
        )

        mention_str = "なし"
        if mention_type == "user":
            mention_str = "操作した本人"
        elif mention_type == "everyone":
            mention_str = "@everyone"
        elif mention_type == "role" and role_to_mention:
            mention_str = f"<@&{role_to_mention.id}>"

        embed.add_field(name="メンション設定", value=mention_str, inline=False)

        await interaction.response.send_message(embed=embed)

    # ----------------------------------------------------
    # メンション文字列の生成ヘルパー
    # ----------------------------------------------------
    def get_mention_text(self, member: discord.Member, config_data: dict) -> str:
        m_type = config_data.get("mention_type", "none")
        if m_type == "user":
            return f"<@{member.id}> "
        elif m_type == "everyone":
            return "@everyone "
        elif m_type == "role":
            role_id = config_data.get("mention_role_id")
            if role_id:
                return f"<@&{role_id}> "
        return ""

    # ----------------------------------------------------
    # イベント処理: VCの入退室（接続・切断）検知
    # ----------------------------------------------------
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

        guild_config = config[guild_id]
        target_vc_id = guild_config.get("target_vc_id")
        notify_channel_id = guild_config.get("notify_channel_id")

        notify_channel = member.guild.get_channel(notify_channel_id)
        if not notify_channel:
            return

        avatar_url = (
            member.display_avatar.url
            if member.display_avatar
            else member.default_avatar.url
        )
        now_timestamp = int(time.time())
        mention_text = self.get_mention_text(member, guild_config)

        # 1. 接続（参加）処理
        if (before.channel is None or before.channel.id != target_vc_id) and (
            after.channel and after.channel.id == target_vc_id
        ):
            embed = discord.Embed(
                title="VCに接続しました",
                description=(
                    f"**{member.display_name}**\n"
                    f"<#{after.channel.id}> に参加しました\n\n"
                    f"<t:{now_timestamp}:F>"
                ),
                color=0x57F287,  # 緑色
            )
            embed.set_thumbnail(url=avatar_url)

            # メンション文字列がある場合は content に指定して送信（Embed内だと通知が飛ばないため）
            await notify_channel.send(content=mention_text, embed=embed)

        # 2. 切断（退出）処理
        elif (before.channel and before.channel.id == target_vc_id) and (
            after.channel is None or after.channel.id != target_vc_id
        ):
            embed = discord.Embed(
                title="VCから切断しました",
                description=(
                    f"**{member.display_name}**\n"
                    f"<#{before.channel.id}> から退出しました\n\n"
                    f"<t:{now_timestamp}:F>"
                ),
                color=0xED4245,  # 赤色
            )
            embed.set_thumbnail(url=avatar_url)

            await notify_channel.send(content=mention_text, embed=embed)


async def setup(bot: commands.Bot):
    await bot.add_cog(VCNotifier(bot))