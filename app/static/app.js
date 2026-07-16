const REFRESH_INTERVAL_MS = 15_000;

function formatUptime(totalSeconds) {
    if (
        totalSeconds === null ||
        totalSeconds === undefined
    ) {
        return "—";
    }

    const days = Math.floor(
        totalSeconds / 86400,
    );

    const hours = Math.floor(
        (totalSeconds % 86400) / 3600,
    );

    const minutes = Math.floor(
        (totalSeconds % 3600) / 60,
    );

    if (days > 0) {
        return `${days}d ${hours}h`;
    }

    if (hours > 0) {
        return `${hours}h ${minutes}m`;
    }

    return `${minutes}m`;
}

function formatDuration(totalSeconds) {
    if (
        totalSeconds === null ||
        totalSeconds === undefined
    ) {
        return "Unknown age";
    }

    const days = Math.floor(
        totalSeconds / 86400,
    );

    const hours = Math.floor(
        (totalSeconds % 86400) / 3600,
    );

    const minutes = Math.floor(
        (totalSeconds % 3600) / 60,
    );

    if (days > 0) {
        return `${days}d ${hours}h ago`;
    }

    if (hours > 0) {
        return `${hours}h ${minutes}m ago`;
    }

    return `${minutes}m ago`;
}

function formatFrameTime(value) {
    if (
        value === null ||
        value === undefined
    ) {
        return "—";
    }

    return `${Number(value).toFixed(2)} ms`;
}

function formatBytes(bytes) {
    if (
        bytes === null ||
        bytes === undefined
    ) {
        return "—";
    }

    const units = [
        "B",
        "KB",
        "MB",
        "GB",
        "TB",
    ];

    let value = Number(bytes);
    let unit = 0;

    while (
        value >= 1024 &&
        unit < units.length - 1
    ) {
        value /= 1024;
        unit += 1;
    }

    const decimals = unit >= 3 ? 1 : 0;

    return `${value.toFixed(decimals)} ${units[unit]}`;
}

function formatPercent(value) {
    if (
        value === null ||
        value === undefined
    ) {
        return "—";
    }

    return `${Number(value).toFixed(1)}%`;
}

function setServerState(online) {
    const statusDot =
        document.querySelector("#status-dot");

    const statusText =
        document.querySelector("#status-text");

    const apiState =
        document.querySelector("#api-state");

    statusDot.classList.remove(
        "status-loading",
        "status-online",
        "status-offline",
    );

    if (online) {
        statusDot.classList.add(
            "status-online",
        );

        statusText.textContent =
            "Server online";

        apiState.textContent =
            "Connected";

        return;
    }

    statusDot.classList.add(
        "status-offline",
    );

    statusText.textContent =
        "Server unavailable";

    apiState.textContent =
        "Disconnected";
}

function updateBackupStatus(backup) {
    const state =
        document.querySelector("#backup-state");

    const detail =
        document.querySelector("#backup-detail");

    state.classList.remove(
        "backup-healthy",
        "backup-warning",
    );

    if (!backup?.exists) {
        state.textContent = "Missing";

        state.classList.add(
            "backup-warning",
        );

        detail.textContent =
            "No backup found";

        return;
    }

    state.textContent = backup.healthy
        ? "Healthy"
        : "Overdue";

    state.classList.add(
        backup.healthy
            ? "backup-healthy"
            : "backup-warning",
    );

    detail.textContent =
        `${formatDuration(
            backup.age_seconds,
        )} · ${formatBytes(
            backup.size_bytes,
        )}`;
}

function renderPlayers(payload) {
    const list =
        document.querySelector(
            "#online-player-list",
        );

    const total =
        document.querySelector(
            "#online-player-total",
        );

    list.replaceChildren();

    if (!payload.available) {
        total.textContent =
            "Unavailable";

        const message =
            document.createElement("p");

        message.className = "muted";

        message.textContent =
            "Player information is temporarily unavailable.";

        list.appendChild(message);
        return;
    }

    total.textContent =
        String(payload.players.length);

    if (payload.players.length === 0) {
        const message =
            document.createElement("p");

        message.className = "muted";

        message.textContent =
            "Nobody is online.";

        list.appendChild(message);
        return;
    }

    for (const player of payload.players) {
        const card =
            document.createElement("article");

        card.className =
            "player-card";

        const identity =
            document.createElement("div");

        const name =
            document.createElement("a");

        name.className =
            "player-profile-link";

        name.href =
            `/players/${encodeURIComponent(
                player.name
                    .trim()
                    .toLowerCase(),
            )}`;

        name.textContent =
            player.name;

        const state =
            document.createElement("span");

        state.className =
            "player-online-state";

        state.textContent =
            "Online";

        identity.append(
            name,
            state,
        );

        const level =
            document.createElement("span");

        level.className =
            "player-level";

        level.textContent =
            player.level === null
                ? "Level unknown"
                : `Level ${player.level}`;

        card.append(
            identity,
            level,
        );

        list.appendChild(card);
    }
}

