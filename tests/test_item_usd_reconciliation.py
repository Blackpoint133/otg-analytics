import io
import logging
import sys
import tempfile
import unittest
from pathlib import Path

import pandas as pd


PROJECT_ROOT = Path(__file__).resolve().parents[3]
APP_DIR = PROJECT_ROOT / "data_streamlit" / "opensea_sales" / "streamlit_opensea_sales"
if str(APP_DIR) not in sys.path:
    sys.path.insert(0, str(APP_DIR))

import charts  # noqa: E402
import data_access  # noqa: E402


ENRICHMENT_COLUMNS = data_access.ENRICHMENT_COLUMNS


def make_original(rows=3, with_primary=True):
    data = {
        "id": list(range(1, rows + 1)),
        "sale_date": pd.date_range("2026-01-01", periods=rows, freq="D").strftime("%Y-%m-%d %H:%M:%S"),
        "parsed_date": pd.date_range("2026-01-01", periods=rows, freq="D").strftime("%Y-%m-%d %H:%M:%S"),
        "name": ["Item"] * rows,
        "token_id": [str(1000 + i) for i in range(rows)],
        "price_gun": [100.0 + i for i in range(rows)],
        "type_token": ["GUN"] * rows,
        "rarity": ["Epic"] * rows,
        "seller": [f"seller_{i}" for i in range(rows)],
        "buyer": [f"buyer_{i}" for i in range(rows)],
        "transaction_hash": [f"0xhash{i}" for i in range(rows)],
        "item_url": [f"https://example.test/{i}" for i in range(rows)],
        "image_url": [f"https://example.test/{i}.png" for i in range(rows)],
        "type": ["GUN"] * rows,
    }
    df = pd.DataFrame(data)
    if not with_primary:
        df["transaction_hash"] = ""
        df["token_id"] = ""
    return df


def make_enriched(original, rows=None):
    enriched = original.copy().iloc[: rows if rows is not None else len(original)].copy()
    enriched["gun_usd_price_at_sale"] = [0.03 + (i * 0.001) for i in range(len(enriched))]
    enriched["price_usd_at_sale"] = enriched["price_gun"] * enriched["gun_usd_price_at_sale"]
    enriched["price_source"] = "test_price"
    enriched["price_timestamp"] = "2026-01-01 00:00:00"
    enriched["price_resolution"] = "daily"
    enriched["usd_price_confidence"] = "high"
    enriched["usd_backfilled"] = True
    return enriched


