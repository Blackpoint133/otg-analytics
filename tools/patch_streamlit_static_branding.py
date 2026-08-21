"""Patch Streamlit static first-paint title/favicon for OTG OpenSea Sales.

This is a maintenance script. It never patches on import.
"""

from __future__ import annotations

import argparse
import datetime as dt
import hashlib
import importlib.util
import json
import os
import shutil
import sys
import tempfile
from pathlib import Path
from typing import Any


SCRIPT_VERSION = "2026-08-18.1"

EXPECTED_PYTHON = Path(sys.executable).resolve()
EXPECTED_STREAMLIT_VERSION = "1.55.0"
PROJECT_ROOT = Path(__file__).resolve().parents[1]


def _default_static_dir() -> Path:
    spec = importlib.util.find_spec("streamlit")
    if spec is None or spec.origin is None:
        return Path(sys.prefix) / "Lib" / "site-packages" / "streamlit" / "static"
    return Path(spec.origin).resolve().parent / "static"


EXPECTED_STATIC_DIR = _default_static_dir()
INDEX_PATH = EXPECTED_STATIC_DIR / "index.html"
FAVICON_PATH = EXPECTED_STATIC_DIR / "favicon.png"
OTG_FAVICON_SOURCE = PROJECT_ROOT / "img" / "logo.png"
BACKUP_ROOT = PROJECT_ROOT / ".publish_backups" / "streamlit_branding"

ORIGINAL_TITLE = "<title>Streamlit</title>"
PATCHED_TITLE = "<title>Off The Grid</title>"
FAVICON_LINK = '<link rel="shortcut icon" href="./favicon.png" />'
TITLE_GUARD_MARKER = "otg-runtime-title-guard:v1"
TITLE_GUARD_SCRIPT = """    <script>
      /* otg-runtime-title-guard:v1 */
      (() => {
        const requiredTitle = "Off The Grid";

        const enforceTitle = () => {
          if (document.title !== requiredTitle) {
            document.title = requiredTitle;
          }
        };

        enforceTitle();

        new MutationObserver(enforceTitle).observe(document.head, {
          childList: true,
          characterData: true,
          subtree: true
        });
      })();
    </script>"""
TITLE_GUARD_INSERTION = "\n\n" + TITLE_GUARD_SCRIPT

ORIGINAL_INDEX_SHA256 = (
    "b8db86052dc8c143d29d6ee6becf051021220cbd680bf3a972c5ab133d3d1f8a"
)
ORIGINAL_STREAMLIT_FAVICON_SHA256 = (
    "89fe5c560c3b6b3c4a3af5791691a2c606bb24b9f6deb7e71dccb509d588d7e1"
)
LEGACY_OTG_FAVICON_SHA256 = (
    "c51029da5cfefb3b81810132e1ea8f36f7a895a55e8943438ab39cac93e41f06"
)
OTG_FAVICON_SHA256 = (
    "f7ab71f0f98df3acfd8f79572e2a432ccf0b4801047c8aa715de10fc82827352"
)


EXIT_PATCHED = 0
EXIT_ORIGINAL = 10
EXIT_MIXED = 20
EXIT_UNSUPPORTED = 30
EXIT_FS_ERROR = 40


class BrandingError(Exception):
    """Base error for controlled patch failures."""


class UnsupportedError(BrandingError):
    """Environment or marker validation failed."""


class MixedStateError(BrandingError):
    """Installation is neither fully original nor fully patched."""


class FileSystemError(BrandingError):
    """Filesystem operation failed."""


def _norm_path(path: Path) -> str:
    return os.path.normcase(os.path.normpath(str(path.resolve())))


def _same_path(a: Path | str, b: Path | str) -> bool:
    return _norm_path(Path(a)) == _norm_path(Path(b))


def _sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _sha256_file(path: Path) -> str:
    return _sha256_bytes(path.read_bytes())


def _read_bytes(path: Path) -> bytes:
    try:
        return path.read_bytes()
    except OSError as exc:
        raise FileSystemError(f"Unable to read {path}: {exc}") from exc


