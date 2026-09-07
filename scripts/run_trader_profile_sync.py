"""Run one quota-safe, low-priority Trader OpenSea profile sync cycle."""

from __future__ import annotations

import json
import os
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


def _pid_is_running(pid: int) -> bool:
    if pid <= 0:
        return False
    try:
        os.kill(pid, 0)
        return True
    except (OSError, ValueError):
        return False


def acquire_lock(path: Path = LOCK_PATH):
    path.parent.mkdir(parents=True, exist_ok=True)
    for _ in range(2):
        try:
            handle = path.open("x", encoding="utf-8")
            handle.write(str(os.getpid()))
            handle.flush()
            return handle
        except FileExistsError:
            try:
                owner = int(path.read_text(encoding="utf-8").strip())
            except (OSError, ValueError):
                return None
            if _pid_is_running(owner):
                return None
            try:
                path.unlink()
            except OSError:
                return None
    return None


def run_once() -> dict:
    lock = acquire_lock(LOCK_PATH)
    if lock is None:
        return {"status": "already_running", "requested_limit": DEFAULT_REQUEST_LIMIT, "min_remaining": DEFAULT_MIN_REMAINING}
    try:
        result = refresh(limit=DEFAULT_REQUEST_LIMIT, min_remaining=DEFAULT_MIN_REMAINING)
        result["status"] = "completed"
        return result
    finally:
        lock.close()
        try:
            LOCK_PATH.unlink()
        except OSError:
            pass


if __name__ == "__main__":
    print(json.dumps(run_once(), sort_keys=True))
