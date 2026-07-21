from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path

from armory_parser.extractor import SnapshotError, extract_snapshot


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Extract a sanitized Paldeck snapshot from a Palworld backup",
    )
    parser.add_argument(
        "snapshot",
        type=Path,
        help="Path to a completed Palworld .tar.gz backup",
    )
    args = parser.parse_args()

    try:
        identity_secret = _read_identity_secret()
        result = extract_snapshot(
            archive_path=args.snapshot,
            identity_secret=identity_secret,
        )
    except (SnapshotError, OSError) as exc:
        print(f"Paldeck extraction failed: {exc}", file=sys.stderr)
        return 1

    json.dump(result, sys.stdout, separators=(",", ":"), sort_keys=True)
    sys.stdout.write("\n")
    return 0


def _read_identity_secret() -> bytes:
    secret_file = os.environ.get("ARMORY_ID_SECRET_FILE")
    if secret_file:
        secret = Path(secret_file).read_bytes().strip()
    else:
        secret = os.environ.get("ARMORY_ID_SECRET", "").encode("utf-8")

    if not secret:
        raise SnapshotError(
            "Set ARMORY_ID_SECRET_FILE or ARMORY_ID_SECRET"
        )
    return secret


if __name__ == "__main__":
    raise SystemExit(main())
