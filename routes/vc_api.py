from fastapi import APIRouter, Form
from utils.config_manager import ConfigManager

router = APIRouter(prefix="/api/vc", tags=["VC Notifier"])
config_manager = ConfigManager()


@router.post("/add")
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


@router.post("/delete")
async def delete_vc_setting(
    guild_id: str = Form(...), vc_id: str = Form(...)
):
    data = config_manager.load("vc_notifier")
    if guild_id in data and vc_id in data[guild_id]:
        del data[guild_id][vc_id]
        config_manager.save("vc_notifier", data)
    return {"status": "ok"}