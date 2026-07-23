from fastapi import APIRouter, Form, Request

router = APIRouter(prefix="/api", tags=["Moderation"])


@router.post("/clear")
async def clear_messages(
    request: Request, channel_id: str = Form(...), amount: int = Form(...)
):
    bot_instance = getattr(request.app.state, "bot", None)
    if not bot_instance:
        return {"status": "error", "message": "Bot is not connected"}

    channel = bot_instance.get_channel(int(channel_id))
    if not channel:
        return {"status": "error", "message": "Channel not found"}

    try:
        deleted = await channel.purge(limit=amount)
        return {"status": "ok", "deleted_count": len(deleted)}
    except Exception as e:
        return {"status": "error", "message": str(e)}