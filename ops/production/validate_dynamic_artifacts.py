"""Validate freshly generated dynamic artifacts through application readers.

This command is intentionally read-only.  It is used by the guarded
production orchestration after refresh builders finish and before an app is
started.  It never prints payloads or environment values.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
from datetime import datetime, timezone
from pathlib import Path
import sys


def _max_enriched_date(data_dir: Path) -> str:
    values: list[datetime] = []
    for path in sorted((data_dir / "sales_enriched").glob("*.csv")):
        try:
            import pandas as pd

            frame = pd.read_csv(path, usecols=["sale_date"])
            parsed = pd.to_datetime(frame["sale_date"], errors="coerce", utc=True).dropna()
            values.extend(value.to_pydatetime() for value in parsed)
        except (OSError, ValueError, KeyError, ImportError):
            continue
    if not values:
        return ""
    # The current market builders publish source_latest_date at UTC-day
    # precision even though source sales rows contain full timestamps.
    return max(values).astimezone(timezone.utc).date().isoformat()


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def validate(repo_root: Path, data_dir: Path, env_path: Path | None) -> dict[str, object]:
    sys.path.insert(0, str(repo_root / "scripts"))
    from market_snapshot_contract import inspect_market_snapshot  # noqa: PLC0415

    market_contract = inspect_market_snapshot(data_dir)
    package_root = repo_root / "streamlit_opensea_sales"
    sys.path.insert(0, str(package_root))
    if env_path and env_path.exists():
        # The application readers are read-only.  Only a process-local source
        # selector is needed here; secrets remain in the child environment.
        for line in env_path.read_text(encoding="utf-8").splitlines():
            if "=" in line and not line.lstrip().startswith("#"):
                key, value = line.split("=", 1)
                if key.strip() in {"GUNZSCOPE_SUPPLY_SOURCE"}:
                    os.environ.setdefault(key.strip(), value.strip().strip("\"'"))
    os.environ["GUNZSCOPE_SUPPLY_SOURCE"] = "v3"

    import item_class_data
    import gunzscope_supply
    import market_data_access
    import opensea_account_profiles
    import trader_analytics

    manifest = market_data_access.load_market_manifest()
    build_id = market_data_access.get_market_build_id_from_manifest(manifest)
    if not build_id:
        raise ValueError("market build identity missing")
    expected_latest = market_contract["raw_latest_date"]
    if not expected_latest:
        raise ValueError("enriched source date missing")
    period = market_data_access.load_market_period_summaries(
        cache_buster=build_id,
        file_version=market_data_access.get_market_period_summaries_file_version(),
        expected_source_latest_date=expected_latest,
    )
    expansion = market_data_access.load_market_expansion_metrics(
        cache_buster=build_id,
        file_version=market_data_access.get_market_expansion_metrics_file_version(),
        expected_source_latest_date=expected_latest,
    )
    if not period or not expansion:
        raise ValueError("market runtime reader rejected artifact")
    if period.get("source_market_build_id") != build_id or expansion.get("source_market_build_id") != build_id:
        raise ValueError("market build identity mismatch")
    if period.get("source_latest_date") != expected_latest or expansion.get("source_latest_date") != expected_latest:
        raise ValueError("market latest date mismatch")

    trader_path = data_dir / "trader_analytics_snapshot.json"
    trader_payload = trader_analytics.load_current_snapshot(trader_path)
    if not trader_payload or trader_payload.get("event_count", 0) <= 0 or trader_payload.get("wallet_count", 0) <= 0:
        raise ValueError("trader reader rejected artifact")
    trader_analytics.validate_snapshot(trader_payload)
    if len(trader_payload.get("wallets", [])) != trader_payload.get("wallet_count"):
        raise ValueError("trader wallet count mismatch")

    item_path = data_dir / "item_class_snapshot.json"
    item_payload = item_class_data.load_item_class_snapshot(str(item_path), item_path.stat().st_mtime_ns)
    if item_payload.get("schema_version") != 1 or not item_payload.get("items"):
        raise ValueError("item class reader rejected artifact")
    if not item_class_data.source_class_mapping(item_payload) or not item_class_data.class_mapping(item_payload):
        raise ValueError("item class mappings missing")
    item_name = next(iter(item_payload["items"]))
    if not item_class_data.class_for_name(item_name, item_payload):
        raise ValueError("item class resolution missing")

    supply_path = data_dir / "gunzscope_supply_snapshot_v3_provider.json"
    supply_payload = json.loads(supply_path.read_text(encoding="utf-8"))
    gunzscope_supply.validate_snapshot_v3(supply_payload)
    if not gunzscope_supply.load_snapshot_v3(str(supply_path), supply_path.stat().st_mtime).get("provider_items"):
        raise ValueError("supply reader rejected artifact")
    if gunzscope_supply.selected_supply_source() != "v3":
        raise ValueError("supply source is not v3")
    serving = gunzscope_supply.read_serving_snapshot()
    if not serving or serving.get("schema_version") != 3:
        raise ValueError("serving supply schema is not 3")

    profile_path = data_dir / "opensea_account_profiles_snapshot.json"
    profile_payload = opensea_account_profiles.load_profile_snapshot(profile_path)
    if profile_payload.get("schema_version") != 1 or not isinstance(profile_payload.get("profiles"), dict):
        raise ValueError("profile reader rejected artifact")
    if trader_payload.get("wallet_count", 0) > 0 and not isinstance(profile_payload.get("fallback_names"), dict):
        raise ValueError("profile fallback structure missing")

    secret_names = {
        "POSTGRES_PASSWORD",
        "API_GUNZSCOPE",
        "OTG_SITE_ANALYTICS_HMAC_SECRET",
        "OTG_FEEDBACK_TELEGRAM_BOT_TOKEN",
        "OTG_FEEDBACK_TELEGRAM_CHAT_ID",
        "OTG_INTERNAL_ANALYTICS_PASSWORD",
    }
    secrets = [os.environ.get(name, "") for name in secret_names if os.environ.get(name)]
    artifact_paths = [
        data_dir / "market_overview_enriched" / "market_period_summaries.json",
        data_dir / "market_overview_enriched" / "market_expansion_metrics.json",
        trader_path,
        item_path,
        supply_path,
        profile_path,
    ]
    for path in artifact_paths:
        raw = path.read_bytes()
        if any(secret.encode("utf-8") in raw for secret in secrets):
            raise ValueError("secret detected in dynamic artifact")

    return {
        "market_build_id": build_id,
        "source_latest_date": expected_latest,
        "market_base_snapshot": market_contract,
        "trader_event_count": trader_payload["event_count"],
        "trader_wallet_count": trader_payload["wallet_count"],
        "supply_source": "v3",
        "serving_schema": 3,
        "artifact_sha256": {path.name: _sha256(path) for path in artifact_paths},
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--repo-root", required=True, type=Path)
    parser.add_argument("--data-dir", required=True, type=Path)
    parser.add_argument("--env", type=Path)
    args = parser.parse_args()
    result = validate(args.repo_root.resolve(), args.data_dir.resolve(), args.env.resolve() if args.env else None)
    print("APPLICATION_READERS=PASS")
    print("SECRET_ARTIFACT_LEAK=NO")
    print(f"SUPPLY_SOURCE={result['supply_source']}")
    print(f"SERVING_SCHEMA={result['serving_schema']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
