import asyncio
import os
import sys
import discord
from discord.ext import commands
from dotenv import load_dotenv
from utils.config_manager import ConfigManager
from web_server import run_web_server

load_dotenv()
BOT_TOKEN = os.getenv("DISCORD_TOKEN")

if not BOT_TOKEN:
    print(
        "❌ エラー: .env ファイルまたは環境変数に 'DISCORD_TOKEN' が設定されていません。"
    )
    sys.exit(1)

intents = discord.Intents.default()
intents.voice_states = True
intents.members = True
intents.guilds = True


class MyBot(commands.Bot):

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.config_manager = ConfigManager()


bot = MyBot(command_prefix="!", intents=intents)


@bot.event
async def on_ready():
    print("====================================")
    print(f" ログイン成功: {bot.user.name} (ID: {bot.user.id})")
    print("====================================")

    try:
        for guild in bot.guilds:
            bot.tree.copy_global_to(guild=guild)
            synced = await bot.tree.sync(guild=guild)
            print(
                f"✅ {guild.name} に {len(synced)} 個のコマンドを同期しました"
            )
    except Exception as e:
        print(f"❌ コマンド同期エラー: {e}")


async def load_extensions():
    if not os.path.exists("./cogs"):
        os.makedirs("./cogs")

    for filename in os.listdir("./cogs"):
        if filename.endswith(".py"):
            await bot.load_extension(f"cogs.{filename[:-3]}")
            print(f"📦 モジュールロード完了: {filename}")


async def main():
    async with bot:
        await load_extensions()
        # bot インスタンスを渡して Web サーバーを並行起動
        asyncio.create_task(run_web_server(bot))
        await bot.start(BOT_TOKEN)


if __name__ == "__main__":
    asyncio.run(main())