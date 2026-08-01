import asyncio
import hashlib
import secrets
import logging

from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import (
    Depends,
    FastAPI,
    HTTPException,
    Query,
    Request,
    Response,
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
from app.announcement_models import AnnouncementListResponse
from app.config import get_settings
from app.database.session import (
    SessionFactory,
    create_database_tables,
    get_session,
)
from app.models import (
    ActivityTimelineResponse,
    LevelLeaderboardResponse,
    PlayerHistoryResponse,
    PlayerListResponse,
    PlayerProfile,
    PlaytimeLeaderboardResponse,
    ServerStatus,
)
from app.repositories.players import PlayerRepository
from app.repositories.armory import ArmoryRepository
from app.repositories.announcements import AnnouncementRepository
from app.repositories.voting import DuplicateVoteError, InvalidVoteError, VotingRepository
from app.services.armory import ArmoryService
from app.services.announcements import AnnouncementService
from app.services.backups import BackupService
from app.services.infrastructure import InfrastructureService
from app.services.players import PlayerService
from app.services.status import StatusService
from app.services.voting import VotingService
from app.voting_models import PollListResponse, VoteRequest, VoteResponse


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
announcement_service = AnnouncementService(
    repository=AnnouncementRepository(),
)
voting_service = VotingService(
    repository=VotingRepository(),
)



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

@app.get("/hall-of-fame", response_class=HTMLResponse)
async def hall_of_fame_page(request: Request) -> HTMLResponse:
    return templates.TemplateResponse(
        request=request,
        name="hall-of-fame.html",
        context={"title": "Hall of Fame"},
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
    "/api/announcements",
    response_model=AnnouncementListResponse,
)
async def announcements(
    limit: int = Query(default=10, ge=1, le=50),
    session: AsyncSession = Depends(get_session),
) -> AnnouncementListResponse:
    return await announcement_service.list_active(session, limit)


@app.get(
    "/api/activity",
    response_model=ActivityTimelineResponse,
)
async def activity_timeline(
    limit: int = Query(
        default=30,
        ge=1,
        le=100,
    ),
    session: AsyncSession = Depends(get_session),
) -> ActivityTimelineResponse:
    return await player_service.get_activity_timeline(
        session=session,
        limit=limit,
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


@app.get(
    "/api/polls",
    response_model=PollListResponse,
)
async def active_polls(
    limit: int = Query(default=5, ge=1, le=20),
    session: AsyncSession = Depends(get_session),
) -> PollListResponse:
    return await voting_service.list_active(session, limit)


@app.post(
    "/api/polls/{poll_id}/vote",
    response_model=VoteResponse,
)
async def cast_vote(
    poll_id: int,
    payload: VoteRequest,
    request: Request,
    response: Response,
    session: AsyncSession = Depends(get_session),
) -> VoteResponse:
    voter_token = request.cookies.get("palworld_voter")
    try:
        valid_token = (
            voter_token is not None
            and len(voter_token) == 64
            and len(bytes.fromhex(voter_token)) == 32
        )
    except ValueError:
        valid_token = False

    if not valid_token:
        voter_token = secrets.token_hex(32)
        response.set_cookie(
            "palworld_voter",
            voter_token,
            max_age=31_536_000,
            httponly=True,
            samesite="lax",
        )

    assert voter_token is not None
    voter_hash = hashlib.sha256(voter_token.encode()).hexdigest()
    try:
        poll = await voting_service.vote(
            session,
            poll_id,
            payload.option_id,
            voter_hash,
        )
    except DuplicateVoteError as exc:
        raise HTTPException(status_code=409, detail="Already voted") from exc
    except InvalidVoteError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc

    return VoteResponse(accepted=True, poll=poll)
