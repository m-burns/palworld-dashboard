from typing import Any

import httpx


class PalworldApiError(RuntimeError):
    pass


class PalworldClient:
    def __init__(
        self,
        base_url: str,
        username: str,
        password: str,
        timeout_seconds: float = 5.0,
    ) -> None:
        self._base_url = base_url.rstrip("/")
        self._auth = httpx.BasicAuth(username, password)
        self._timeout = timeout_seconds

    async def _get(self, path: str) -> dict[str, Any]:
        try:
            async with httpx.AsyncClient(
                auth=self._auth,
                timeout=self._timeout,
            ) as client:
                response = await client.get(
                    f"{self._base_url}{path}"
                )
                response.raise_for_status()
                return response.json()

        except (
            httpx.HTTPError,
            ValueError,
        ) as exc:
            raise PalworldApiError(
                f"Palworld API request failed: {path}"
            ) from exc

    async def get_info(self) -> dict[str, Any]:
        return await self._get("/v1/api/info")

    async def get_metrics(self) -> dict[str, Any]:
        return await self._get("/v1/api/metrics")

    async def get_players(self) -> dict[str, Any]:
        return await self._get("/v1/api/players")
