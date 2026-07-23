import os
import uvicorn
from dotenv import load_dotenv
from fastapi import FastAPI
from fastapi.templating import Jinja2Templates

# 1. auth_router のインポートを追加
from routes.alarm_api import router as alarm_router
from routes.auth_api import router as auth_router
from routes.moderation_api import router as moderation_router
from routes.ui import router as ui_router
from routes.vc_api import router as vc_router

load_dotenv()

app = FastAPI()

# テンプレートを app.state に保持
templates = Jinja2Templates(directory="templates")
app.state.templates = templates

# 2. auth_router をアプリに登録
app.include_router(ui_router)
app.include_router(auth_router)  # ← 追加しました！
app.include_router(alarm_router)
app.include_router(vc_router)
app.include_router(moderation_router)

PORT = int(os.getenv("PORT", 8000))


async def run_web_server(bot=None):
    app.state.bot = bot  # Botインスタンスを保持

    config = uvicorn.Config(
        app, host="0.0.0.0", port=PORT, log_level="info"
    )
    server = uvicorn.Server(config)
    print(f"🌐 WebUI サーバーを起動しました: http://0.0.0.0:{PORT}")
    await server.serve()