import os
import uuid
from fastapi import APIRouter, File, Form, HTTPException, Request, UploadFile
from fastapi.responses import JSONResponse
from utils.audio_downloader import AudioDownloader
from utils.config_manager import ConfigManager

router = APIRouter(prefix="/api/alarm", tags=["Alarm API"])
config_manager = ConfigManager()
downloader = AudioDownloader()


@router.post("/add")
async def add_alarm(
    request: Request,
    guild_id: str = Form(...),
    vc_id: str = Form(...),  # HTMLフォームの name="vc_id" に合わせます
    time_str: str = Form(...),  # HTMLフォームの name="time_str" に合わせます
    mode: str = Form("repeat"),  # 🔑 モードを受け取り (デフォルト: repeat)
    youtube_url: str = Form(None),
    audio_file: UploadFile = File(None),
):
    # ユーザー権限チェック（Cookie確認など必要に応じて調整）
    user_id = request.cookies.get("user_id")
    if not user_id:
        raise HTTPException(
            status_code=401, detail="ログインが必要です。"
        )

    alarms = config_manager.load("alarms")
    if guild_id not in alarms:
        alarms[guild_id] = []

    alarm_id = f"alarm_{uuid.uuid4().hex[:8]}"
    local_path = ""

    # 音声ファイルの保存処理
    if audio_file and audio_file.filename:
        os.makedirs("data/audio", exist_ok=True)
        local_path = f"data/audio/{alarm_id}_{audio_file.filename}"
        contents = await audio_file.read()
        with open(local_path, "wb") as f:
            f.write(contents)
    elif youtube_url:
        local_path = downloader.download_youtube_audio(
            youtube_url, alarm_id
        )

    if not local_path:
        raise HTTPException(
            status_code=400, detail="音源を指定してください。"
        )

    # 🔑 保存データの構築 (mode と last_triggered を追加)
    new_alarm = {
        "id": alarm_id,
        "time": time_str,
        "mode": mode,  # "repeat" または "once"
        "vc_channel_id": int(vc_id),
        "local_file_path": local_path,
        "enabled": True,
        "last_triggered": None,  # 同一分内の重複発火防止用
    }

    alarms[guild_id].append(new_alarm)
    config_manager.save("alarms", alarms)

    return JSONResponse(
        content={
            "status": "success",
            "message": "アラームを保存しました。",
        }
    )


@router.post("/delete")
async def delete_alarm(
    request: Request,
    guild_id: str = Form(...),
    alarm_id: str = Form(...),
):
    alarms = config_manager.load("alarms")
    if guild_id not in alarms:
        return JSONResponse(
            content={"status": "error", "message": "対象のサーバーがありません。"}
        )

    target_alarm = None
    new_list = []
    for alarm in alarms[guild_id]:
        if alarm.get("id") == alarm_id:
            target_alarm = alarm
        else:
            new_list.append(alarm)

    if not target_alarm:
        return JSONResponse(
            content={
                "status": "error",
                "message": "指定されたアラームが見つかりません。",
            }
        )

    alarms[guild_id] = new_list
    config_manager.save("alarms", alarms)

    # 音声ファイルの削除
    audio_path = target_alarm.get("local_file_path")
    if audio_path and os.path.exists(audio_path):
        try:
            os.remove(audio_path)
        except Exception as e:
            print(f"⚠️ ファイル削除エラー: {e}")

    return JSONResponse(
        content={"status": "success", "message": "アラームを削除しました。"}
    )