function renderLevelLeaderboard(payload) {
    const list = document.querySelector(
        "#level-leaderboard",
    );

    list.replaceChildren();

    if (!payload.players?.length) {
        const message =
            document.createElement("p");

        message.className = "muted";

        message.textContent =
            "No player levels have been recorded yet.";

        list.appendChild(message);
        return;
    }

    for (const player of payload.players) {
        const row =
            document.createElement("article");

        row.className =
            "leaderboard-row";

        const rank =
            document.createElement("span");

        rank.className =
            "leaderboard-rank";

        rank.textContent =
            `#${player.rank}`;

        const identity =
            document.createElement("div");

        identity.className =
            "leaderboard-identity";

        const name =
            document.createElement("a");

        name.className =
            "player-profile-link";

        name.href =
            `/players/${encodeURIComponent(
                player.name
                    .trim()
                    .toLowerCase(),
            )}`;

        name.textContent =
            player.name;

        const lastSeen =
            document.createElement("span");

        lastSeen.className =
            "leaderboard-last-seen";

        lastSeen.textContent =
            `Last seen ${new Date(
                player.last_seen_at,
            ).toLocaleString()}`;

        identity.append(
            name,
            lastSeen,
        );

        const level =
            document.createElement("span");

        level.className =
            "leaderboard-level";

        level.textContent =
            player.highest_level === null
                ? "Unknown"
                : `Level ${player.highest_level}`;

        row.append(
            rank,
            identity,
            level,
        );

        list.appendChild(row);
    }
}

async function refreshStatus() {
    const lastChecked =
        document.querySelector(
            "#last-checked",
        );

    try {
        const response = await fetch(
            "/api/status",
            {
                headers: {
                    Accept:
                        "application/json",
                },
                cache: "no-store",
            },
        );

        if (!response.ok) {
            throw new Error(
                `HTTP ${response.status}`,
            );
        }

        const data =
            await response.json();

        setServerState(
            data.online,
        );

        document.querySelector(
            "#server-name",
        ).textContent =
            data.name ??
            "Palworld Server";

        document.querySelector(
            "#server-version",
        ).textContent =
            data.version ??
            "Unknown";

        document.querySelector(
            "#player-count",
        ).textContent =
            `${data.players.current} / ` +
            `${data.players.maximum}`;

        document.querySelector(
            "#server-fps",
        ).textContent =
            data.server_fps ??
            "—";

        document.querySelector(
            "#frame-time",
        ).textContent =
            formatFrameTime(
                data.frame_time_ms,
            );

        document.querySelector(
            "#uptime",
        ).textContent =
            formatUptime(
                data.uptime_seconds,
            );

        document.querySelector(
            "#world-day",
        ).textContent =
            data.world_day ??
            "—";

        document.querySelector(
            "#base-count",
        ).textContent =
            data.base_count ??
            "—";

        const infrastructure =
            data.infrastructure;

        document.querySelector(
            "#cpu-percent",
        ).textContent =
            formatPercent(
                infrastructure?.cpu_percent,
            );

        document.querySelector(
            "#memory-percent",
        ).textContent =
            formatPercent(
                infrastructure
                    ?.memory_used_percent,
            );

        document.querySelector(
            "#memory-detail",
        ).textContent =
            infrastructure
                ?.memory_total_bytes
                ? `${formatBytes(
                    infrastructure
                        .memory_used_bytes,
                )} / ${formatBytes(
                    infrastructure
                        .memory_total_bytes,
                )}`
                : "Unavailable";

        document.querySelector(
            "#swap-percent",
        ).textContent =
            formatPercent(
                infrastructure
                    ?.swap_used_percent,
            );

        document.querySelector(
            "#swap-detail",
        ).textContent =
            infrastructure
                ?.swap_total_bytes
                ? `${formatBytes(
                    infrastructure
                        .swap_used_bytes,
                )} / ${formatBytes(
                    infrastructure
                        .swap_total_bytes,
                )}`
                : "Not configured";

        document.querySelector(
            "#disk-percent",
        ).textContent =
            formatPercent(
                infrastructure
                    ?.disk_used_percent,
            );

        document.querySelector(
            "#disk-detail",
        ).textContent =
            infrastructure
                ?.disk_total_bytes
                ? `${formatBytes(
                    infrastructure
                        .disk_used_bytes,
                )} / ${formatBytes(
                    infrastructure
                        .disk_total_bytes,
                )}`
                : "Unavailable";

        updateBackupStatus(
            data.latest_backup,
        );

        lastChecked.textContent =
            `Last checked ${new Date(
                data.checked_at,
            ).toLocaleString()}`;
    } catch (error) {
        setServerState(false);

        lastChecked.textContent =
            "Dashboard could not contact the API";

        console.error(
            "Dashboard refresh failed",
            error,
        );
    }
}

