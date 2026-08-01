#!/usr/bin/env bash
set -Eeuo pipefail
backup_directory="${PALWORLD_BACKUP_DIRECTORY:-/opt/palworld/palworld/backups}"
output_file="${BACKUP_STATUS_OUTPUT:-/opt/palworld-dashboard/runtime/backup-status.json}"
latest_backup="$(find "${backup_directory}" -maxdepth 1 -type f -name '*.tar.gz' -printf '%T@ %p\n' | sort -nr | sed -n '1p' | cut -d ' ' -f 2-)"
[[ -n "${latest_backup}" ]] || { echo "No completed backup found" >&2; exit 1; }
output_directory="$(dirname "${output_file}")"
mkdir -p "${output_directory}"
temporary_file="$(mktemp "${output_directory}/backup-status.XXXXXX")"
trap 'rm -f "${temporary_file}"' EXIT
python3 - "${latest_backup}" "${temporary_file}" <<'PY'
import json, os, sys
from datetime import UTC, datetime
from pathlib import Path
backup = Path(sys.argv[1])
output = Path(sys.argv[2])
stat = backup.stat()
output.write_text(json.dumps({
    "created_at": datetime.fromtimestamp(stat.st_mtime, UTC).isoformat(),
    "size_bytes": stat.st_size,
}, separators=(",", ":")) + "\n", encoding="utf-8")
os.chmod(output, 0o644)
PY
mv -f "${temporary_file}" "${output_file}"
trap - EXIT
