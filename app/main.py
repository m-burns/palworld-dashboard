import asyncio
import logging

from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import (
    Depends,
    FastAPI,
    HTTPException,
    Query,
    Request,
)
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from sqlalchemy.ext.asyncio import AsyncSession

from app.clients.palworld import PalworldClient
from app.armory_models import (
    ArmoryLeaderboardResponse,
    ArmoryPlayerProfile,
)
from app.config import get_settings
from app.database.session import (
    SessionFactory,
    create_database_tables,
    get_session,
)
from app.models import (
    LevelLeaderboardResponse,
    PlayerHistoryResponse,
    PlayerListResponse,
    PlayerProfile,
    PlaytimeLeaderboardResponse,
    ServerStatus,
)
from app.repositories.players import PlayerRepository
from app.repositories.armory import ArmoryRepository
from app.services.armory import ArmoryService
from app.services.backups import BackupService
from app.services.infrastructure import InfrastructureService
from app.services.players import PlayerService
from app.services.status import StatusService


BASE_DIR = Path(__file__).resolve().parent

settings = get_settings()

logger = logging.getLogger(__name__)

async def player_tracking_loop() -> None:
    while True:
        try:
            async with SessionFactory() as session:
                await player_service.get_online_players(
                    session=session,
                )
        except Exception:
            logger.exception(
                "Background player tracking failed"
            )

        await asyncio.sleep(30)


@asynccontextmanager
async def lifespan(
    app: FastAPI,
):
    await create_database_tables()

    tracking_task = asyncio.create_task(
        player_tracking_loop()
    )

    try:
        yield
    finally:
        tracking_task.cancel()

        try:
            await tracking_task
        except asyncio.CancelledError:
            pass

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

player_repository = PlayerRepository()
armory_repository = ArmoryRepository()

player_service = PlayerService(
    palworld_client=palworld_client,
    player_repository=player_repository,
)

armory_service = ArmoryService(
    repository=armory_repository,
)

app = FastAPI(
    title="Palworld Dashboard",
    version="0.9.0",
    lifespan=lifespan,
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


@app.get(
    "/api/players",
    response_model=PlayerListResponse,
)
async def online_players(
    session: AsyncSession = Depends(get_session),
) -> PlayerListResponse:
    return await player_service.get_online_players(
        session=session,
    )


@app.get(
    "/api/players/history",
    response_model=PlayerHistoryResponse,
)
async def player_history(
    session: AsyncSession = Depends(get_session),
) -> PlayerHistoryResponse:
    return await player_service.get_player_history(
        session=session,
    )

@app.get(
    "/api/leaderboards/levels",
    response_model=LevelLeaderboardResponse,
)
async def level_leaderboard(
    limit: int = Query(
        default=10,
        ge=1,
        le=100,
    ),
    session: AsyncSession = Depends(get_session),
) -> LevelLeaderboardResponse:
    return await player_service.get_level_leaderboard(
        session=session,
        limit=limit,
    )

@app.get(
    "/api/leaderboards/playtime",
    response_model=PlaytimeLeaderboardResponse,
)
async def playtime_leaderboard(
    limit: int = Query(
        default=10,
        ge=1,
        le=100,
    ),
    session: AsyncSession = Depends(get_session),
) -> PlaytimeLeaderboardResponse:
    return await player_service.get_playtime_leaderboard(
        session=session,
        limit=limit,
    )


@app.get(
    "/api/armory/leaderboard",
    response_model=ArmoryLeaderboardResponse,
)
async def armory_leaderboard(
    limit: int = Query(
        default=100,
        ge=1,
        le=100,
    ),
    session: AsyncSession = Depends(get_session),
) -> ArmoryLeaderboardResponse:
    return await armory_service.get_leaderboard(
        session=session,
        limit=limit,
    )


@app.get(
    "/api/armory/players/{player_id}",
    response_model=ArmoryPlayerProfile,
)
async def armory_player_profile(
    player_id: int,
    session: AsyncSession = Depends(get_session),
) -> ArmoryPlayerProfile:
    profile = await armory_service.get_player_profile(
        session=session,
        player_id=player_id,
    )
    if profile is None:
        raise HTTPException(
            status_code=404,
            detail="Armory player not found",
        )
    return profile


@app.get("/armory", response_class=HTMLResponse)
async def armory_page(request: Request) -> HTMLResponse:
    return templates.TemplateResponse(
        request=request,
        name="armory.html",
        context={"title": "Paldeck Armory"},
    )


@app.get(
    "/armory/players/{player_id}",
    response_class=HTMLResponse,
)
async def armory_player_page(
    request: Request,
    player_id: int,
) -> HTMLResponse:
    return templates.TemplateResponse(
        request=request,
        name="armory-player.html",
        context={
            "title": "Paldeck Armory Player",
            "player_id": player_id,
        },
    )

@app.get(
    "/api/players/{player_key}",
    response_model=PlayerProfile,
)
async def player_profile(
    player_key: str,
    session: AsyncSession = Depends(get_session),
) -> PlayerProfile:
    profile = await player_service.get_player_profile(
        session=session,
        player_key=player_key,
    )

    if profile is None:
        raise HTTPException(
            status_code=404,
            detail="Player not found",
        )

    return profile

@app.get(
    "/players/{player_key}",
    response_class=HTMLResponse,
)
async def player_profile_page(
    request: Request,
    player_key: str,
) -> HTMLResponse:
    return templates.TemplateResponse(
        request=request,
        name="player.html",
        context={
            "title": "Player Profile",
            "player_key": player_key,
        },
    )
