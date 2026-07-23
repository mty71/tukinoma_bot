import json
from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from utils.config_manager import ConfigManager

router = APIRouter()
config_manager = ConfigManager()


# 1. サーバー選択画面（ルート）
@router.get("/", response_class=HTMLResponse)
async def index(request: Request, error: str = None):
    templates = request.app.state.templates

    user_id = request.cookies.get("user_id")
    username = request.cookies.get("username")
    guilds_raw = request.cookies.get("managed_guilds")

    is_authenticated = user_id is not None
    managed_guilds = json.loads(guilds_raw) if guilds_raw else []

    # 未ログインであっても、errorがあればサーバー選択（または未ログイン画面）へerror_messageとして渡す
    return templates.TemplateResponse(
        request=request,
        name="server_select.html",
        context={
            "is_authenticated": is_authenticated,
            "username": username,
            "guilds": managed_guilds,
            "error_message": error,  # ← ここで確実に渡す
        },
    )


# 2. 選択した特定サーバーの設定画面
@router.get("/guild/{guild_id}", response_class=HTMLResponse)
async def guild_dashboard(request: Request, guild_id: str):
    templates = request.app.state.templates

    user_id = request.cookies.get("user_id")
    username = request.cookies.get("username")
    guilds_raw = request.cookies.get("managed_guilds")

    if not user_id or not guilds_raw:
        return RedirectResponse(url="/")

    managed_guilds = json.loads(guilds_raw)
    target_guild = next(
        (g for g in managed_guilds if g["id"] == guild_id), None
    )

    if not target_guild:
        raise HTTPException(
            status_code=403, detail="このサーバーへのアクセス権限がありません。"
        )

    is_admin = target_guild["is_admin"]

    all_alarms = config_manager.load("alarms")
    all_vc_settings = config_manager.load("vc_notifier")

    server_alarms = {guild_id: all_alarms.get(guild_id, [])}
    server_vc_settings = (
        {guild_id: all_vc_settings.get(guild_id, [])} if is_admin else {}
    )

    return templates.TemplateResponse(
        request=request,
        name="index.html",
        context={
            "alarms": server_alarms,
            "vc_settings": server_vc_settings,
            "is_authenticated": True,
            "is_admin": is_admin,
            "username": username,
            "current_guild": target_guild,
        },
    )