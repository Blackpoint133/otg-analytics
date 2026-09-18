"""Validated static catalog for the public Ecosystem directory."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any
from urllib.parse import urlparse


APP_ROOT = Path(__file__).resolve().parent
REPO_ROOT = APP_ROOT.parent
CATALOG_PATH = APP_ROOT / "config" / "ecosystem_projects.json"

ALLOWED_TYPES = {"official", "external_officially_linked", "community"}
ALLOWED_CATEGORIES = {
    "network",
    "game",
    "player_app",
    "wallet",
    "blockchain",
    "developer",
    "marketplace",
    "analytics",
    "game_tools",
}
REQUIRED_FIELDS = {
    "id",
    "name",
    "type",
    "category",
    "description",
    "url",
    "logo_asset",
    "source_url",
    "status",
    "featured",
    "tracking_key",
}


class EcosystemCatalogError(ValueError):
    """Raised when the static catalog violates its contract."""


def _require_https(value: Any, field: str, project_id: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise EcosystemCatalogError(f"{project_id}: {field} must be a non-empty HTTPS URL")
    parsed = urlparse(value.strip())
    if parsed.scheme != "https" or not parsed.netloc or parsed.username or parsed.password:
        raise EcosystemCatalogError(f"{project_id}: {field} must be an explicit HTTPS URL")
    return value.strip()


def _validate_project(project: Any, seen_ids: set[str], seen_tracking_keys: set[str]) -> dict[str, Any]:
    if not isinstance(project, dict):
        raise EcosystemCatalogError("each project must be an object")
    missing = REQUIRED_FIELDS - set(project)
    if missing:
        raise EcosystemCatalogError(f"project missing fields: {sorted(missing)}")

    project_id = project["id"]
    if not isinstance(project_id, str) or not project_id.strip():
        raise EcosystemCatalogError("project id must be a non-empty string")
    project_id = project_id.strip()
    if project_id in seen_ids:
        raise EcosystemCatalogError(f"duplicate project id: {project_id}")

    tracking_key = project["tracking_key"]
    if not isinstance(tracking_key, str) or not tracking_key.strip():
        raise EcosystemCatalogError(f"{project_id}: tracking_key must be a non-empty string")
    tracking_key = tracking_key.strip()
    if tracking_key != project_id:
        raise EcosystemCatalogError(f"{project_id}: tracking_key must equal id")
    if tracking_key in seen_tracking_keys:
        raise EcosystemCatalogError(f"duplicate tracking_key: {tracking_key}")

    for field in ("name", "description", "status"):
        if not isinstance(project[field], str) or not project[field].strip():
            raise EcosystemCatalogError(f"{project_id}: {field} must be non-empty")
    if project["type"] not in ALLOWED_TYPES:
        raise EcosystemCatalogError(f"{project_id}: unsupported type {project['type']!r}")
    if project["category"] not in ALLOWED_CATEGORIES:
        raise EcosystemCatalogError(f"{project_id}: unsupported category {project['category']!r}")
    if not isinstance(project["featured"], bool):
        raise EcosystemCatalogError(f"{project_id}: featured must be boolean")

    validated = dict(project)
    validated["id"] = project_id
    validated["tracking_key"] = tracking_key
    validated["url"] = _require_https(project["url"], "url", project_id)
    validated["source_url"] = _require_https(project["source_url"], "source_url", project_id)

    logo_asset = project["logo_asset"]
    if logo_asset is not None:
        if not isinstance(logo_asset, str) or not logo_asset or logo_asset.startswith(("/", "\\")) or ".." in Path(logo_asset).parts:
            raise EcosystemCatalogError(f"{project_id}: logo_asset must be a safe repository-relative path")
        asset_path = REPO_ROOT / logo_asset
        if not asset_path.is_file():
            raise EcosystemCatalogError(f"{project_id}: logo_asset does not exist: {logo_asset}")
        validated["logo_asset"] = logo_asset

    seen_ids.add(project_id)
    seen_tracking_keys.add(tracking_key)
    return validated


def validate_catalog_payload(payload: Any) -> tuple[dict[str, Any], ...]:
    if not isinstance(payload, dict) or payload.get("schema_version") != 1:
        raise EcosystemCatalogError("catalog schema_version must be 1")
    projects = payload.get("projects")
    if not isinstance(projects, list) or len(projects) != 12:
        raise EcosystemCatalogError("catalog must contain exactly 12 projects")
    seen_ids: set[str] = set()
    seen_tracking_keys: set[str] = set()
    validated = tuple(_validate_project(project, seen_ids, seen_tracking_keys) for project in projects)
    return validated


def load_ecosystem_catalog(path: Path | None = None) -> tuple[dict[str, Any], ...]:
    catalog_path = Path(path) if path else CATALOG_PATH
    try:
        payload = json.loads(catalog_path.read_text(encoding="utf-8"))
        return validate_catalog_payload(payload)
    except EcosystemCatalogError:
        raise
    except (OSError, json.JSONDecodeError) as exc:
        raise EcosystemCatalogError(f"unable to load ecosystem catalog: {exc}") from exc


def catalog_counts(projects: tuple[dict[str, Any], ...]) -> dict[str, int]:
    return {
        "official": sum(project["type"] == "official" for project in projects),
        "external_officially_linked": sum(project["type"] == "external_officially_linked" for project in projects),
        "community": sum(project["type"] == "community" for project in projects),
    }
