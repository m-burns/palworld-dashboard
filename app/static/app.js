const REFRESH_INTERVAL_MS = 15_000;

function formatUptime(totalSeconds) {
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

function formatFrameTime(value) {
    if (value === null || value === undefined) {
        return "—";
    }

    return `${Number(value).toFixed(2)} ms`;
}

function formatBytes(bytes) {
    if (bytes === null || bytes === undefined) {
        return "—";
    }

    const units = ["B", "KB", "MB", "GB", "TB"];

    let value = Number(bytes);
    let unit = 0;

    while (value >= 1024 && unit < units.length - 1) {
        value /= 1024;
        unit++;
    }

    return `${value.toFixed(unit >= 3 ? 1 : 0)} ${units[unit]}`;
}

function formatPercent(value) {
    if (value === null || value === undefined) {
        return "—";
    }

    return `${Number(value).toFixed(1)}%`;
}

function setServerState(online) {
    const statusDot = document.querySelector("#status-dot");
    const statusText = document.querySelector("#status-text");
    const apiState = document.querySelector("#api-state");

    statusDot.classList.remove(
        "status-loading",
        "status-online",
        "status-offline",
    );

    if (online) {
        statusDot.classList.add("status-online");
        statusText.textContent = "Server online";
        apiState.textContent = "Connected";
        return;
    }

    statusDot.classList.add("status-offline");
    statusText.textContent = "Server unavailable";
    apiState.textContent = "Disconnected";
}

async function refreshDashboard() {
    const lastChecked = document.querySelector("#last-checked");

    try {
        const response = await fetch("/api/status", {
            headers: {
                Accept: "application/json",
            },
            cache: "no-store",
        });

        if (!response.ok) {
            throw new Error(`HTTP ${response.status}`);
        }

        const data = await response.json();

        setServerState(data.online);

        document.querySelector("#server-name").textContent =
            data.name ?? "Palworld Server";

        document.querySelector("#server-version").textContent =
            data.version ?? "Unknown";

        document.querySelector("#player-count").textContent =
            `${data.players.current} / ${data.players.maximum}`;

        document.querySelector("#server-fps").textContent =
            data.server_fps ?? "—";

        document.querySelector("#frame-time").textContent =
            formatFrameTime(data.frame_time_ms);

        document.querySelector("#uptime").textContent =
            formatUptime(data.uptime_seconds);

        document.querySelector("#world-day").textContent =
            data.world_day ?? "—";

        document.querySelector("#base-count").textContent =
            data.base_count ?? "—";

        // Infrastructure metrics

        const infrastructure = data.infrastructure;

        document.querySelector("#cpu-percent").textContent =
            formatPercent(infrastructure?.cpu_percent);

        document.querySelector("#memory-percent").textContent =
            formatPercent(infrastructure?.memory_used_percent);

        document.querySelector("#memory-detail").textContent =
            infrastructure?.memory_total_bytes
                ? `${formatBytes(
                      infrastructure.memory_used_bytes
                  )} / ${formatBytes(
                      infrastructure.memory_total_bytes
                  )}`
                : "Unavailable";

        document.querySelector("#swap-percent").textContent =
            formatPercent(infrastructure?.swap_used_percent);

        document.querySelector("#swap-detail").textContent =
            infrastructure?.swap_total_bytes
                ? `${formatBytes(
                      infrastructure.swap_used_bytes
                  )} / ${formatBytes(
                      infrastructure.swap_total_bytes
                  )}`
                : "Not configured";

        document.querySelector("#disk-percent").textContent =
            formatPercent(infrastructure?.disk_used_percent);

        document.querySelector("#disk-detail").textContent =
            infrastructure?.disk_total_bytes
                ? `${formatBytes(
                      infrastructure.disk_used_bytes
                  )} / ${formatBytes(
                      infrastructure.disk_total_bytes
                  )}`
                : "Unavailable";

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

refreshDashboard();

setInterval(
    refreshDashboard,
    REFRESH_INTERVAL_MS,
);
