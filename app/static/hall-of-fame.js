const MEDALS = ["Gold", "Silver", "Bronze"];

function formatHallPlaytime(totalSeconds) {
    const days = Math.floor(totalSeconds / 86400);
    const hours = Math.floor((totalSeconds % 86400) / 3600);
    if (days > 0) return `${days}d ${hours}h`;
    const minutes = Math.floor((totalSeconds % 3600) / 60);
    return hours > 0 ? `${hours}h ${minutes}m` : `${minutes}m`;
}

function createHallEntry(player, index, value, href) {
    const entry = document.createElement("a");
    entry.className = `hall-entry hall-place-${index + 1}`;
    entry.href = href;

    const place = document.createElement("span");
    place.className = "hall-place";
    place.textContent = String(index + 1);

    const identity = document.createElement("div");
    identity.className = "hall-identity";

    const medal = document.createElement("small");
    medal.textContent = MEDALS[index];

    const name = document.createElement("strong");
    name.textContent = player;

    identity.append(medal, name);

    const record = document.createElement("strong");
    record.className = "hall-record";
    record.textContent = value;

    entry.append(place, identity, record);
    return entry;
}

function renderHall(selector, entries, mapEntry, emptyMessage) {
    const container = document.querySelector(selector);
    container.replaceChildren();

    if (!entries.length) {
        const message = document.createElement("p");
        message.className = "muted";
        message.textContent = emptyMessage;
        container.appendChild(message);
        return;
    }

    entries.slice(0, 3).forEach((entry, index) => {
        container.appendChild(mapEntry(entry, index));
    });
}

async function fetchJson(url) {
    const response = await fetch(url, {
        headers: {Accept: "application/json"},
        cache: "no-store",
    });
    if (!response.ok) throw new Error(`${url}: HTTP ${response.status}`);
    return response.json();
}

async function loadHallOfFame() {
    const updated = document.querySelector("#hall-updated");

    try {
        const [levels, playtime, armory] = await Promise.all([
            fetchJson("/api/leaderboards/levels?limit=3"),
            fetchJson("/api/leaderboards/playtime?limit=3"),
            fetchJson("/api/armory/leaderboard?limit=3"),
        ]);

        renderHall(
            "#hall-level",
            levels.players || [],
            (player, index) => createHallEntry(
                player.name,
                index,
                `Level ${player.highest_level ?? "—"}`,
                `/players/${encodeURIComponent(player.name.trim().toLowerCase())}`,
            ),
            "No level records yet.",
        );

        renderHall(
            "#hall-playtime",
            playtime.players || [],
            (player, index) => createHallEntry(
                player.name,
                index,
                formatHallPlaytime(player.total_seconds),
                `/players/${encodeURIComponent(player.name.trim().toLowerCase())}`,
            ),
            "No playtime records yet.",
        );

        renderHall(
            "#hall-armory",
            armory.available ? armory.players || [] : [],
            (player, index) => createHallEntry(
                player.display_name,
                index,
                `${player.completion_percent.toFixed(1)}%`,
                `/armory/players/${player.player_id}`,
            ),
            "No Paldeck snapshot has been imported yet.",
        );

        updated.textContent = `Records refreshed ${new Date().toLocaleString()}`;
    } catch (error) {
        updated.textContent = "Hall of Fame records are temporarily unavailable.";
        console.error("Hall of Fame refresh failed", error);
    }
}

loadHallOfFame();
