import time
import discord
from discord import app_commands
from discord.ext import commands


# /vc のグループコマンドを定義
class VCGroup(app_commands.Group):

    def __init__(self, cog: "VCNotifier"):
        super().__init__(
            name="vc", description="VC通知機能に関するコマンド群"
        )
        self.cog = cog

    # ----------------------------------------------------
    # 1. 設定追加・更新 (/vc add)
    # ----------------------------------------------------
    @app_commands.command(
        name="add", description="監視するVCと通知先の設定を追加・更新します"
    )
    @app_commands.describe(
        vc="監視したいボイスチャンネル",
        text_channel="通知を送信するテキストチャンネル",
        mention_type="通知時のメンション種類",
        role_to_mention="指定ロールを選んだ場合の対象ロール",
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
    async def add(
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
        vc_id_str = str(vc.id)
        data = self.cog.get_data()

        if guild_id not in data:
            data[guild_id] = {}

        data[guild_id][vc_id_str] = {
            "notify_channel_id": text_channel.id,
            "mention_type": mention_type,
            "mention_role_id": (
                role_to_mention.id if role_to_mention else None
            ),
        }
        self.cog.save_data(data)

        embed = discord.Embed(
            title="⚙️ VC通知設定を追加・更新しました", color=0x57F287
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
    # 2. 設定一覧表示 (/vc list)
    # ----------------------------------------------------
    @app_commands.command(
        name="list", description="登録されているVC通知設定の一覧を表示します"
    )
    async def list(self, interaction: discord.Interaction):
        guild_id = str(interaction.guild_id)
        data = self.cog.get_data()

        if guild_id not in data or not data[guild_id]:
            await interaction.response.send_message(
                "⚠️ 登録されている設定はありません。`/vc add` で追加してください。",
                ephemeral=True,
            )
            return

        embed = discord.Embed(
            title="📋 登録済みのVC通知一覧", color=0x3498DB
        )

        for vc_id_str, setting in data[guild_id].items():
            notify_ch_id = setting.get("notify_channel_id")
            m_type = setting.get("mention_type", "none")
            m_role_id = setting.get("mention_role_id")

            m_str = "なし"
            if m_type == "user":
                m_str = "本人"
            elif m_type == "everyone":
                m_str = "@everyone"
            elif m_type == "role" and m_role_id:
                m_str = f"<@&{m_role_id}>"

            embed.add_field(
                name=f"🔊 VC: <#{vc_id_str}>",
                value=(
                    f"└ **通知先**: <#{notify_ch_id}>\n"
                    f"└ **メンション**: {m_str}"
                ),
                inline=False,
            )

        await interaction.response.send_message(embed=embed)

    # ----------------------------------------------------
    # 3. 単体設定削除 (/vc remove)
    # ----------------------------------------------------
    @app_commands.command(
        name="remove", description="指定したVCの通知設定を1つ削除します"
    )
    @app_commands.describe(vc="設定を削除したいボイスチャンネル")
    async def remove(
        self, interaction: discord.Interaction, vc: discord.VoiceChannel
    ):
        if not interaction.user.guild_permissions.administrator:
            await interaction.response.send_message(
                "❌ 管理者権限が必要です。", ephemeral=True
            )
            return

        guild_id = str(interaction.guild_id)
        vc_id_str = str(vc.id)
        data = self.cog.get_data()

        if guild_id not in data or vc_id_str not in data[guild_id]:
            await interaction.response.send_message(
                f"⚠️ <#{vc.id}> の設定は存在しません。", ephemeral=True
            )
            return

        del data[guild_id][vc_id_str]
        self.cog.save_data(data)

        await interaction.response.send_message(
            f"🗑️ <#{vc.id}> の通知設定を削除しました。"
        )

    # ----------------------------------------------------
    # 4. 設定一括削除 (/vc clear)
    # ----------------------------------------------------
    @app_commands.command(
        name="clear",
        description="このサーバーのVC通知設定をすべて一括削除します",
    )
    async def clear(self, interaction: discord.Interaction):
        if not interaction.user.guild_permissions.administrator:
            await interaction.response.send_message(
                "❌ 管理者権限が必要です。", ephemeral=True
            )
            return

        guild_id = str(interaction.guild_id)
        data = self.cog.get_data()

        if guild_id not in data or not data[guild_id]:
            await interaction.response.send_message(
                "⚠️ 削除対象の設定が存在しません。", ephemeral=True
            )
            return

        count = len(data[guild_id])
        del data[guild_id]
        self.cog.save_data(data)

        embed = discord.Embed(
            title="🧹 VC通知設定を全削除しました",
            description=f"このサーバーに登録されていた **{count} 件** の設定をすべてクリアしました。",
            color=0xED4245,
        )
        await interaction.response.send_message(embed=embed)


# 本体Cog
class VCNotifier(commands.Cog):
    FEATURE_NAME = "vc_notifier"

    def __init__(self, bot: commands.Bot):
        self.bot = bot
        # グループコマンドを登録
        self.vc_group = VCGroup(self)
        self.bot.tree.add_command(self.vc_group)

    def cog_unload(self):
        # Cogのアンロード時にグループコマンドを解除
        self.bot.tree.remove_command(self.vc_group.name)

    def get_data(self) -> dict:
        return self.bot.config_manager.load(self.FEATURE_NAME)

    def save_data(self, data: dict) -> None:
        self.bot.config_manager.save(self.FEATURE_NAME, data)

    def get_mention_text(self, member: discord.Member, vc_setting: dict) -> str:
        m_type = vc_setting.get("mention_type", "none")
        if m_type == "user":
            return f"<@{member.id}> "
        elif m_type == "everyone":
            return "@everyone "
        elif m_type == "role":
            role_id = vc_setting.get("mention_role_id")
            if role_id:
                return f"<@&{role_id}> "
        return ""

    # ----------------------------------------------------
    # イベント処理 (VC接続/切断)
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
        data = self.get_data()

        if guild_id not in data:
            return

        guild_settings = data[guild_id]
        now_timestamp = int(time.time())
        avatar_url = (
            member.display_avatar.url
            if member.display_avatar
            else member.default_avatar.url
        )

        # 1. 接続（参加）判定
        if after.channel:
            after_vc_id = str(after.channel.id)
            if after_vc_id in guild_settings and (
                before.channel is None or before.channel.id != after.channel.id
            ):
                setting = guild_settings[after_vc_id]
                notify_channel = member.guild.get_channel(
                    setting.get("notify_channel_id")
                )
                if notify_channel:
                    mention_text = self.get_mention_text(member, setting)
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
                    await notify_channel.send(
                        content=mention_text, embed=embed
                    )

        # 2. 切断（退出）判定
        if before.channel:
            before_vc_id = str(before.channel.id)
            if before_vc_id in guild_settings and (
                after.channel is None or after.channel.id != before.channel.id
            ):
                setting = guild_settings[before_vc_id]
                notify_channel = member.guild.get_channel(
                    setting.get("notify_channel_id")
                )
                if notify_channel:
                    mention_text = self.get_mention_text(member, setting)
                    embed = discord.Embed(
                        title="VCから切断しました",
                        description=(
                            f"**{member.display_name}**\n"
                            f"<#{before.channel.id}> から退出しました\n\n"
                            f"<t:{now_timestamp}:F>"
                        ),
                        color=0xED4245,
                    )
                    embed.set_thumbnail(url=avatar_url)
                    await notify_channel.send(
                        content=mention_text, embed=embed
                    )


async def setup(bot: commands.Bot):
    await bot.add_cog(VCNotifier(bot))