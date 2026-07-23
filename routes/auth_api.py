import json
import os
import httpx
from dotenv import load_dotenv
from fastapi import APIRouter, Request
from fastapi.responses import RedirectResponse

load_dotenv()

router = APIRouter(prefix="/api/auth", tags=["Auth"])

CLIENT_ID = os.getenv("DISCORD_CLIENT_ID")
CLIENT_SECRET = os.getenv("DISCORD_CLIENT_SECRET")
REDIRECT_URI = os.getenv("DISCORD_REDIRECT_URI")


# 1. Discordのログイン画面へリダイレクト
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


# 2. Discordからのコールバック受領 & サーバー所属チェック
@router.get("/callback")
async def callback(request: Request, code: str):
    bot_instance = getattr(request.app.state, "bot", None)
    if not bot_instance:
        return {"status": "error", "message": "Bot is not connected"}

    async with httpx.AsyncClient() as client:
        # アクセストークンの取得
        data = {
            "client_id": CLIENT_ID,
            "client_secret": CLIENT_SECRET,
            "grant_type": "authorization_code",
            "code": code,
            "redirect_uri": REDIRECT_URI,
        }
        headers = {"Content-Type": "application/x-www-form-urlencoded"}

        token_res = await client.post(
            "https://discord.com/api/v10/oauth2/token",
            data=data,
            headers=headers,
        )
        if token_res.status_code != 200:
            return {"status": "error", "message": "Failed to get access token"}

        access_token = token_res.json().get("access_token")

        # ログインしたユーザーの所属サーバー一覧を取得
        guilds_res = await client.get(
            "https://discord.com/api/v10/users/@me/guilds",
            headers={"Authorization": f"Bearer {access_token}"},
        )
        if guilds_res.status_code != 200:
            return {
                "status": "error",
                "message": "Failed to fetch user guilds",
            }

        user_guilds = guilds_res.json()
        user_guild_ids = {g["id"] for g in user_guilds}

        # Botが参加しているサーバー一覧
        bot_guild_ids = {str(guild.id) for guild in bot_instance.guilds}

        # ユーザーがBotと同じサーバーに入っている共通のサーバーIDを抽出
        common_guilds = list(user_guild_ids.intersection(bot_guild_ids))

        if not common_guilds:
            return {
                "status": "error",
                "message": "❌ Botが参加しているサーバーに所属していません。",
            }

        # ログインユーザー情報の取得
        user_res = await client.get(
            "https://discord.com/api/v10/users/@me",
            headers={"Authorization": f"Bearer {access_token}"},
        )
        user_data = user_res.json()

    # 認証成功時：Cookieにユーザー情報と「所属している共通サーバーIDリスト」を保存
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
    # 🔑 JSON形式で所属サーバーIDリストをCookieに書き込む
    response.set_cookie(
        key="user_guilds",
        value=json.dumps(common_guilds),
        max_age=86400,
        httponly=True,
    )

    return response


# 3. ログアウト
@router.get("/logout")
async def logout():
    response = RedirectResponse(url="/")
    response.delete_cookie("user_id")
    response.delete_cookie("username")
    response.delete_cookie("user_guilds")  # 所属サーバー情報もクリア
    return response