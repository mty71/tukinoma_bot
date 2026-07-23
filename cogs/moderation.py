import discord
from discord import app_commands
from discord.ext import commands


class Moderation(commands.Cog):

    def __init__(self, bot: commands.Bot):
        self.bot = bot

    # ----------------------------------------------------
    # メッセージ一括削除コマンド (/clear [件数])
    # ----------------------------------------------------
    @app_commands.command(
        name="clear", description="指定した件数のメッセージを一括削除します"
    )
    @app_commands.describe(
        amount="削除するメッセージの件数（1〜100）"
    )
    async def clear_messages(
        self, interaction: discord.Interaction, amount: int
    ):
        # 1. 実行者の権限チェック (メッセージ管理権限)
        if not interaction.user.guild_permissions.manage_messages:
            await interaction.response.send_message(
                "❌ メッセージを管理（削除）する権限がありません。",
                ephemeral=True,
            )
            return

        # 2. 件数の範囲チェック
        if amount < 1 or amount > 100:
            await interaction.response.send_message(
                "⚠️ 1〜100 の範囲で指定してください。", ephemeral=True
            )
            return

        # 処理中レスポンスを返しておく (14日以上前のメッセージ削除等で時間がかかる場合対策)
        await interaction.response.defer(ephemeral=True)

        try:
            # メッセージを一括削除
            deleted = await interaction.channel.purge(limit=amount)

            # 削除成功メッセージ (実行した人にだけ見える非表示メッセージでレスポンス)
            await interaction.followup.send(
                f"🧹 **{len(deleted)}件** のメッセージを削除しました。",
                ephemeral=True,
            )

        except discord.Forbidden:
            await interaction.followup.send(
                "❌ Botに「メッセージの管理」または「メッセージ履歴の閲覧」権限が付与されていません。",
                ephemeral=True,
            )
        except discord.HTTPException as e:
            await interaction.followup.send(
                f"❌ 削除処理中にエラーが発生しました: {e}", ephemeral=True
            )


async def setup(bot: commands.Bot):
    await bot.add_cog(Moderation(bot))