import re
import discord
from discord.ext import commands

class TwitterFixer(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        # x.com / twitter.com の様々な形式のURLに対応する正規表現
        self.twitter_url_pattern = re.compile(
            r'https?://(?:www\.|mobile\.)?(?:x\.com|twitter\.com)/[a-zA-Z0-9_]+/status/[0-9]+(?:\?\S*)?'
        )

    @commands.Cog.listener()
    async def on_message(self, message: discord.Message):
        # Bot自身のメッセージや他のBotは無視
        if message.author.bot:
            return

        # メッセージにURLが含まれているかチェック
        matches = self.twitter_url_pattern.findall(message.content)

        if matches:
            print(f"DEBUG: Twitter URL detected in message from {message.author}: {matches}")
            fixed_urls = []
            for url in matches:
                # x.com や twitter.com を vxtwitter.com に置換
                fixed_url = re.sub(
                    r'https?://(?:www\.|mobile\.)?(?:x\.com|twitter\.com)',
                    'https://vxtwitter.com',
                    url
                )
                fixed_urls.append(fixed_url)

            # 重複URLを除去して改行で結合
            unique_urls = list(dict.fromkeys(fixed_urls))
            reply_content = "\n".join(unique_urls)
            
            try:
                # 相手に通知を飛ばさずにリプライ送信
                await message.reply(reply_content, mention_author=False)
                print("DEBUG: Reply sent successfully!")
            except Exception as e:
                print(f"❌ リプライ送信エラー: {e}")

async def setup(bot: commands.Bot):
    await bot.add_cog(TwitterFixer(bot))