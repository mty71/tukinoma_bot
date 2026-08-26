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

    guilds_res = requests.get(
        "https://discord.com/api/v10/users/@me/guilds",
        headers={"Authorization": f"Bearer {access_token}"},
    )
    if guilds_res.status_code != 200:
        err = quote("所属サーバー情報の取得に失敗しました")
        return RedirectResponse(f"/?error={err}")

    user_guilds = guilds_res.json()
    user_guild_ids = {g["id"] for g in user_guilds}

    bot_guild_ids = {str(guild.id) for guild in bot_instance.guilds}
    common_guild_ids = user_guild_ids.intersection(bot_guild_ids)

    if not common_guild_ids:
        err = quote(
            "Botが参加しているサーバーに所属していません。対象のDiscordサーバーに参加してから再度ログインしてください。"
        )
        response = RedirectResponse(url=f"/?error={err}", status_code=303)
        response.delete_cookie("user_id")
        response.delete_cookie("username")
        response.delete_cookie("managed_guilds")
        return response

    managed_guilds = []
    ADMINISTRATOR_BIT = 0x8

    for g in user_guilds:
        if g["id"] in common_guild_ids:
            perms = int(g.get("permissions", 0))
            is_admin = bool(
                g.get("owner") or (perms & ADMINISTRATOR_BIT) == ADMINISTRATOR_BIT
            )

            icon_hash = g.get("icon")
            icon_url = (
                f"https://cdn.discordapp.com/icons/{g['id']}/{icon_hash}.png"
                if icon_hash
                else None
            )

            managed_guilds.append(
                {
                    "id": g["id"],
                    "name": g["name"],
                    "icon": icon_url,
                    "is_admin": is_admin,
                }
            )

    user_res = requests.get(
        "https://discord.com/api/v10/users/@me",
        headers={"Authorization": f"Bearer {access_token}"},
    )
    user_data = user_res.json()

    response = RedirectResponse(url="/", status_code=303)
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
        key="managed_guilds",
        value=json.dumps(managed_guilds),
        max_age=86400,
        httponly=True,
    )

    return response


@router.get("/logout")
async def logout():
    response = RedirectResponse(url="/", status_code=303)
    response.delete_cookie("user_id")
    response.delete_cookie("username")
    response.delete_cookie("managed_guilds")
    return response

@router.post("/activity_login")
async def activity_login(request: Request):
    """Activity SDKからの認証コードを受け取り、Cookieをセットするハイブリッド用API"""
    data = await request.json()
    code = data.get("code")
    
    if not code:
        return JSONResponse(status_code=400, content={"detail": "Code missing"})

    # 1. トークン交換
    payload = {
        "client_id": CLIENT_ID,
        "client_secret": CLIENT_SECRET,
        "grant_type": "authorization_code",
        "code": code,
    }
    headers = {"Content-Type": "application/x-www-form-urlencoded"}
    token_res = requests.post("https://discord.com/api/v10/oauth2/token", data=payload, headers=headers)
    
    if token_res.status_code != 200:
        return JSONResponse(status_code=400, content={"detail": "Token exchange failed"})
        
    access_token = token_res.json().get("access_token")

    # 2. ユーザー情報とサーバー情報の取得 (既存の/callbackと同じ処理)
    user_res = requests.get("https://discord.com/api/v10/users/@me", headers={"Authorization": f"Bearer {access_token}"})
    guilds_res = requests.get("https://discord.com/api/v10/users/@me/guilds", headers={"Authorization": f"Bearer {access_token}"})
    
    user_data = user_res.json()
    user_guilds = guilds_res.json()

    bot_instance = getattr(request.app.state, "bot", None)
    if bot_instance:
        bot_guild_ids = {str(guild.id) for guild in bot_instance.guilds}
        user_guild_ids = {g["id"] for g in user_guilds}
        common_guild_ids = user_guild_ids.intersection(bot_guild_ids)
        
        managed_guilds = []
        ADMINISTRATOR_BIT = 0x8
        for g in user_guilds:
            if g["id"] in common_guild_ids:
                perms = int(g.get("permissions", 0))
                is_admin = bool(g.get("owner") or (perms & ADMINISTRATOR_BIT) == ADMINISTRATOR_BIT)
                icon_hash = g.get("icon")
                icon_url = f"https://cdn.discordapp.com/icons/{g['id']}/{icon_hash}.png" if icon_hash else None
                managed_guilds.append({
                    "id": g["id"], "name": g["name"], "icon": icon_url, "is_admin": is_admin
                })
    else:
        managed_guilds = []

    # 3. CookieをセットしてJSONを返す (成功サイン)
    response = JSONResponse(content={"status": "ok"})
    response.set_cookie(key="user_id", value=user_data["id"], max_age=86400, httponly=True)
    response.set_cookie(key="username", value=user_data["username"], max_age=86400, httponly=True)
    response.set_cookie(key="managed_guilds", value=json.dumps(managed_guilds), max_age=86400, httponly=True)
    
    return response