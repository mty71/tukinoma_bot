from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse
from utils.config_manager import ConfigManager

router = APIRouter()
config_manager = ConfigManager()


@router.get("/", response_class=HTMLResponse)
async def index(request: Request):
    templates = request.app.state.templates
    alarms = config_manager.load("alarms")
    vc_settings = config_manager.load("vc_notifier")

    return templates.TemplateResponse(
        request=request,
        name="index.html",
        context={"alarms": alarms, "vc_settings": vc_settings},
    )