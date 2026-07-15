from fastapi import FastAPI

from app.clients.palworld import PalworldClient
from app.config import get_settings
from app.models import ServerStatus
from app.services.status import StatusService


settings = get_settings()

palworld_client = PalworldClient(
    base_url=settings.palworld_api_url,
    username=settings.palworld_api_username,
    password=settings.palworld_api_password,
)

status_service = StatusService(palworld_client)

app = FastAPI(
    title="Palworld Dashboard",
    version="0.2.0",
)


@app.get("/health")
async def health() -> dict[str, str]:
    return {"status": "ok"}


@app.get(
    "/api/status",
    response_model=ServerStatus,
)
async def server_status() -> ServerStatus:
    return await status_service.get_status()
