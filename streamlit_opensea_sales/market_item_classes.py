"""Prepared Sales by Item Class contract.

This module is deliberately independent of Streamlit.  The derived-data
builder and the read-only frontend loader use the same class metadata,
resolver, and payload validator so a chart cannot silently invent a second
taxonomy.
"""

from __future__ import annotations

import hashlib
import json
import math
import re
from pathlib import Path
from typing import Any

import pandas as pd


ITEM_CLASS_CONTRACT_VERSION = 1
ITEM_CLASS_SOURCE = "public.item_metadata_current.class + public.common_data.class fallback"
UNCLASSIFIED = "UNCLASSIFIED"

CURRENT_ITEM_CLASS_ORDER = (
    "Customization Item",
    "Weapon",
    "Body Part",
    "Weapon Skin",
    "Weapon Attachment",
    "Profile Customization",
)

CURRENT_ITEM_CLASS_COLORS = {
    "Customization Item": "#FF003A",
    "Weapon": "#FF8A65",
    "Body Part": "#67C77A",
    "Weapon Skin": "#8F78C6",
    "Weapon Attachment": "#5DA9E9",
    "Profile Customization": "#D8C3A5",
    UNCLASSIFIED: "#6B6B73",
}

# Reserved, muted colors for genuinely new snapshot classes.  Existing class
# colors are never drawn from this pool and therefore never reassigned.
_EXTENSION_COLORS = (
    "#B8C0CC", "#F08A5D", "#4EC5C1", "#C77DFF", "#A8DADC",
    "#F4A261", "#90BE6D", "#E9C46A", "#577590", "#F28482",
    "#84A59D", "#BDB2FF", "#FFAFCC", "#70D6FF", "#C9ADA7",
)


def _stable_id(name: str) -> str:
    value = re.sub(r"[^a-z0-9]+", "_", name.casefold()).strip("_")
    return value or f"class_{hashlib.sha256(name.encode('utf-8')).hexdigest()[:12]}"


def _extension_color(name: str, used: set[str]) -> str:
    digest = hashlib.sha256(name.encode("utf-8")).digest()
    start = digest[0] % len(_EXTENSION_COLORS)
    for offset in range(len(_EXTENSION_COLORS)):
        color = _EXTENSION_COLORS[(start + offset) % len(_EXTENSION_COLORS)]
        if color not in used:
            return color
    # A future taxonomy larger than the reserved palette is a data-contract
    # issue, not a reason to reassign an existing class's color.
    raise ValueError("ITEM_CLASS_EXTENSION_COLOR_CAPACITY_EXCEEDED")


def build_class_metadata(class_names: set[str] | list[str] | tuple[str, ...], include_unclassified: bool = False) -> list[dict[str, Any]]:
    """Return stable class IDs/order/colors for the supplied exact labels."""
    names = {str(name) for name in class_names if isinstance(name, str) and name}
    names -= {UNCLASSIFIED}
    ordered = [name for name in CURRENT_ITEM_CLASS_ORDER if name in names]
    ordered.extend(sorted(names - set(CURRENT_ITEM_CLASS_ORDER), key=lambda value: (value.casefold(), value)))
    if include_unclassified:
        ordered.append(UNCLASSIFIED)

    used = set(CURRENT_ITEM_CLASS_COLORS.values())
    metadata: list[dict[str, Any]] = []
    ids: set[str] = set()
    for index, name in enumerate(ordered):
        class_id = "unclassified" if name == UNCLASSIFIED else _stable_id(name)
        if class_id in ids:
            class_id = f"{class_id}_{hashlib.sha256(name.encode('utf-8')).hexdigest()[:8]}"
        ids.add(class_id)
        color = CURRENT_ITEM_CLASS_COLORS.get(name)
        if color is None:
            color = _extension_color(name, used)
        used.add(color)
        metadata.append({"id": class_id, "name": name, "order": index, "color": color})
    return metadata


def read_item_class_snapshot(path: Path) -> tuple[dict[str, Any], dict[str, str], dict[str, Any]]:
    """Read, hash, and parse one exact snapshot byte stream."""
    raw = path.read_bytes()
    payload = json.loads(raw.decode("utf-8"))
    if not isinstance(payload, dict) or not isinstance(payload.get("items"), dict):
        raise ValueError("ITEM_CLASS_SNAPSHOT_INVALID")
    mapping: dict[str, str] = {}
    for name, record in payload["items"].items():
        if not isinstance(name, str) or not isinstance(record, dict):
            continue
        class_name = record.get("class")
        if isinstance(class_name, str) and class_name.strip():
            mapping[name] = class_name.strip()
    identity = {
        "sha256": hashlib.sha256(raw).hexdigest(),
        "schema_version": payload.get("schema_version"),
        "source": payload.get("source", ""),
        "generated_at": payload.get("generated_at", ""),
    }
    return payload, mapping, identity


def snapshot_identity(path: Path) -> dict[str, Any]:
    return read_item_class_snapshot(path)[2]