async function refreshPlayers() {
    try {
        const response = await fetch(
            "/api/players",
            {
                headers: {
                    Accept:
                        "application/json",
                },
                cache: "no-store",
            },
        );

        if (!response.ok) {
            throw new Error(
                `HTTP ${response.status}`,
            );
        }

        const payload =
            await response.json();

        renderPlayers(payload);
    } catch (error) {
        renderPlayers({
            available: false,
            players: [],
        });

        console.error(
            "Player refresh failed",
            error,
        );
    }
}

async function refreshLevelLeaderboard() {
    try {
        const response = await fetch(
            "/api/leaderboards/levels?limit=10",
            {
                headers: {
                    Accept: "application/json",
                },
                cache: "no-store",
            },
        );

        if (!response.ok) {
            throw new Error(
                `HTTP ${response.status}`,
            );
        }

        renderLevelLeaderboard(
            await response.json(),
        );
    } catch (error) {
        const list = document.querySelector(
            "#level-leaderboard",
        );

        list.replaceChildren();

        const message =
            document.createElement("p");

        message.className = "muted";
        message.textContent =
            "Leaderboard is temporarily unavailable.";

        list.appendChild(message);

        console.error(
            "Leaderboard refresh failed",
            error,
        );
    }
}

function formatPlaytime(totalSeconds) {
    if (totalSeconds === null || totalSeconds === undefined) {
        return "—";
    }

    const days = Math.floor(totalSeconds / 86400);
    const hours = Math.floor((totalSeconds % 86400) / 3600);
    const minutes = Math.floor((totalSeconds % 3600) / 60);

    if (days > 0) {
        return `${days}d ${hours}h`;
    }

    if (hours > 0) {
        return `${hours}h ${minutes}m`;
    }

    return `${minutes}m`;
}

function renderPlaytimeLeaderboard(payload) {
    const list = document.querySelector(
        "#playtime-leaderboard",
    );

    list.replaceChildren();

    if (!payload.players?.length) {
        const message =
            document.createElement("p");

        message.className = "muted";

        message.textContent =
            "No playtime has been tracked yet.";

        list.appendChild(message);
        return;
    }

    for (const player of payload.players) {
        const row =
            document.createElement("article");

        row.className =
            "leaderboard-row";

        const rank =
            document.createElement("span");

        rank.className =
            "leaderboard-rank";

        rank.textContent =
            `#${player.rank}`;

        const identity =
            document.createElement("div");

        identity.className =
            "leaderboard-identity";

        const name =
            document.createElement("a");

        name.className =
            "player-profile-link";

        name.href =
            `/players/${encodeURIComponent(
                player.name
                    .trim()
                    .toLowerCase(),
            )}`;

        name.textContent =
            player.name;

        const detail =
            document.createElement("span");

        detail.className =
            "leaderboard-last-seen";

        detail.textContent =
            `${player.session_count} session${
                player.session_count === 1
                    ? ""
                    : "s"
            }${
                player.currently_online
                    ? " · Online"
                    : ""
            }`;

        identity.append(
            name,
            detail,
        );

        const time =
            document.createElement("span");

        time.className =
            "leaderboard-level";

        time.textContent =
            formatPlaytime(
                player.total_seconds,
            );

        row.append(
            rank,
            identity,
            time,
        );

        list.appendChild(row);
    }
}

async function refreshPlaytimeLeaderboard() {
    try {
        const response = await fetch(
            "/api/leaderboards/playtime?limit=10",
            {
                headers: {
                    Accept: "application/json",
                },
                cache: "no-store",
            },
        );

        if (!response.ok) {
            throw new Error(`HTTP ${response.status}`);
        }

        renderPlaytimeLeaderboard(
            await response.json(),
        );
    } catch (error) {
        console.error(
            "Playtime leaderboard refresh failed",
            error,
        );
    }
}

function refreshDashboard() {
    refreshStatus();
    refreshPlayers();
    refreshLevelLeaderboard();
    refreshPlaytimeLeaderboard();
}

refreshDashboard();

setInterval(
    refreshDashboard,
    REFRESH_INTERVAL_MS,
);
