import json
from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse
from utils.config_manager import ConfigManager

router = APIRouter()
config_manager = ConfigManager()


@router.get("/", response_class=HTMLResponse)
async def index(request: Request):
    templates = request.app.state.templates

    user_id = request.cookies.get("user_id")
    username = request.cookies.get("username")
    user_guilds_raw = request.cookies.get("user_guilds")

    is_authenticated = user_id is not None
    user_guilds = json.loads(user_guilds_raw) if user_guilds_raw else []

    # 全設定データのロード
    all_alarms = config_manager.load("alarms")
    all_vc_settings = config_manager.load("vc_notifier")

    # 🔑 ログイン中のユーザーが参加しているサーバーのデータだけを抽出 (フィルタリング)
    filtered_alarms = {}
    filtered_vc_settings = {}

    if is_authenticated:
        for guild_id, data in all_alarms.items():
            if guild_id in user_guilds:
                filtered_alarms[guild_id] = data

        for guild_id, data in all_vc_settings.items():
            if guild_id in user_guilds:
                filtered_vc_settings[guild_id] = data

    return templates.TemplateResponse(
        request=request,
        name="index.html",
        context={
            "alarms": filtered_alarms,  # フィルタリング後のデータを渡す
            "vc_settings": filtered_vc_settings,
            "is_authenticated": is_authenticated,
            "username": username,
        },
    )