def class_for_name(name: Any, mapping: dict[str, str]) -> str:
    """Resolve exact names, then only an unambiguous outer-trim alias."""
    raw = str(name)
    if raw in mapping:
        return mapping[raw]
    trimmed = raw.strip()
    if trimmed == raw:
        return UNCLASSIFIED
    candidates = {class_name for item_name, class_name in mapping.items() if item_name.strip() == trimmed}
    return next(iter(candidates)) if len(candidates) == 1 else UNCLASSIFIED


def build_sales_by_item_class(
    sales_df: pd.DataFrame,
    daily_df: pd.DataFrame,
    monthly_df: pd.DataFrame,
    snapshot_payload: dict[str, Any],
    snapshot_identity_value: dict[str, Any],
) -> dict[str, Any]:
    """Build a compact daily/monthly count payload from one snapshot instance."""
    if not isinstance(snapshot_payload, dict) or not isinstance(snapshot_identity_value, dict):
        raise ValueError("ITEM_CLASS_SNAPSHOT_REQUIRED")
    mapping = {
        str(name): str(record["class"]).strip()
        for name, record in snapshot_payload.get("items", {}).items()
        if isinstance(record, dict) and isinstance(record.get("class"), str) and record["class"].strip()
    }
    sales = sales_df.copy()
    if "name" not in sales.columns or "sale_date" not in sales.columns:
        raise ValueError("ITEM_CLASS_SALE_FIELDS_MISSING")
    sales["sale_date"] = pd.to_datetime(sales["sale_date"], errors="coerce", utc=True)
    if sales["sale_date"].isna().any():
        raise ValueError("ITEM_CLASS_SALE_DATE_INVALID")
    sales["_item_class"] = [class_for_name(value, mapping) for value in sales["name"]]
    unclassified = int((sales["_item_class"] == UNCLASSIFIED).sum())
    classified = int(len(sales) - unclassified)
    class_names = set(sales.loc[sales["_item_class"] != UNCLASSIFIED, "_item_class"])
    classes = build_class_metadata(class_names, include_unclassified=unclassified > 0)
    class_id_by_name = {entry["name"]: entry["id"] for entry in classes}

    daily_axis = daily_df.copy()
    daily_axis["date"] = pd.to_datetime(daily_axis["date"], errors="coerce", utc=True).dt.normalize()
    if daily_axis["date"].isna().any() or daily_axis["date"].duplicated().any():
        raise ValueError("ITEM_CLASS_DAILY_AXIS_INVALID")
    sale_dates = set(sales["sale_date"].dt.normalize())
    if not sale_dates.issubset(set(daily_axis["date"])):
        raise ValueError("ITEM_CLASS_DAILY_AXIS_INCOMPLETE")

    def counts_for(frame: pd.DataFrame) -> list[dict[str, Any]]:
        values = frame["_item_class"].value_counts()
        return [
            {"class_id": entry["id"], "sales": int(values.get(entry["name"], 0))}
            for entry in classes
        ]

    daily_rows = []
    for date in daily_axis["date"]:
        frame = sales[sales["sale_date"].dt.normalize() == date]
        daily_rows.append({"date": date.strftime("%Y-%m-%d"), "total_sales": int(len(frame)), "counts": counts_for(frame)})

    monthly_axis = monthly_df.copy()
    monthly_axis["month_start"] = pd.to_datetime(monthly_axis["month_start"], errors="coerce", utc=True).dt.tz_localize(None)
    monthly_axis["month_end"] = pd.to_datetime(monthly_axis["month_end"], errors="coerce", utc=True).dt.tz_localize(None)
    if monthly_axis["month_start"].isna().any() or monthly_axis["month_end"].isna().any() or monthly_axis["month_start"].duplicated().any():
        raise ValueError("ITEM_CLASS_MONTHLY_AXIS_INVALID")
    sales["_month_start"] = sales["sale_date"].dt.tz_convert("UTC").dt.tz_localize(None).dt.to_period("M").dt.to_timestamp()
    month_values = set(sales["_month_start"])
    if not month_values.issubset(set(monthly_axis["month_start"])):
        raise ValueError("ITEM_CLASS_MONTHLY_AXIS_INCOMPLETE")
    monthly_rows = []
    for _, row in monthly_axis.iterrows():
        frame = sales[sales["_month_start"] == row["month_start"]]
        monthly_rows.append({
            "month": str(row.get("month", row["month_start"].strftime("%Y-%m"))),
            "month_start": row["month_start"].strftime("%Y-%m-%d"),
            "month_end": row["month_end"].strftime("%Y-%m-%d"),
            "total_sales": int(len(frame)),
            "counts": counts_for(frame),
        })

    return {
        "contract_version": ITEM_CLASS_CONTRACT_VERSION,
        "class_source": ITEM_CLASS_SOURCE,
        "item_class_snapshot_identity": snapshot_identity_value,
        "classes": classes,
        "coverage": {
            "total_sales": int(len(sales)),
            "classified_sales": classified,
            "unclassified_sales": unclassified,
            "mapping_coverage_percent": round((classified / len(sales) * 100) if len(sales) else 100.0, 6),
        },
        "daily": daily_rows,
        "monthly": monthly_rows,
    }


