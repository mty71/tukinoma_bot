import json
import os
from urllib.parse import quote
import requests
from dotenv import load_dotenv
from fastapi import APIRouter, Request, HTTPException # HTTPException を追加
from fastapi.responses import RedirectResponse, JSONResponse # JSONResponse を追加

load_dotenv()

router = APIRouter(prefix="/api/auth", tags=["Auth"])

CLIENT_ID = os.getenv("DISCORD_CLIENT_ID")
CLIENT_SECRET = os.getenv("DISCORD_CLIENT_SECRET")
REDIRECT_URI = os.getenv("DISCORD_REDIRECT_URI")

# ==========================================
# 既存のコード (/login, /callback, /logout) はここから
# ==========================================
# ... (中略) ...
# ==========================================
# 既存のコードはここまで
# ==========================================


# 👇 ここから下を追記：Activity専用のトークン交換エンドポイント
@router.post("/token")
async def exchange_token(request: Request):
    """Discord Embedded App SDK用のトークン交換"""
    data = await request.json()
    code = data.get("code")

    if not code:
        raise HTTPException(status_code=400, detail="Code is missing")

    # Activityのトークン交換では redirect_uri は不要なケースが多いですが、
    # エラーが出る場合はダミーのURLか REDIRECT_URI を含めてください。
    payload = {
        "client_id": CLIENT_ID,
        "client_secret": CLIENT_SECRET,
        "grant_type": "authorization_code",
        "code": code,
    }
    headers = {"Content-Type": "application/x-www-form-urlencoded"}

    # 既存コードに合わせて requests を使用
    token_res = requests.post(
        "https://discord.com/api/v10/oauth2/token",
        data=payload,
        headers=headers,
    )
    
    if token_res.status_code != 200:
        raise HTTPException(status_code=token_res.status_code, detail="Token exchange failed")

    return JSONResponse(content=token_res.json())