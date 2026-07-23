import json
import os
from urllib.parse import quote
import requests
from dotenv import load_dotenv
from fastapi import APIRouter, Request
from fastapi.responses import RedirectResponse

load_dotenv()

router = APIRouter(prefix="/api/auth", tags=["Auth"])

CLIENT_ID = os.getenv("DISCORD_CLIENT_ID")
CLIENT_SECRET = os.getenv("DISCORD_CLIENT_SECRET")
REDIRECT_URI = os.getenv("DISCORD_REDIRECT_URI")


@router.get("/login")
async def login():
    discord_login_url = (
        f"https://discord.com/api/oauth2/authorize"
        f"?client_id={CLIENT_ID}"
        f"&redirect_uri={REDIRECT_URI}"
        f"&response_type=code"
        f"&scope=identify%20guilds"
    )
    return RedirectResponse(discord_login_url)


@router.get("/callback")
async def callback(request: Request, code: str):
    bot_instance = getattr(request.app.state, "bot", None)
    if not bot_instance:
        err = quote("Botが接続されていません")
        return RedirectResponse(f"/?error={err}")

    # アクセストークンの取得
    data = {
        "client_id": CLIENT_ID,
        "client_secret": CLIENT_SECRET,
        "grant_type": "authorization_code",
        "code": code,
        "redirect_uri": REDIRECT_URI,
    }
    headers = {"Content-Type": "application/x-www-form-urlencoded"}

    token_res = requests.post(
        "https://discord.com/api/v10/oauth2/token",
        data=data,
        headers=headers,
    )
    if token_res.status_code != 200:
        err = quote("アクセストークンの取得に失敗しました")
        return RedirectResponse(f"/?error={err}")

    access_token = token_res.json().get("access_token")

    # ログインしたユーザーの所属サーバー一覧を取得
    guilds_res = requests.get(
        "https://discord.com/api/v10/users/@me/guilds",
        headers={"Authorization": f"Bearer {access_token}"},
    )
    if guilds_res.status_code != 200:
        err = quote("所属サーバー情報の取得に失敗しました")
        return RedirectResponse(f"/?error={err}")

    user_guilds = guilds_res.json()
    user_guild_ids = {g["id"] for g in user_guilds}

    # Botが参加しているサーバー一覧
    bot_guild_ids = {str(guild.id) for guild in bot_instance.guilds}

    # 共通のサーバーIDを抽出
    common_guilds = list(user_guild_ids.intersection(bot_guild_ids))

    # ❌ サーバーに入っていない場合のUIリダイレクト
    if not common_guilds:
        err = quote(
            "Botが参加しているサーバーに所属していません。対象のDiscordサーバーに参加してから再度お試しください。"
        )
        return RedirectResponse(f"/?error={err}")

    # ログインユーザー情報の取得
    user_res = requests.get(
        "https://discord.com/api/v10/users/@me",
        headers={"Authorization": f"Bearer {access_token}"},
    )
    user_data = user_res.json()

    # Cookieのセット
    response = RedirectResponse(url="/")
    response.set_cookie(
        key="user_id", value=user_data["id"], max_age=86400, httponly=True
    )
    response.set_cookie(
        key="username",
        value=user_data["username"],
        max_age=86400,
        httponly=True,
    )
    response.set_cookie(
        key="user_guilds",
        value=json.dumps(common_guilds),
        max_age=86400,
        httponly=True,
    )

    return response


@router.get("/logout")
async def logout():
    response = RedirectResponse(url="/")
    response.delete_cookie("user_id")
    response.delete_cookie("username")
    response.delete_cookie("user_guilds")
    return response