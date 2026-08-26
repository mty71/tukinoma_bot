import json
from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from utils.config_manager import ConfigManager

router = APIRouter()
config_manager = ConfigManager()

# ==========================================
# 既存のコード (/, /guild/{guild_id}) はここから
# ==========================================
# ... (中略) ...
# ==========================================
# 既存のコードはここまで
# ==========================================


# 👇 ここから下を追記：Activity用の画面（VC内で開かれるページ）
@router.get("/activity", response_class=HTMLResponse)
async def activity_dashboard(request: Request):
    templates = request.app.state.templates
    
    # Activity内での認証はDiscord SDK側(JS)で行うため、ここではCookieチェック等は不要です
    return templates.TemplateResponse(
        request=request,
        name="activity.html",
        context={}
    )