def validate_sales_by_item_class_payload(payload: Any, *, expected_source_latest_date: str = "", expected_snapshot_identity: dict[str, Any] | None = None) -> bool:
    try:
        if not isinstance(payload, dict) or payload.get("contract_version") != ITEM_CLASS_CONTRACT_VERSION:
            return False
        if payload.get("class_source") != ITEM_CLASS_SOURCE:
            return False
        identity = payload.get("item_class_snapshot_identity")
        if not isinstance(identity, dict) or not re.fullmatch(r"[0-9a-f]{64}", str(identity.get("sha256", ""))):
            return False
        if expected_snapshot_identity is not None and identity.get("sha256") != expected_snapshot_identity.get("sha256"):
            return False
        classes = payload.get("classes")
        if not isinstance(classes, list) or not classes:
            return False
        ids = [entry.get("id") for entry in classes]
        orders = [entry.get("order") for entry in classes]
        if any(not isinstance(entry, dict) for entry in classes) or len(ids) != len(set(ids)) or orders != list(range(len(classes))):
            return False
        if any(not isinstance(entry.get("name"), str) or not entry["name"] or not isinstance(entry.get("color"), str) or not re.fullmatch(r"#[0-9A-Fa-f]{6}", entry["color"]) for entry in classes):
            return False
        coverage = payload.get("coverage")
        if not isinstance(coverage, dict):
            return False
        total = coverage.get("total_sales")
        classified = coverage.get("classified_sales")
        unclassified = coverage.get("unclassified_sales")
        percent = coverage.get("mapping_coverage_percent")
        if any(not isinstance(value, int) or isinstance(value, bool) or value < 0 for value in (total, classified, unclassified)):
            return False
        if classified + unclassified != total or not isinstance(percent, (int, float)) or not math.isfinite(float(percent)):
            return False
        if abs(float(percent) - ((classified / total * 100) if total else 100.0)) > 0.001:
            return False

        def check_rows(rows: Any, monthly: bool) -> tuple[int, dict[str, int]]:
            if not isinstance(rows, list):
                raise ValueError
            previous = None
            aggregate = {class_id: 0 for class_id in ids}
            row_total = 0
            for row in rows:
                if not isinstance(row, dict):
                    raise ValueError
                key = "month_start" if monthly else "date"
                if not isinstance(row.get(key), str) or (not isinstance(row.get("month"), str) if monthly else False):
                    raise ValueError
                current = row[key]
                if previous is not None and current <= previous:
                    raise ValueError
                previous = current
                counts = row.get("counts")
                if not isinstance(counts, list) or len(counts) != len(classes):
                    raise ValueError
                count_ids = [entry.get("class_id") for entry in counts if isinstance(entry, dict)]
                if count_ids != ids:
                    raise ValueError
                values = []
                for entry in counts:
                    value = entry.get("sales")
                    if not isinstance(value, int) or isinstance(value, bool) or value < 0:
                        raise ValueError
                    values.append(value)
                    aggregate[entry["class_id"]] += value
                if not isinstance(row.get("total_sales"), int) or row["total_sales"] < 0 or sum(values) != row["total_sales"]:
                    raise ValueError
                row_total += row["total_sales"]
            return row_total, aggregate

        daily_total, daily_aggregate = check_rows(payload.get("daily"), False)
        monthly_total, monthly_aggregate = check_rows(payload.get("monthly"), True)
        if daily_total != total or monthly_total != total or daily_aggregate != monthly_aggregate:
            return False
        if daily_aggregate.get("unclassified", 0) != unclassified:
            return False
        if expected_source_latest_date:
            daily_dates = payload.get("daily", [])
            if daily_dates and daily_dates[-1].get("date") != expected_source_latest_date:
                return False
        return True
    except (AttributeError, KeyError, TypeError, ValueError):
        return False


def payload_to_frames(payload: dict[str, Any]) -> tuple[pd.DataFrame, pd.DataFrame, list[dict[str, Any]]]:
    if not validate_sales_by_item_class_payload(payload):
        raise ValueError("ITEM_CLASS_PAYLOAD_INVALID")
    classes = payload["classes"]
    ids = [entry["id"] for entry in classes]

    def frame(rows: list[dict[str, Any]], monthly: bool) -> pd.DataFrame:
        records = []
        for row in rows:
            record = {"total_sales": row["total_sales"]}
            record["month" if monthly else "date"] = row["month" if monthly else "date"]
            if monthly:
                record["month_start"] = row["month_start"]
                record["month_end"] = row["month_end"]
            record.update({entry["class_id"]: entry["sales"] for entry in row["counts"]})
            records.append(record)
        result = pd.DataFrame(records)
        if monthly:
            result["month_start"] = pd.to_datetime(result["month_start"], utc=True)
            result["month_end"] = pd.to_datetime(result["month_end"], utc=True)
        else:
            result["date"] = pd.to_datetime(result["date"], utc=True)
        for class_id in ids:
            if class_id not in result:
                result[class_id] = 0
        return result

    return frame(payload["daily"], False), frame(payload["monthly"], True), classes
