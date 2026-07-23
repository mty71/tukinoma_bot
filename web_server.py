import os
import shutil
import uuid
import uvicorn
from dotenv import load_dotenv
from fastapi import FastAPI, File, Form, Request, UploadFile
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from utils.audio_downloader import AudioDownloader
from utils.config_manager import ConfigManager

load_dotenv()

app = FastAPI()
config_manager = ConfigManager()
downloader = AudioDownloader()

templates = Jinja2Templates(directory="templates")

PORT = int(os.getenv("PORT", 8000))
# botインスタンス参照用（main.pyからセットされる）
bot_instance = None


@app.get("/", response_class=HTMLResponse)
async def index(request: Request):
    alarms = config_manager.load("alarms")
    vc_settings = config_manager.load("vc_notifier")
    return templates.TemplateResponse(
        request=request,
        name="index.html",
        context={"alarms": alarms, "vc_settings": vc_settings},
    )


# ----------------------------------------------------
# 1. アラーム機能 API (CRUD)
# ----------------------------------------------------
@app.post("/api/alarm/add")
async def add_alarm(
    guild_id: str = Form(...),
    vc_id: str = Form(...),
    time_str: str = Form(...),
    youtube_url: str = Form(None),
    audio_file: UploadFile = File(None),
):
    alarm_id = f"alarm_{uuid.uuid4().hex[:8]}"
    local_path = ""

    if audio_file and audio_file.filename:
        local_path = f"data/audio/{alarm_id}_{audio_file.filename}"
        with open(local_path, "wb") as buffer:
            shutil.copyfileobj(audio_file.file, buffer)
    elif youtube_url:
        local_path = downloader.download_youtube_audio(youtube_url, alarm_id)

    data = config_manager.load("alarms")
    if guild_id not in data:
        data[guild_id] = []

    data[guild_id].append(
        {
            "id": alarm_id,
            "time": time_str,
            "vc_channel_id": int(vc_id),
            "local_file_path": local_path,
            "enabled": True,
        }
    )
    config_manager.save("alarms", data)
    return {"status": "ok", "alarm_id": alarm_id}


@app.post("/api/alarm/delete")
async def delete_alarm(guild_id: str = Form(...), alarm_id: str = Form(...)):
    data = config_manager.load("alarms")
    if guild_id in data:
        target_alarm = next(
            (a for a in data[guild_id] if a.get("id") == alarm_id), None
        )
        data[guild_id] = [
            a for a in data[guild_id] if a.get("id") != alarm_id
        ]
        config_manager.save("alarms", data)

        if target_alarm and os.path.exists(
            target_alarm.get("local_file_path", "")
        ):
            try:
                os.remove(target_alarm["local_file_path"])
            except Exception:
                pass
    return {"status": "ok"}


# web_server.py に追加する API エンドポイント
@app.post("/api/alarm/stop")
async def stop_alarm_api(guild_id: str = Form(...)):
    if not bot_instance:
        return {"status": "error", "message": "Bot is not connected"}

    guild = bot_instance.get_guild(int(guild_id))
    if not guild:
        return {"status": "error", "message": "Guild not found"}

    alarm_cog = bot_instance.get_cog("Alarm")
    if alarm_cog:
        stopped = await alarm_cog.stop_alarm_for_guild(guild)
        if stopped:
            return {"status": "ok", "message": "Stopped"}

    return {"status": "error", "message": "No active alarm playing"}

# ----------------------------------------------------
# 2. VC通知設定 API (CRUD)
# ----------------------------------------------------
@app.post("/api/vc/add")
async def add_vc_setting(
    guild_id: str = Form(...),
    vc_id: str = Form(...),
    text_channel_id: str = Form(...),
    mention_type: str = Form("none"),
    mention_role_id: str = Form(None),
):
    data = config_manager.load("vc_notifier")
    if guild_id not in data:
        data[guild_id] = {}

    data[guild_id][vc_id] = {
        "notify_channel_id": int(text_channel_id),
        "mention_type": mention_type,
        "mention_role_id": (
            int(mention_role_id) if mention_role_id else None
        ),
    }
    config_manager.save("vc_notifier", data)
    return {"status": "ok"}


@app.post("/api/vc/delete")
async def delete_vc_setting(
    guild_id: str = Form(...), vc_id: str = Form(...)
):
    data = config_manager.load("vc_notifier")
    if guild_id in data and vc_id in data[guild_id]:
        del data[guild_id][vc_id]
        config_manager.save("vc_notifier", data)
    return {"status": "ok"}


# ----------------------------------------------------
# 3. メッセージ削除 (Clear) API
# ----------------------------------------------------
@app.post("/api/clear")
async def clear_messages(
    channel_id: str = Form(...), amount: int = Form(...)
):
    if not bot_instance:
        return {"status": "error", "message": "Bot is not connected"}

    channel = bot_instance.get_channel(int(channel_id))
    if not channel:
        return {"status": "error", "message": "Channel not found"}

    try:
        deleted = await channel.purge(limit=amount)
        return {"status": "ok", "deleted_count": len(deleted)}
    except Exception as e:
        return {"status": "error", "message": str(e)}


async def run_web_server(bot=None):
    global bot_instance
    bot_instance = bot

    config = uvicorn.Config(
        app, host="0.0.0.0", port=PORT, log_level="info"
    )
    server = uvicorn.Server(config)
    print(f"🌐 WebUI サーバーを起動しました: http://0.0.0.0:{PORT}")
    await server.serve()