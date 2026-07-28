import hashlib
import hmac
import os
import subprocess
import requests
from fastapi import APIRouter, Header, HTTPException, Request, BackgroundTasks

router = APIRouter(prefix="/api/deploy", tags=["Deploy"])

WEBHOOK_SECRET = os.getenv("GITHUB_WEBHOOK_SECRET", "your_secret_key_here")
PTERO_URL = os.getenv("PTERODACTYL_URL", "").rstrip("/")
PTERO_API_KEY = os.getenv("PTERODACTYL_API_KEY", "")
PTERO_SERVER_ID = os.getenv("PTERODACTYL_SERVER_ID", "")


def verify_signature(payload_body: bytes, secret: str, signature_header: str) -> bool:
    if not signature_header:
        return False
    try:
        hash_type, signature = signature_header.split("=")
        if hash_type != "sha256":
            return False
        mac = hmac.new(secret.encode(), msg=payload_body, digestmod=hashlib.sha256)
        return hmac.compare_digest(mac.hexdigest(), signature)
    except Exception:
        return False


def run_deploy_and_restart():
    """git pull 実行後に Pterodactyl API でサーバーを再起動する"""
    try:
        # 1. git pull の実行
        print("🔄 [Deploy] Executing git pull...")
        result = subprocess.run(
            ["git", "pull", "origin", "main"],
            capture_output=True,
            text=True,
            check=True
        )
        print(f"✅ [Deploy] git pull output: {result.stdout}")

        # 2. Pterodactyl Client API 経由で再起動リクエストを送信
        url = f"{PTERO_URL}/api/client/servers/{PTERO_SERVER_ID}/power"
        headers = {
            "Authorization": f"Bearer {PTERO_API_KEY}",
            "Content-Type": "application/json",
            "Accept": "application/json",
        }
        data = {"signal": "restart"}

        print("🚀 [Deploy] Sending restart signal to Pterodactyl...")
        res = requests.post(url, json=data, headers=headers)
        if res.status_code == 204:
            print("✅ [Deploy] Server restart triggered successfully!")
        else:
            print(f"⚠️ [Deploy] Failed to restart server: {res.status_code} - {res.text}")

    except Exception as e:
        print(f"❌ [Deploy] Error during deployment: {e}")


@router.post("/github")
async def github_webhook(
    request: Request,
    background_tasks: BackgroundTasks,
    x_hub_signature_256: str = Header(None),
    x_github_event: str = Header(None),
):
    payload = await request.body()

    # 1. 署名検証
    if not verify_signature(payload, WEBHOOK_SECRET, x_hub_signature_256):
        raise HTTPException(status_code=400, detail="Invalid signature")

    # 2. push イベントの処理
    if x_github_event == "push":
        # レスポンスをGitHubに返したあと、バックグラウンドで処理を走らせる
        background_tasks.add_task(run_deploy_and_restart)
        return {"status": "ok", "message": "Deployment and restart triggered"}

    return {"status": "ignored", "message": f"Event {x_github_event} ignored"}