def _write_atomic(path: Path, data: bytes, expected_sha256: str) -> None:
    tmp_path: Path | None = None
    try:
        with tempfile.NamedTemporaryFile(
            mode="wb",
            delete=False,
            dir=str(path.parent),
            prefix=f".{path.name}.",
            suffix=".tmp",
        ) as tmp:
            tmp_path = Path(tmp.name)
            tmp.write(data)
            tmp.flush()
            os.fsync(tmp.fileno())

        actual_tmp_hash = _sha256_file(tmp_path)
        if actual_tmp_hash != expected_sha256:
            raise FileSystemError(
                f"Temporary file hash mismatch for {path}: {actual_tmp_hash}"
            )

        os.replace(str(tmp_path), str(path))
        tmp_path = None

        actual_final_hash = _sha256_file(path)
        if actual_final_hash != expected_sha256:
            raise FileSystemError(
                f"Final file hash mismatch for {path}: {actual_final_hash}"
            )
    except OSError as exc:
        raise FileSystemError(f"Atomic write failed for {path}: {exc}") from exc
    finally:
        if tmp_path is not None:
            try:
                tmp_path.unlink(missing_ok=True)
            except OSError:
                pass


def _load_runtime() -> tuple[str, Path]:
    try:
        import streamlit  # type: ignore
        import streamlit.file_util as file_util  # type: ignore
    except Exception as exc:
        raise UnsupportedError(f"Unable to import Streamlit: {exc}") from exc

    version = str(streamlit.__version__)
    static_dir = Path(file_util.get_static_dir())
    return version, static_dir


def _validate_environment() -> tuple[str, Path]:
    if not _same_path(sys.executable, EXPECTED_PYTHON):
        raise UnsupportedError(
            f"Unexpected Python executable: {sys.executable}; "
            f"expected {EXPECTED_PYTHON}"
        )

    version, static_dir = _load_runtime()
    if version != EXPECTED_STREAMLIT_VERSION:
        raise UnsupportedError(
            f"Unexpected Streamlit version: {version}; "
            f"expected {EXPECTED_STREAMLIT_VERSION}"
        )
    if not _same_path(static_dir, EXPECTED_STATIC_DIR):
        raise UnsupportedError(
            f"Unexpected Streamlit static dir: {static_dir}; "
            f"expected {EXPECTED_STATIC_DIR}"
        )
    return version, static_dir


