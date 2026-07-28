import re
import discord
from discord.ext import commands

class TwitterFixer(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        # x.com または twitter.com のURLを検出する正規表現
        self.twitter_url_pattern = re.compile(
            r'https?://(?:www\.)?(?:x\.com|twitter\.com)/[a-zA-Z0-9_]+/status/[0-9]+(?:\?\S+)?'
        )

    @commands.Cog.listener()
    async def on_message(self, message: discord.Message):
        # Bot自身のメッセージは無視する
        if message.author.bot:
            return

        # メッセージ本文からTwitterのURLをすべて検索
        matches = self.twitter_url_pattern.findall(message.content)

        if matches:
            fixed_urls = []
            for url in matches:
                # https://x.com/... や https://twitter.com/... を vxtwitter.com に置換
                fixed_url = re.sub(
                    r'https?://(?:www\.)?(?:x\.com|twitter\.com)',
                    'https://vxtwitter.com',
                    url
                )
                fixed_urls.append(fixed_url)

            # 変換したURLを改行でつないでリプライ
            reply_content = "\n".join(fixed_urls)
            
            try:
                # mention_author=False にすることで、相手への通知（メンション）を飛ばさずにリプライします
                await message.reply(reply_content, mention_author=False)
            except discord.HTTPException as e:
                print(f"⚠️ リプライ送信エラー: {e}")

async def setup(bot: commands.Bot):
    await bot.add_cog(TwitterFixer(bot))