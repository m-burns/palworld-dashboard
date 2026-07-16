function formatDuration(totalSeconds) {
    if (
        totalSeconds === null ||
        totalSeconds === undefined
    ) {
        return "—";
    }

    const days = Math.floor(totalSeconds / 86400);
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

function formatDate(value) {
    if (!value) {
        return "—";
    }

    return new Date(value).toLocaleString();
}

function setProfileState(online) {
    const dot = document.querySelector(
        "#profile-status-dot",
    );

    const status = document.querySelector(
        "#profile-status",
    );

    dot.classList.remove(
        "status-loading",
        "status-online",
        "status-offline",
    );

    if (online) {
        dot.classList.add("status-online");
        status.textContent = "Currently online";
        return;
    }

    dot.classList.add("status-offline");
    status.textContent = "Currently offline";
}

function renderProfile(profile) {
    document.title =
        `${profile.name} · Palworld Dashboard`;

    document.querySelector(
        "#profile-name",
    ).textContent = profile.name;

    setProfileState(
        profile.currently_online,
    );

    document.querySelector(
        "#profile-highest-level",
    ).textContent =
        profile.highest_level === null
            ? "Unknown"
            : `Level ${profile.highest_level}`;

    document.querySelector(
        "#profile-latest-level",
    ).textContent =
        profile.latest_level === null
            ? "Unknown"
            : `Level ${profile.latest_level}`;

    document.querySelector(
        "#profile-total-playtime",
    ).textContent =
        formatDuration(
            profile.total_playtime_seconds,
        );

    document.querySelector(
        "#profile-session-count",
    ).textContent =
        String(profile.session_count);

    document.querySelector(
        "#profile-longest-session",
    ).textContent =
        formatDuration(
            profile.longest_session_seconds,
        );

    document.querySelector(
        "#profile-average-session",
    ).textContent =
        formatDuration(
            profile.average_session_seconds,
        );

    document.querySelector(
        "#profile-first-seen",
    ).textContent =
        formatDate(profile.first_seen_at);

    document.querySelector(
        "#profile-last-seen",
    ).textContent =
        formatDate(profile.last_seen_at);

    document.querySelector(
        "#profile-completed-sessions",
    ).textContent =
        String(profile.completed_session_count);
}

async function loadProfile() {
    const page = document.querySelector(
        ".profile-page",
    );

    const playerKey =
        page.dataset.playerKey;

    try {
        const response = await fetch(
            `/api/players/${encodeURIComponent(
                playerKey,
            )}`,
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

        renderProfile(
            await response.json(),
        );
    } catch (error) {
        document.querySelector(
            "#profile-error",
        ).hidden = false;

        document.querySelector(
            "#profile-name",
        ).textContent =
            "Unknown player";

        setProfileState(false);

        console.error(
            "Player profile load failed",
            error,
        );
    }
}

loadProfile();