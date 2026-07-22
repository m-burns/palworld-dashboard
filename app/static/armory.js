function formatSnapshotAge(value) {
    const timestamp = new Date(value);
    const seconds = Math.max(0, Math.floor((Date.now() - timestamp) / 1000));
    if (seconds < 3600) {
        return `${Math.floor(seconds / 60)}m ago`;
    }
    if (seconds < 86400) {
        return `${Math.floor(seconds / 3600)}h ago`;
    }
    return `${Math.floor(seconds / 86400)}d ago`;
}

function createLeaderboardRow(player) {
    const row = document.createElement("a");
    row.className = "armory-rank-row";
    row.href = `/armory/players/${player.player_id}`;

    const rank = document.createElement("span");
    rank.className = "armory-rank-number";
    rank.textContent = `#${player.rank}`;

    const identity = document.createElement("div");
    identity.className = "armory-rank-identity";
    const name = document.createElement("strong");
    name.textContent = player.display_name;
    const detail = document.createElement("span");
    detail.textContent = `${player.encountered_entries} encountered · ${player.total_captures} captures`;
    identity.append(name, detail);

    const progress = document.createElement("div");
    progress.className = "armory-rank-progress";
    const progressText = document.createElement("div");
    const fraction = document.createElement("strong");
    fraction.textContent = `${player.completed_entries} / ${player.completion_total}`;
    const percent = document.createElement("span");
    percent.textContent = `${player.completion_percent.toFixed(2)}%`;
    progressText.append(fraction, percent);
    const track = document.createElement("div");
    track.className = "progress-track";
    const fill = document.createElement("span");
    fill.style.width = `${player.completion_percent}%`;
    track.appendChild(fill);
    progress.append(progressText, track);

    const arrow = document.createElement("span");
    arrow.className = "armory-rank-arrow";
    arrow.textContent = "→";
    row.append(rank, identity, progress, arrow);
    return row;
}

function renderLeaderboard(payload) {
    document.querySelector("#armory-loading").hidden = true;
    const empty = document.querySelector("#armory-empty");
    const leaderboard = document.querySelector("#armory-leaderboard");

    if (!payload.available || !payload.players.length) {
        empty.hidden = false;
        return;
    }

    document.querySelector("#armory-player-total").textContent = payload.players.length;
    document.querySelector("#armory-catalog-total").textContent = payload.completion_total;
    document.querySelector("#armory-snapshot-age").textContent = formatSnapshotAge(payload.snapshot_created_at);
    document.querySelector("#armory-snapshot-time").textContent = new Date(payload.snapshot_created_at).toLocaleString();

    leaderboard.replaceChildren(...payload.players.map(createLeaderboardRow));
    leaderboard.hidden = false;
}

async function loadArmory() {
    try {
        const response = await fetch("/api/armory/leaderboard?limit=100", {
            headers: {Accept: "application/json"},
            cache: "no-store",
        });
        if (!response.ok) {
            throw new Error(`HTTP ${response.status}`);
        }
        renderLeaderboard(await response.json());
    } catch (error) {
        document.querySelector("#armory-loading").hidden = true;
        const empty = document.querySelector("#armory-empty");
        empty.hidden = false;
        empty.querySelector("strong").textContent = "Armory temporarily unavailable";
        console.error("Armory load failed", error);
    }
}

loadArmory();
