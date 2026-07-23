from fastapi import APIRouter, Request, Form

router = APIRouter(prefix="/api", tags=["Moderation"])


@router.post("/clear")
async def clear_messages(
    request: Request,
    channel_id: str = Form(...),
    amount: int = Form(...)
):
    # 🔑 管理者チェック
    if request.cookies.get("is_admin") != "true":
        return {"status": "error", "message": "❌ この操作には管理者権限が必要です"}

    bot_instance = getattr(request.app.state, "bot", None)
    if not bot_instance:
        return {"status": "error", "message": "Botが接続されていません"}

    try:
        channel = bot_instance.get_channel(int(channel_id))
        if not channel:
            channel = await bot_instance.fetch_channel(int(channel_id))

        if not channel:
            return {"status": "error", "message": "チャンネルが見つかりません"}

        deleted = await channel.purge(limit=amount)
        return {"status": "ok", "deleted_count": len(deleted)}
    except Exception as e:
        return {"status": "error", "message": str(e)}