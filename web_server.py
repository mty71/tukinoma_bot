import shutil
import uuid
from fastapi import FastAPI, File, Form, Request, UploadFile
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from utils.audio_downloader import AudioDownloader
from utils.config_manager import ConfigManager

app = FastAPI()
config_manager = ConfigManager()
downloader = AudioDownloader()

templates = Jinja2Templates(directory="templates")


@app.get("/", response_class=HTMLResponse)
async def index(request: Request):
    # 保存されているアラーム一覧を表示
    alarms = config_manager.load("alarms")
    return templates.TemplateResponse(
        "index.html", {"request": request, "alarms": alarms}
    )


@app.post("/api/alarm/add")
async def add_alarm(
    guild_id: str = Form(...),
    vc_id: str = Form(...),
    time_str: str = Form(...),  # "07:30"
    youtube_url: str = Form(None),
    audio_file: UploadFile = File(None),
):
    alarm_id = f"alarm_{uuid.uuid4().hex[:8]}"
    local_path = ""

    # 音声ファイルの判定（ファイルアップロード優先、次点でYouTube）
    if audio_file and audio_file.filename:
        local_path = f"data/audio/{alarm_id}_{audio_file.filename}"
        with open(local_path, "wb") as buffer:
            shutil.copyfileobj(audio_file.file, buffer)
    elif youtube_url:
        local_path = downloader.download_youtube_audio(youtube_url, alarm_id)

    # データの保存
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