let species = [];
let activeFilter = "all";

function matchesFilter(entry) {
    if (activeFilter === "captured") {
        return entry.capture_count > 0 && entry.counts_toward_completion;
    }
    if (activeFilter === "encountered") {
        return entry.discovered && entry.capture_count === 0;
    }
    return true;
}

function createSpeciesCard(entry) {
    const card = document.createElement("article");
    card.className = "armory-species-card";
    if (entry.capture_count > 0 && entry.counts_toward_completion) {
        card.classList.add("is-captured");
    } else if (entry.discovered) {
        card.classList.add("is-encountered");
    }

    const number = document.createElement("span");
    number.className = "armory-species-number";
    number.textContent = entry.paldeck_number ? `No. ${entry.paldeck_number}` : "Special";
    const name = document.createElement("strong");
    name.textContent = entry.name;
    const state = document.createElement("span");
    state.className = "armory-species-state";
    if (entry.capture_count > 0) {
        state.textContent = `${entry.capture_count} captured`;
    } else if (entry.discovered) {
        state.textContent = "Encountered";
    } else {
        state.textContent = "Recorded";
    }
    card.append(number, name, state);
    return card;
}

function renderSpecies() {
    const query = document.querySelector("#armory-search").value.trim().toLowerCase();
    const visible = species.filter((entry) => (
        matchesFilter(entry) && entry.name.toLowerCase().includes(query)
    ));
    document.querySelector("#armory-result-count").textContent = `${visible.length} recorded ${visible.length === 1 ? "Pal" : "Pals"}`;
    const grid = document.querySelector("#armory-species-grid");
    grid.replaceChildren(...visible.map(createSpeciesCard));
    if (!visible.length) {
        const message = document.createElement("p");
        message.className = "muted";
        message.textContent = "No recorded Pals match this view.";
        grid.appendChild(message);
    }
}

function renderProfile(profile) {
    document.title = `${profile.display_name} · Paldeck Armory`;
    document.querySelector("#armory-profile-name").textContent = profile.display_name;
    document.querySelector("#armory-profile-updated").textContent = `Snapshot from ${new Date(profile.snapshot_created_at).toLocaleString()}`;
    document.querySelector("#armory-profile-percent").textContent = `${profile.completion_percent.toFixed(2)}%`;
    document.querySelector("#armory-profile-progress").style.width = `${profile.completion_percent}%`;
    document.querySelector("#armory-profile-completed").textContent = `${profile.completed_entries} / ${profile.completion_total}`;
    document.querySelector("#armory-profile-encountered").textContent = profile.encountered_entries;
    document.querySelector("#armory-profile-captures").textContent = profile.total_captures;
    document.querySelector("#armory-profile-remaining").textContent = Math.max(0, profile.completion_total - profile.completed_entries);
    species = profile.species;
    renderSpecies();
}

async function loadProfile() {
    const playerId = document.querySelector(".armory-player-page").dataset.playerId;
    try {
        const response = await fetch(`/api/armory/players/${encodeURIComponent(playerId)}`, {
            headers: {Accept: "application/json"},
            cache: "no-store",
        });
        if (!response.ok) {
            throw new Error(`HTTP ${response.status}`);
        }
        renderProfile(await response.json());
    } catch (error) {
        document.querySelector("#armory-profile-name").textContent = "Unknown player";
        document.querySelector("#armory-profile-error").hidden = false;
        console.error("Armory profile load failed", error);
    }
}

document.querySelector("#armory-search").addEventListener("input", renderSpecies);
for (const button of document.querySelectorAll(".filter-button")) {
    button.addEventListener("click", () => {
        activeFilter = button.dataset.filter;
        document.querySelectorAll(".filter-button").forEach((item) => item.classList.toggle("active", item === button));
        renderSpecies();
    });
}

loadProfile();
