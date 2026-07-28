import re
import discord
from discord.ext import commands

class TwitterFixer(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        # x.com または twitter.com のURLを抽出する正規表現
        self.twitter_url_pattern = re.compile(
            r'https?://(?:www\.|mobile\.)?(?:x\.com|twitter\.com)/[a-zA-Z0-9_]+/status/[0-9]+(?:\?\S*)?'
        )

    @commands.Cog.listener()
    async def on_message(self, message: discord.Message):
        # Bot自身のメッセージや他のBotは無視
        if message.author.bot:
            return

        # 既に https://vxtwitter.com/https://... になっている二次反応を防ぐため、
        # メッセージ全体がすでに vxtwitter プレフィックスから始まっている場合は無視
        if "vxtwitter.com/https" in message.content:
            return

        matches = self.twitter_url_pattern.findall(message.content)

        if matches:
            fixed_urls = []
            for url in matches:
                # 元のURLの直前に https://vxtwitter.com/ をそのまま連結する
                fixed_url = f"https://vxtwitter.com/{url}"
                fixed_urls.append(fixed_url)

            # 重複を除去して改行で結合
            unique_urls = list(dict.fromkeys(fixed_urls))
            reply_content = "\n".join(unique_urls)

            try:
                # 相手に通知を飛ばさずにリプライ
                await message.reply(reply_content, mention_author=False)
            except Exception as e:
                print(f"❌ リプライ送信エラー: {e}")

async def setup(bot: commands.Bot):
    await bot.add_cog(TwitterFixer(bot))