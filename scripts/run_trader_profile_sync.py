"""Run one quota-safe, low-priority Trader OpenSea profile sync cycle."""

from __future__ import annotations

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from refresh_opensea_account_profiles import (
    DEFAULT_MIN_REMAINING,
    DEFAULT_REQUEST_LIMIT,
    PROFILE_SNAPSHOT,
    refresh,
)

LOCK_PATH = PROFILE_SNAPSHOT.with_name("trader_profile_sync.lock")
AUTOSYNC_STALE_HOURS = 720

if sys.platform == "win32":
    import msvcrt
else:
    import fcntl


def acquire_lock(path: Path = LOCK_PATH):
    path.parent.mkdir(parents=True, exist_ok=True)
    handle = path.open("a+b")
    try:
        handle.seek(0)
        if handle.read(1) == b"":
            handle.write(b"0")
            handle.flush()
        handle.seek(0)
        if sys.platform == "win32":
            try:
                msvcrt.locking(handle.fileno(), msvcrt.LK_NBLCK, 1)
            except OSError:
                handle.close()
                return None
        else:
            try:
                fcntl.flock(handle.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
            except OSError:
                handle.close()
                return None
        return handle
    except OSError:
        handle.close()
        return None


def release_lock(handle) -> None:
    try:
        handle.seek(0)
        if sys.platform == "win32":
            msvcrt.locking(handle.fileno(), msvcrt.LK_UNLCK, 1)
        else:
            fcntl.flock(handle.fileno(), fcntl.LOCK_UN)
    finally:
        handle.close()


def run_once() -> dict:
    lock = acquire_lock(LOCK_PATH)
    if lock is None:
        return {"status": "already_running", "requested_limit": DEFAULT_REQUEST_LIMIT, "min_remaining": DEFAULT_MIN_REMAINING}
    try:
        result = refresh(
            limit=DEFAULT_REQUEST_LIMIT,
            min_remaining=DEFAULT_MIN_REMAINING,
            stale_hours=AUTOSYNC_STALE_HOURS,
        )
        result["status"] = "completed"
        return result
    finally:
        release_lock(lock)


if __name__ == "__main__":
    print(json.dumps(run_once(), sort_keys=True))
