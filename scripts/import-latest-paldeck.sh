#!/usr/bin/env bash

set -Eeuo pipefail

project_directory="${PALWORLD_DASHBOARD_DIRECTORY:-/opt/palworld-dashboard}"
backup_directory="${PALWORLD_BACKUP_DIRECTORY:-/opt/palworld/palworld/backups}"
secret_file="${ARMORY_ID_SECRET_FILE:-${project_directory}/.armory-id-secret}"
parser_image="${ARMORY_PARSER_IMAGE:-palworld-armory-parser:latest}"
lock_file="${ARMORY_IMPORT_LOCK_FILE:-/tmp/palworld-armory-import.lock}"

exec 9>"${lock_file}"
if ! flock --nonblock 9; then
    echo "A Paldeck import is already running" >&2
    exit 0
fi

if [[ ! -r "${secret_file}" ]]; then
    echo "Armory identity secret is not readable: ${secret_file}" >&2
    exit 1
fi

latest_snapshot="$({
    find "${backup_directory}" \
        -maxdepth 1 \
        -type f \
        -name 'palworld-save-*.tar.gz' \
        -printf '%T@ %f\n'
} | sort --numeric-sort --reverse | sed -n '1p' | cut -d ' ' -f 2-)"

if [[ -z "${latest_snapshot}" ]]; then
    echo "No completed Palworld backup was found" >&2
    exit 1
fi

docker run --rm \
    --user "$(id -u):$(id -g)" \
    --network none \
    --read-only \
    --tmpfs /tmp:rw,noexec,nosuid,size=64m \
    --cap-drop ALL \
    --security-opt no-new-privileges \
    --volume "${backup_directory}:/snapshots:ro" \
    --volume "${secret_file}:/run/secrets/armory-id:ro" \
    --env ARMORY_ID_SECRET_FILE=/run/secrets/armory-id \
    "${parser_image}" \
    "/snapshots/${latest_snapshot}" \
    | docker compose \
        --file "${project_directory}/compose.yml" \
        --project-directory "${project_directory}" \
        exec --no-TTY dashboard \
        python -m app.armory_cli