def _analyze_files(version: str, static_dir: Path) -> dict[str, Any]:
    result: dict[str, Any] = {
        "script_version": SCRIPT_VERSION,
        "python_executable": str(Path(sys.executable).resolve()),
        "streamlit_version": version,
        "static_directory": str(static_dir.resolve()),
        "index_path": str(INDEX_PATH),
        "favicon_path": str(FAVICON_PATH),
        "otg_favicon_source": str(OTG_FAVICON_SOURCE),
        "index_exists": INDEX_PATH.exists(),
        "favicon_exists": FAVICON_PATH.exists(),
        "otg_favicon_exists": OTG_FAVICON_SOURCE.exists(),
    }

    if not INDEX_PATH.exists() or not FAVICON_PATH.exists() or not OTG_FAVICON_SOURCE.exists():
        result["state"] = "UNSUPPORTED"
        result["reason"] = "Required target/source file is missing"
        return result

    index_bytes = _read_bytes(INDEX_PATH)
    favicon_bytes = _read_bytes(FAVICON_PATH)
    otg_favicon_bytes = _read_bytes(OTG_FAVICON_SOURCE)
    index_text = index_bytes.decode("utf-8", errors="replace")

    original_title_count = index_text.count(ORIGINAL_TITLE)
    patched_title_count = index_text.count(PATCHED_TITLE)
    favicon_link_count = index_text.count(FAVICON_LINK)
    title_guard_count = index_text.count(TITLE_GUARD_MARKER)
    complete_title_guard_count = index_text.count(TITLE_GUARD_SCRIPT)

    index_hash = _sha256_bytes(index_bytes)
    favicon_hash = _sha256_bytes(favicon_bytes)
    otg_favicon_hash = _sha256_bytes(otg_favicon_bytes)

    title_original = original_title_count == 1 and patched_title_count == 0
    title_patched = patched_title_count == 1 and original_title_count == 0
    favicon_original = favicon_hash == ORIGINAL_STREAMLIT_FAVICON_SHA256
    favicon_legacy = favicon_hash == LEGACY_OTG_FAVICON_SHA256
    favicon_patched = favicon_hash == OTG_FAVICON_SHA256
    guard_absent = title_guard_count == 0 and complete_title_guard_count == 0
    guard_patched = title_guard_count == 1 and complete_title_guard_count == 1
    source_valid = otg_favicon_hash == OTG_FAVICON_SHA256

    result.update(
        {
            "index_sha256": index_hash,
            "favicon_sha256": favicon_hash,
            "otg_favicon_sha256": otg_favicon_hash,
            "original_title_count": original_title_count,
            "patched_title_count": patched_title_count,
            "favicon_link_count": favicon_link_count,
            "title_guard_count": title_guard_count,
            "title_state": (
                "ORIGINAL"
                if title_original
                else "PATCHED"
                if title_patched
                else "UNSUPPORTED"
            ),
            "favicon_state": (
                "ORIGINAL"
                if favicon_original
                else "PATCHED"
                if favicon_patched
                else "UNSUPPORTED"
            ),
            "title_guard_state": (
                "ABSENT"
                if guard_absent
                else "PATCHED"
                if guard_patched
                else "UNSUPPORTED"
            ),
            "source_favicon_valid": source_valid,
        }
    )

    if not source_valid:
        result["state"] = "UNSUPPORTED"
        result["reason"] = "OTG favicon source hash does not match approved hash"
    elif favicon_link_count != 1:
        result["state"] = "UNSUPPORTED"
        result["reason"] = "favicon link marker missing or duplicated"
    elif original_title_count > 0 and patched_title_count > 0:
        result["state"] = "UNSUPPORTED"
        result["reason"] = "Both original and patched titles exist"
    elif original_title_count + patched_title_count != 1:
        result["state"] = "UNSUPPORTED"
        result["reason"] = "Permitted title marker missing or duplicated"
    elif title_guard_count > 1:
        result["state"] = "UNSUPPORTED"
        result["reason"] = "Runtime title guard marker is duplicated"
    elif title_guard_count != complete_title_guard_count:
        result["state"] = "UNSUPPORTED"
        result["reason"] = "Runtime title guard marker exists without exact guard"
    elif title_original and favicon_original:
        if guard_absent:
            result["state"] = "ORIGINAL"
            result["reason"] = "Supported original state; patch can be applied"
        else:
            result["state"] = "MIXED"
            result["reason"] = "Original title/favicon state unexpectedly has title guard"
    elif title_patched and favicon_patched:
        if guard_absent:
            result["state"] = "PATCHED_TITLE_FAVICON"
            result["reason"] = "Title and favicon are patched; runtime guard can be applied"
        elif guard_patched:
            result["state"] = "PATCHED_TITLE_FAVICON_AND_RUNTIME_GUARD"
            result["reason"] = "Fully guarded and valid"
        else:
            result["state"] = "UNSUPPORTED"
            result["reason"] = "Unsupported runtime title guard state"
    elif title_patched and favicon_legacy and guard_patched:
        result["state"] = "MIGRATION_FAVICON"
        result["reason"] = "Patched title guard is valid; favicon migration can be applied"
    elif (title_original or title_patched) and (favicon_original or favicon_patched):
        result["state"] = "MIXED"
        result["reason"] = "Title and favicon are in different supported states"
    else:
        result["state"] = "UNSUPPORTED"
        result["reason"] = "Unsupported title/favicon state"

    return result


def _status() -> dict[str, Any]:
    version, static_dir = _validate_environment()
    return _analyze_files(version, static_dir)


def _exit_code_for_state(state: str) -> int:
    if state == "PATCHED_TITLE_FAVICON_AND_RUNTIME_GUARD":
        return EXIT_PATCHED
    if state in {"ORIGINAL", "PATCHED_TITLE_FAVICON", "MIGRATION_FAVICON"}:
        return EXIT_ORIGINAL
    if state == "MIXED":
        return EXIT_MIXED
    return EXIT_UNSUPPORTED


def _print_result(result: dict[str, Any], as_json: bool) -> None:
    if as_json:
        print(json.dumps(result, indent=2, sort_keys=True))
        return

    for key in [
        "script_version",
        "python_executable",
        "streamlit_version",
        "static_directory",
        "index_path",
        "favicon_path",
        "otg_favicon_source",
        "index_exists",
        "favicon_exists",
        "otg_favicon_exists",
        "index_sha256",
        "favicon_sha256",
        "otg_favicon_sha256",
        "title_state",
        "favicon_state",
        "title_guard_count",
        "title_guard_state",
        "favicon_link_count",
        "source_favicon_valid",
        "state",
        "reason",
        "backup_directory",
        "message",
        "restart_required",
    ]:
        if key in result:
            print(f"{key}: {result[key]}")


