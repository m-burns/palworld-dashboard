from pathlib import Path

from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

from app.clients.palworld import PalworldClient
from app.config import get_settings
from app.models import ServerStatus
from app.services.backups import BackupService
from app.services.infrastructure import InfrastructureService
from app.services.status import StatusService


BASE_DIR = Path(__file__).resolve().parent

settings = get_settings()

palworld_client = PalworldClient(
    base_url=settings.palworld_api_url,
    username=settings.palworld_api_username,
    password=settings.palworld_api_password,
)

infrastructure_service = InfrastructureService()

backup_service = BackupService(
    directory=settings.backup_directory,
    max_age_hours=settings.backup_max_age_hours,
)

status_service = StatusService(
    palworld_client=palworld_client,
    infrastructure_service=infrastructure_service,
    backup_service=backup_service,
)

app = FastAPI(
    title="Palworld Dashboard",
    version="0.5.0",
)

app.mount(
    "/static",
    StaticFiles(directory=BASE_DIR / "static"),
    name="static",
)

templates = Jinja2Templates(
    directory=BASE_DIR / "templates",
)


@app.get("/", response_class=HTMLResponse)
async def home(request: Request) -> HTMLResponse:
    return templates.TemplateResponse(
        request=request,
        name="index.html",
        context={
            "title": "Palworld Server Dashboard",
        },
    )


@app.get("/health")
async def health() -> dict[str, str]:
    return {
        "status": "ok",
    }


@app.get(
    "/api/status",
    response_model=ServerStatus,
)
async def server_status() -> ServerStatus:
    return await status_service.get_status()
