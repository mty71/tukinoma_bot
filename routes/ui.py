from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from utils.config_manager import ConfigManager

router = APIRouter()
config_manager = ConfigManager()


@router.get("/", response_class=HTMLResponse)
async def index(request: Request):
    templates = request.app.state.templates

    # Cookieからログインユーザー情報を取得
    user_id = request.cookies.get("user_id")
    username = request.cookies.get("username")

    # 未ログインの場合はログインを促すフラグを渡す（または強制リダイレクト）
    is_authenticated = user_id is not None

    alarms = config_manager.load("alarms")
    vc_settings = config_manager.load("vc_notifier")

    return templates.TemplateResponse(
        request=request,
        name="index.html",
        context={
            "alarms": alarms,
            "vc_settings": vc_settings,
            "is_authenticated": is_authenticated,
            "username": username,
        },
    )