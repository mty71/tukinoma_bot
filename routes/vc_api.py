from fastapi import APIRouter, Request, Form
from utils.config_manager import ConfigManager

router = APIRouter(prefix="/api/vc", tags=["VC Notifier"])
config_manager = ConfigManager()


@router.post("/save")
async def save_vc_setting(
    request: Request,
    guild_id: str = Form(...),
    target_vc_id: str = Form(...),
    notice_channel_id: str = Form(...)
):
    # 🔑 管理者チェック
    if request.cookies.get("is_admin") != "true":
        return {"status": "error", "message": "❌ この操作には管理者権限が必要です"}

    vc_settings = config_manager.load("vc_notifier")
    
    if guild_id not in vc_settings:
        vc_settings[guild_id] = []

    # 設定の更新・追加
    existing = next((item for item in vc_settings[guild_id] if item["target_vc_id"] == target_vc_id), None)
    if existing:
        existing["notice_channel_id"] = notice_channel_id
    else:
        vc_settings[guild_id].append({
            "target_vc_id": target_vc_id,
            "notice_channel_id": notice_channel_id
        })

    config_manager.save("vc_notifier", vc_settings)
    return {"status": "ok"}


@router.post("/delete")
async def delete_vc_setting(
    request: Request,
    guild_id: str = Form(...),
    target_vc_id: str = Form(...)
):
    # 🔑 管理者チェック
    if request.cookies.get("is_admin") != "true":
        return {"status": "error", "message": "❌ この操作には管理者権限が必要です"}

    vc_settings = config_manager.load("vc_notifier")
    if guild_id in vc_settings:
        vc_settings[guild_id] = [
            item for item in vc_settings[guild_id] if item["target_vc_id"] != target_vc_id
        ]
        config_manager.save("vc_notifier", vc_settings)

    return {"status": "ok"}