def _make_backup(
    version: str,
    static_dir: Path,
    previous_state: str,
    expected_rollback_state: str,
) -> Path:
    BACKUP_ROOT.mkdir(parents=True, exist_ok=True)
    timestamp = dt.datetime.now(dt.timezone.utc).strftime("%Y%m%d_%H%M%S")
    backup_dir = BACKUP_ROOT / timestamp
    if backup_dir.exists():
        raise FileSystemError(f"Backup directory already exists: {backup_dir}")
    try:
        backup_dir.mkdir(parents=True, exist_ok=False)
        index_bytes = _read_bytes(INDEX_PATH)
        favicon_bytes = _read_bytes(FAVICON_PATH)
        (backup_dir / "index.html").write_bytes(index_bytes)
        (backup_dir / "favicon.png").write_bytes(favicon_bytes)
        manifest = {
            "utc_timestamp": dt.datetime.now(dt.timezone.utc).isoformat(),
            "script_version": SCRIPT_VERSION,
            "python_executable": str(Path(sys.executable).resolve()),
            "streamlit_version": version,
            "static_directory": str(static_dir.resolve()),
            "target_paths": {
                "index_html": str(INDEX_PATH),
                "favicon_png": str(FAVICON_PATH),
            },
            "original_paths": {
                "index_html": str(INDEX_PATH),
                "favicon_png": str(FAVICON_PATH),
            },
            "pre_migration_sha256": {
                "index_html": _sha256_bytes(index_bytes),
                "favicon_png": _sha256_bytes(favicon_bytes),
            },
            "original_sha256": {
                "index_html": _sha256_bytes(index_bytes),
                "favicon_png": _sha256_bytes(favicon_bytes),
            },
            "source_otg_favicon_path": str(OTG_FAVICON_SOURCE),
            "source_otg_favicon_sha256": _sha256_file(OTG_FAVICON_SOURCE),
            "previous_state": previous_state,
            "expected_rollback_state": expected_rollback_state,
        }
        manifest_bytes = (
            json.dumps(manifest, indent=2, sort_keys=True).encode("utf-8")
            + b"\n"
        )
        (backup_dir / "backup_manifest.json").write_bytes(manifest_bytes)
    except OSError as exc:
        raise FileSystemError(f"Unable to create backup: {exc}") from exc
    return backup_dir


def _insert_title_guard(text: str) -> str:
    if text.count(TITLE_GUARD_MARKER) != 0:
        raise UnsupportedError("Runtime title guard must be absent before insertion")
    if text.count(PATCHED_TITLE) != 1:
        raise UnsupportedError("Patched title marker must occur exactly once")
    if text.count(ORIGINAL_TITLE) != 0:
        raise UnsupportedError("Original title marker must be absent before guard insertion")

    candidate = text.replace(PATCHED_TITLE, PATCHED_TITLE + TITLE_GUARD_INSERTION, 1)
    if candidate.count(TITLE_GUARD_MARKER) != 1:
        raise UnsupportedError("Runtime title guard marker was not inserted exactly once")
    if candidate.count(TITLE_GUARD_SCRIPT) != 1:
        raise UnsupportedError("Exact runtime title guard was not inserted exactly once")
    if candidate.replace(TITLE_GUARD_INSERTION, "", 1) != text:
        raise UnsupportedError("Candidate index has changes beyond title guard insertion")
    return candidate


