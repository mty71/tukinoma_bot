import os
import shutil
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

# .env からポート番号を取得（指定がなければデフォルト 8000）
PORT = int(os.getenv("PORT", 8000))


@app.get("/", response_class=HTMLResponse)
async def index(request: Request):
    alarms = config_manager.load("alarms")
    return templates.TemplateResponse(
        request=request, name="index.html", context={"alarms": alarms}
    )


@app.post("/api/alarm/add")
async def add_alarm(
    guild_id: str = Form(...),
    vc_id: str = Form(...),
    time_str: str = Form(...),
    youtube_url: str = Form(None),
    audio_file: UploadFile = File(None),
):
    import uuid

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


# Discord Bot (asyncio) と同時に Web サーバーをバックグラウンド起動するための関数
async def run_web_server():
    config = uvicorn.Config(
        app, host="0.0.0.0", port=PORT, log_level="info"
    )
    server = uvicorn.Server(config)
    print(f"🌐 WebUI サーバーを起動しました: http://0.0.0.0:{PORT}")
    await server.serve()