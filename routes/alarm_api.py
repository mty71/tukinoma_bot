import os
import shutil
import uuid
from fastapi import APIRouter, File, Form, Request, UploadFile
from utils.audio_downloader import AudioDownloader
from utils.config_manager import ConfigManager

router = APIRouter(prefix="/api/alarm", tags=["Alarm"])
config_manager = ConfigManager()
downloader = AudioDownloader()


@router.post("/add")
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


@router.post("/delete")
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


@router.post("/stop")
async def stop_alarm_api(request: Request, guild_id: str = Form(...)):
    bot_instance = getattr(request.app.state, "bot", None)
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