def _candidate_index_bytes(index_bytes: bytes, state: str) -> bytes:
    text = index_bytes.decode("utf-8")
    if state == "ORIGINAL":
        if text.count(ORIGINAL_TITLE) != 1:
            raise UnsupportedError("Original title marker must occur exactly once")
        if text.count(PATCHED_TITLE) != 0:
            raise UnsupportedError("Patched title marker must be absent in original state")
        title_patched_text = text.replace(ORIGINAL_TITLE, PATCHED_TITLE, 1)
        reverted_title = title_patched_text.replace(PATCHED_TITLE, ORIGINAL_TITLE, 1)
        if reverted_title != text:
            raise UnsupportedError("Candidate index has changes beyond title replacement")
        candidate_text = _insert_title_guard(title_patched_text)
        reverted = candidate_text.replace(TITLE_GUARD_INSERTION, "", 1).replace(
            PATCHED_TITLE, ORIGINAL_TITLE, 1
        )
        if reverted != text:
            raise UnsupportedError("Candidate index has changes beyond title and guard")
        return candidate_text.encode("utf-8")

    if state == "PATCHED_TITLE_FAVICON":
        return _insert_title_guard(text).encode("utf-8")

    if state == "MIGRATION_FAVICON":
        if text.count(PATCHED_TITLE) != 1 or text.count(ORIGINAL_TITLE) != 0:
            raise UnsupportedError("Patched title markers are invalid during favicon migration")
        if text.count(TITLE_GUARD_MARKER) != 1 or text.count(TITLE_GUARD_SCRIPT) != 1:
            raise UnsupportedError("Runtime title guard is invalid during favicon migration")
        return index_bytes

    raise UnsupportedError(f"Unsupported state for index candidate: {state}")


def apply_patch() -> dict[str, Any]:
    version, static_dir = _validate_environment()
    result = _analyze_files(version, static_dir)
    state = str(result["state"])

    if state == "PATCHED_TITLE_FAVICON_AND_RUNTIME_GUARD":
        result["message"] = "ALREADY PATCHED"
        result["restart_required"] = "No"
        return result
    if state == "MIXED":
        raise MixedStateError(result.get("reason", "Mixed state"))
    if state not in {"ORIGINAL", "PATCHED_TITLE_FAVICON", "MIGRATION_FAVICON"}:
        raise UnsupportedError(result.get("reason", "Unsupported state"))

    backup_dir = _make_backup(
        version,
        static_dir,
        previous_state=state,
        expected_rollback_state=state,
    )
    original_index_bytes = _read_bytes(INDEX_PATH)
    original_favicon_bytes = _read_bytes(FAVICON_PATH)
    candidate_index = _candidate_index_bytes(original_index_bytes, state)
    candidate_favicon = _read_bytes(OTG_FAVICON_SOURCE)
    if _sha256_bytes(candidate_favicon) != OTG_FAVICON_SHA256:
        raise UnsupportedError("OTG favicon source hash changed before apply")

    index_done = False
    favicon_done = False
    try:
        _write_atomic(INDEX_PATH, candidate_index, _sha256_bytes(candidate_index))
        index_done = True
        if state in {"ORIGINAL", "MIGRATION_FAVICON"}:
            _write_atomic(FAVICON_PATH, candidate_favicon, OTG_FAVICON_SHA256)
            favicon_done = True

        final = _analyze_files(version, static_dir)
        if final["state"] != "PATCHED_TITLE_FAVICON_AND_RUNTIME_GUARD":
            raise FileSystemError(f"Final patched state invalid: {final}")
        final["backup_directory"] = str(backup_dir)
        final["message"] = "PATCHED"
        final["restart_required"] = "Restart or reload the application process if required by the deployment"
        return final
    except Exception as exc:
        rollback_errors: list[str] = []
        try:
            if index_done:
                _write_atomic(INDEX_PATH, original_index_bytes, _sha256_bytes(original_index_bytes))
            if favicon_done and FAVICON_PATH.exists() and _sha256_file(FAVICON_PATH) != _sha256_bytes(original_favicon_bytes):
                _write_atomic(FAVICON_PATH, original_favicon_bytes, _sha256_bytes(original_favicon_bytes))
        except Exception as rollback_exc:
            rollback_errors.append(str(rollback_exc))
        if rollback_errors:
            raise FileSystemError(
                f"Apply failed: {exc}; rollback also failed: {rollback_errors}"
            ) from exc
        raise FileSystemError(
            f"Apply failed and original files were restored from backup {backup_dir}: {exc}"
        ) from exc