class ItemUsdReconciliationTests(unittest.TestCase):
    def test_safe_subset_merge_preserves_original_rows_and_marks_missing(self):
        original = make_original(rows=101)
        enriched = make_enriched(original, rows=100)

        merged, status = data_access._reconcile_original_and_enriched(original, enriched)

        self.assertEqual(status, "partial_enriched_merge:primary")
        self.assertEqual(len(merged), 101)
        self.assertEqual(list(merged["id"]), list(original["id"]))
        self.assertEqual(int(merged["price_usd_at_sale"].notna().sum()), 100)
        self.assertTrue(pd.isna(merged.iloc[-1]["price_usd_at_sale"]))
        self.assertTrue(pd.isna(merged.iloc[-1]["gun_usd_price_at_sale"]))
        self.assertEqual(merged.iloc[-1]["usd_price_confidence"], "missing")
        self.assertFalse(bool(merged.iloc[-1]["usd_backfilled"]))

    def test_production_anarchist_jetpack_regression(self):
        base = APP_DIR / "data_opensea_sales"
        original = pd.read_csv(base / "sales" / "anarchist_jetpack_epic.csv")
        original["type"] = original["type_token"]
        enriched = pd.read_csv(base / "sales_enriched" / "anarchist_jetpack_epic.csv")

        merged, status = data_access._reconcile_original_and_enriched(original, enriched)

        self.assertEqual(status, "partial_enriched_merge:primary")
        self.assertEqual(len(merged), len(original))
        self.assertEqual(int(merged["price_usd_at_sale"].notna().sum()), len(enriched))
        if len(original) != len(enriched):
            self.assertEqual(len(original), 101)
            self.assertEqual(len(enriched), 100)

    def test_equal_row_dataset_reconciles_to_same_enrichment_values(self):
        original = make_original(rows=3)
        enriched = make_enriched(original)

        merged, status = data_access._reconcile_original_and_enriched(original, enriched)

        self.assertEqual(status, "partial_enriched_merge:primary")
        pd.testing.assert_series_equal(merged["price_usd_at_sale"], enriched["price_usd_at_sale"], check_names=False)

    def test_primary_key_matching_ignores_row_position(self):
        original = make_original(rows=3)
        enriched = make_enriched(original).iloc[[2, 0]].copy()

        merged, status = data_access._reconcile_original_and_enriched(original, enriched)

        self.assertEqual(status, "partial_enriched_merge:primary")
        self.assertTrue(pd.isna(merged.iloc[1]["price_usd_at_sale"]))
        self.assertEqual(merged.iloc[0]["price_usd_at_sale"], enriched.iloc[1]["price_usd_at_sale"])
        self.assertEqual(merged.iloc[2]["price_usd_at_sale"], enriched.iloc[0]["price_usd_at_sale"])

    def test_fallback_key_matching_when_primary_unavailable(self):
        original = make_original(rows=3, with_primary=False)
        enriched = make_enriched(original, rows=2)

        merged, status = data_access._reconcile_original_and_enriched(original, enriched)

        self.assertEqual(status, "partial_enriched_merge:fallback")
        self.assertEqual(len(merged), 3)
        self.assertEqual(int(merged["price_usd_at_sale"].notna().sum()), 2)

    def test_duplicate_key_in_original_rejected(self):
        original = make_original(rows=3)
        original.loc[1, ["transaction_hash", "token_id"]] = original.loc[0, ["transaction_hash", "token_id"]]
        enriched = make_enriched(original.iloc[:2].copy())

        merged, status = data_access._reconcile_original_and_enriched(original, enriched)

        self.assertIsNone(merged)
        self.assertEqual(status, "original_duplicate_key")

    def test_duplicate_key_in_enriched_rejected(self):
        original = make_original(rows=3)
        enriched = make_enriched(original.iloc[:2].copy())
        enriched.loc[1, ["transaction_hash", "token_id"]] = enriched.loc[0, ["transaction_hash", "token_id"]]

        merged, status = data_access._reconcile_original_and_enriched(original, enriched)

        self.assertIsNone(merged)
        self.assertEqual(status, "enriched_duplicate_key")

    def test_enriched_unknown_key_rejected(self):
        original = make_original(rows=3)
        enriched = make_enriched(original.iloc[:2].copy())
        enriched.loc[1, "token_id"] = "unknown"

        merged, status = data_access._reconcile_original_and_enriched(original, enriched)

        self.assertIsNone(merged)
        self.assertEqual(status, "enriched_unknown_keys")

    def test_missing_required_enriched_columns_returns_original_through_loader(self):
        original = make_original(rows=2)
        enriched = make_enriched(original).drop(columns=["price_usd_at_sale"])
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            sales_dir = root / "sales"
            enriched_dir = root / "sales_enriched"
            sales_dir.mkdir()
            enriched_dir.mkdir()
            original_path = sales_dir / "item.csv"
            enriched_path = enriched_dir / "item.csv"
            original.to_csv(original_path, index=False)
            enriched.to_csv(enriched_path, index=False)

            result = data_access.get_item_data_from_record({
                "file_path": str(original_path),
                "file_mtime": original_path.stat().st_mtime,
            })

        self.assertNotIn("price_usd_at_sale", result.columns)
        self.assertEqual(len(result), 2)

    def test_core_original_columns_are_not_overwritten(self):
        original = make_original(rows=2)
        enriched = make_enriched(original, rows=1)
        enriched.loc[0, "price_gun"] = 999999
        enriched.loc[0, "seller"] = "changed"

        merged, _ = data_access._reconcile_original_and_enriched(original, enriched)

        self.assertEqual(merged.loc[0, "price_gun"], original.loc[0, "price_gun"])
        self.assertEqual(merged.loc[0, "seller"], original.loc[0, "seller"])

    def test_chart_gun_mode_uses_all_price_gun_points(self):
        df = make_enriched(make_original(rows=3))
        df.loc[2, "price_usd_at_sale"] = pd.NA
        df["sale_date"] = pd.to_datetime(df["sale_date"])
        df["formatted_date"] = df["sale_date"].dt.strftime("%Y-%m-%d %H:%M:%S")

        fig = charts.build_sales_chart(df, False, False, 0.002842)

        self.assertEqual(list(fig.data[0].y), [100.0, 101.0, 102.0])

    def test_chart_usd_mode_uses_historical_values_without_current_price_fill(self):
        df = make_enriched(make_original(rows=3))
        df.loc[2, "price_usd_at_sale"] = pd.NA
        df["sale_date"] = pd.to_datetime(df["sale_date"])
        df["formatted_date"] = df["sale_date"].dt.strftime("%Y-%m-%d %H:%M:%S")

        fig = charts.build_sales_chart(df, False, True, 0.002842)
        y_values = list(fig.data[0].y)

        self.assertEqual(y_values[:2], [3.0, 3.131])
        self.assertTrue(pd.isna(y_values[2]))

    def test_chart_axis_titles_and_tick_format_switch_with_currency(self):
        df = make_enriched(make_original(rows=3))
        df["sale_date"] = pd.to_datetime(df["sale_date"])
        df["formatted_date"] = df["sale_date"].dt.strftime("%Y-%m-%d %H:%M:%S")

        gun_fig = charts.build_sales_chart(df, False, False, 0.002842)
        usd_fig = charts.build_sales_chart(df, False, True, 0.002842)

        self.assertEqual(gun_fig.layout.yaxis.title.text, "GUN")
        self.assertEqual(usd_fig.layout.yaxis.title.text, "USD AT SALE")
        self.assertIsNone(gun_fig.layout.yaxis.tickprefix)
        self.assertEqual(usd_fig.layout.yaxis.tickprefix, "$")
        self.assertEqual(gun_fig.layout.yaxis.tickformat, "~s")
        self.assertEqual(usd_fig.layout.yaxis.tickformat, "~s")

    def test_chart_hover_primary_price_matches_selected_currency(self):
        df = make_enriched(make_original(rows=1))
        df["sale_date"] = pd.to_datetime(df["sale_date"])
        df["formatted_date"] = df["sale_date"].dt.strftime("%Y-%m-%d %H:%M:%S")

        gun_fig = charts.build_sales_chart(df, False, False, 0.002842)
        usd_fig = charts.build_sales_chart(df, False, True, 0.002842)

        self.assertTrue(str(gun_fig.data[0].customdata[0]).startswith("GUN paid: 100"))
        self.assertIn("USD at sale: $3.00", gun_fig.data[0].customdata[0])
        self.assertTrue(str(usd_fig.data[0].customdata[0]).startswith("USD at sale: $3.00"))
        self.assertIn("GUN paid: 100", usd_fig.data[0].customdata[0])
        self.assertIn("GUN/USD at sale: $0.03000000", usd_fig.data[0].customdata[0])

    def test_chart_token_type_traces_remain_distinct(self):
        df = make_enriched(make_original(rows=2))
        df.loc[1, "type"] = "WGUN"
        df["sale_date"] = pd.to_datetime(df["sale_date"])
        df["formatted_date"] = df["sale_date"].dt.strftime("%Y-%m-%d %H:%M:%S")

        fig = charts.build_sales_chart(df, False, True, 0.002842)

        self.assertEqual([trace.name for trace in fig.data], ["GUN", "WGUN"])
        self.assertIn("Token type: GUN", fig.data[0].customdata[0])
        self.assertIn("Token type: WGUN", fig.data[1].customdata[0])

    def test_mobile_chart_exposes_currency_with_annotation(self):
        df = make_enriched(make_original(rows=3))
        df["sale_date"] = pd.to_datetime(df["sale_date"])
        df["formatted_date"] = df["sale_date"].dt.strftime("%Y-%m-%d %H:%M:%S")

        gun_fig = charts.build_sales_chart(df, False, False, 0.002842, mobile_layout=True)
        usd_fig = charts.build_sales_chart(df, False, True, 0.002842, mobile_layout=True)

        self.assertEqual(gun_fig.layout.yaxis.title.text, "")
        self.assertEqual(usd_fig.layout.yaxis.title.text, "")
        self.assertEqual(gun_fig.layout.annotations[0].text, "PRICE - GUN")
        self.assertEqual(usd_fig.layout.annotations[0].text, "PRICE - USD AT SALE")

    def test_representative_production_items_keep_exact_y_arrays(self):
        base = APP_DIR / "data_opensea_sales"
        representative_files = [
            "anarchist_jetpack_epic.csv",
            "tacoma_common.csv",
            "kestrel_legacy_common.csv",
            "player_zero_shorts_epic.csv",
            "prankster_t_shirt_epic.csv",
        ]
        current_price = 0.003153

        for filename in representative_files:
            with self.subTest(filename=filename):
                df = pd.read_csv(base / "sales_enriched" / filename)
                df["sale_date"] = pd.to_datetime(df["sale_date"])
                df["formatted_date"] = df["sale_date"].dt.strftime("%Y-%m-%d %H:%M:%S")
                if "type" not in df.columns:
                    df["type"] = df["type_token"]

                gun_fig = charts.build_sales_chart(df, False, False, current_price)
                usd_fig = charts.build_sales_chart(df, False, True, current_price)

                for trace in gun_fig.data:
                    expected = df[df["type"] == trace.name]["price_gun"].tolist()
                    self.assertEqual(list(trace.y), expected)

                for trace in usd_fig.data:
                    trace_df = df[df["type"] == trace.name]
                    expected = pd.to_numeric(trace_df["price_usd_at_sale"], errors="coerce").tolist()
                    current_estimate = (trace_df["price_gun"] * current_price).tolist()
                    self.assertEqual(list(trace.y), expected)
                    self.assertNotEqual(list(trace.y), current_estimate)

    def test_anarchist_hashes_are_not_constant_current_price_multiplier(self):
        base = APP_DIR / "data_opensea_sales"
        original = pd.read_csv(base / "sales" / "anarchist_jetpack_epic.csv")
        original["type"] = original["type_token"]
        enriched = pd.read_csv(base / "sales_enriched" / "anarchist_jetpack_epic.csv")
        merged, _ = data_access._reconcile_original_and_enriched(original, enriched)

        gun = pd.to_numeric(merged["price_gun"], errors="coerce")
        usd = pd.to_numeric(merged["price_usd_at_sale"], errors="coerce")
        ratios = (usd / gun).dropna().round(10)

        self.assertGreater(ratios.nunique(), 1)

    def test_trend_line_works_in_both_modes(self):
        df = make_enriched(make_original(rows=3))
        df["sale_date"] = pd.to_datetime(df["sale_date"])
        df["formatted_date"] = df["sale_date"].dt.strftime("%Y-%m-%d %H:%M:%S")
        trend = pd.DataFrame({
            "start_date": ["2026-01-01"],
            "end_date": ["2026-01-03"],
            "trend_start_price_gun": [100.0],
            "trend_end_price_gun": [102.0],
            "trend_start_price_usd": [3.0],
            "trend_end_price_usd": [3.3],
        })

        gun_fig = charts.build_sales_chart(df, False, False, 0.002842, show_trend_line=True, trend_df=trend)
        usd_fig = charts.build_sales_chart(df, False, True, 0.002842, show_trend_line=True, trend_df=trend)

        self.assertEqual(gun_fig.data[-1].name, "Trend Line")
        self.assertEqual(usd_fig.data[-1].name, "Trend Line")
        self.assertEqual(list(gun_fig.data[-1].y), [100.0, 102.0])
        self.assertEqual(list(usd_fig.data[-1].y), [3.0, 3.3])

    def test_logging_contains_no_sensitive_row_values(self):
        original = make_original(rows=3)
        enriched = make_enriched(original, rows=2)
        stream = io.StringIO()
        handler = logging.StreamHandler(stream)
        logger = logging.getLogger("test_item_usd_reconciliation")
        logger.handlers = [handler]
        logger.setLevel(logging.INFO)

        merged, status = data_access._reconcile_original_and_enriched(original, enriched)
        logger.info("status=%s rows=%s", status, len(merged))

        log_text = stream.getvalue()
        self.assertNotIn("seller_0", log_text)
        self.assertNotIn("buyer_0", log_text)
        self.assertNotIn("0xhash0", log_text)


if __name__ == "__main__":
    unittest.main()