def rollback(backup_directory: Path) -> dict[str, Any]:
    version, static_dir = _validate_environment()
    backup_dir = backup_directory.resolve()
    manifest_path = backup_dir / "backup_manifest.json"
    backup_index = backup_dir / "index.html"
    backup_favicon = backup_dir / "favicon.png"

    try:
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    except Exception as exc:
        raise UnsupportedError(f"Invalid or missing backup manifest: {exc}") from exc

    if not backup_index.exists() or not backup_favicon.exists():
        raise UnsupportedError("Backup index.html or favicon.png is missing")

    if manifest.get("streamlit_version") != version:
        raise UnsupportedError("Backup Streamlit version does not match active runtime")
    if not _same_path(manifest.get("static_directory", ""), static_dir):
        raise UnsupportedError("Backup static directory does not match active runtime")
    if not _same_path(manifest.get("original_paths", {}).get("index_html", ""), INDEX_PATH):
        raise UnsupportedError("Backup index target does not match expected path")
    if not _same_path(manifest.get("original_paths", {}).get("favicon_png", ""), FAVICON_PATH):
        raise UnsupportedError("Backup favicon target does not match expected path")

    expected_index_hash = manifest.get("original_sha256", {}).get("index_html")
    expected_favicon_hash = manifest.get("original_sha256", {}).get("favicon_png")
    index_bytes = _read_bytes(backup_index)
    favicon_bytes = _read_bytes(backup_favicon)
    if _sha256_bytes(index_bytes) != expected_index_hash:
        raise UnsupportedError("Backup index.html hash does not match manifest")
    if _sha256_bytes(favicon_bytes) != expected_favicon_hash:
        raise UnsupportedError("Backup favicon.png hash does not match manifest")

    _write_atomic(INDEX_PATH, index_bytes, expected_index_hash)
    try:
        _write_atomic(FAVICON_PATH, favicon_bytes, expected_favicon_hash)
    except Exception:
        _write_atomic(INDEX_PATH, index_bytes, expected_index_hash)
        raise

    return {
        "script_version": SCRIPT_VERSION,
        "python_executable": str(Path(sys.executable).resolve()),
        "streamlit_version": version,
        "static_directory": str(static_dir.resolve()),
        "state": "ROLLED_BACK",
        "backup_directory": str(backup_dir),
        "index_sha256": _sha256_file(INDEX_PATH),
        "favicon_sha256": _sha256_file(FAVICON_PATH),
        "restart_required": "Restart or reload the application process if required by the deployment",
        "message": "ROLLBACK COMPLETE",
    }


def main() -> int:
    global EXPECTED_STATIC_DIR, INDEX_PATH, FAVICON_PATH, BACKUP_ROOT
    parser = argparse.ArgumentParser(description=__doc__)
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--check", action="store_true", help="Read-only status check")
    mode.add_argument("--apply", action="store_true", help="Apply branding patch")
    mode.add_argument("--rollback", metavar="BACKUP_DIRECTORY", help="Restore backup")
    parser.add_argument("--json", action="store_true", help="Print JSON output")
    parser.add_argument("--static-dir", type=Path, help="Optional Streamlit static directory override")
    parser.add_argument("--backup-root", type=Path, help="Optional timestamped backup directory")
    args = parser.parse_args()

    if args.static_dir:
        EXPECTED_STATIC_DIR = args.static_dir.resolve()
        INDEX_PATH = EXPECTED_STATIC_DIR / "index.html"
        FAVICON_PATH = EXPECTED_STATIC_DIR / "favicon.png"
    if args.backup_root:
        BACKUP_ROOT = args.backup_root.resolve()

    try:
        if args.check:
            result = _status()
            _print_result(result, args.json)
            return _exit_code_for_state(str(result["state"]))
        if args.apply:
            result = apply_patch()
            _print_result(result, args.json)
            return EXIT_PATCHED
        result = rollback(Path(args.rollback))
        _print_result(result, args.json)
        return EXIT_PATCHED
    except MixedStateError as exc:
        result = {"state": "MIXED", "error": str(exc)}
        _print_result(result, args.json)
        return EXIT_MIXED
    except UnsupportedError as exc:
        result = {"state": "UNSUPPORTED", "error": str(exc)}
        _print_result(result, args.json)
        return EXIT_UNSUPPORTED
    except FileSystemError as exc:
        result = {"state": "FILESYSTEM_ERROR", "error": str(exc)}
        _print_result(result, args.json)
        return EXIT_FS_ERROR
    except Exception as exc:
        result = {"state": "FILESYSTEM_ERROR", "error": repr(exc)}
        _print_result(result, args.json)
        return EXIT_FS_ERROR


if __name__ == "__main__":
    raise SystemExit(main())
