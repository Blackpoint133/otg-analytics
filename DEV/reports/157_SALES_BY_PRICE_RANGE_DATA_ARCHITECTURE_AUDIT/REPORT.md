# Report 157 — Sales by Price Range Data + Architecture Audit

REPORT_SEQUENCE=157
RESULT=SUCCESS

MAIN_BASELINE=9edb927dc25432effda8fe8ae353993d55297f4d
DEVELOP_BASELINE=daa5a57b6c835b6e04ea6880c78c9f8689534929

## Current Market Architecture

AUTHORITATIVE_SALES_SOURCE=streamlit_opensea_sales/data_opensea_sales/sales_enriched/*.csv via market_data_access.load_enriched_market_sales
AUTHORITATIVE_SOURCE_SHAPE=1942 item CSV files; 22286 transaction rows; enriched/raw row-count parity
SALE_TIMESTAMP_FIELD=sale_date
SALE_TIMESTAMP_CONTRACT=Parse with pandas UTC coercion, normalize to UTC calendar day; existing snapshot validation compares raw and prepared latest UTC dates
GUN_PRICE_FIELD=price_gun
TOKEN_FIELD=type_token (frontend item loader normalizes this to type where needed)
USD_PRICE_FIELD_OR_CONTRACT=price_usd_at_sale, paired with gun_usd_price_at_sale; enrichment provenance is price_source, price_timestamp, price_resolution, usd_price_confidence, usd_backfilled
USD_ENRICHMENT_COVERAGE=22286/22286 rows have finite price_usd_at_sale and gun_usd_price_at_sale; usd_price_confidence is medium-high for all rows; source mix is coinmarketcap_csv_manual=17379 and dexscreener_postgres_token_price=4907
CURRENT_MARKET_OVERVIEW_SOURCE=market_overview_enriched/daily_market_metrics.csv and monthly_market_metrics.csv, validated against the same sales_enriched snapshot
CURRENT_PERIOD_FILTER=ui.market_overview._get_market_period_bounds and _filter_market_chart_data; ALL, 12m, 6m, 3m; latest prepared daily UTC date is the end anchor; raw fallback sales use a half-open end-exclusive next-day bound
CURRENT_DAILY_PATTERN=Prepared daily_market_metrics has date plus transactions_count and market aggregates; current axis contains active dates only (420 rows across 430 calendar days)
CURRENT_MONTHLY_PATTERN=Prepared monthly_market_metrics has month, month_start, month_end plus market aggregates; current snapshot contains 15 chronological month rows
CURRENT_CHART_HELPERS=charts_market.build_daily_liquidity_chart; build_daily_volume_chart; build_monthly_liquidity_chart; build_monthly_volume_chart
CURRENT_CHART_RENDER_ORDER=Desktop 2x2: daily liquidity, daily volume, monthly liquidity, monthly volume; mobile sequentially in the same order
CURRENT_MARKET_LOADING=ui.market_overview.render_market_overview loads manifest/cache_buster, daily metrics, monthly metrics, summary, optional prepared period/expansion summaries, and transaction-level enriched sales only when the prepared KPI summary cannot satisfy the selected period
CURRENT_CACHE_CONTRACT=market_data_access loaders use @st.cache_data(ttl=3600); manifest created_at_utc is the cache buster; derived artifact versions use mtime_ns:size

## Read-only Dataset Audit

TOTAL_VALID_SALES=22286
TOTAL_INVALID_OR_MISSING_PRICE_SALES=0
RAW_SALE_ROWS=22286
DAILY_PREPARED_TRANSACTION_TOTAL=22286
MONTHLY_PREPARED_TRANSACTION_TOTAL=22286
RAW_GUN_TOTAL=30967203.3524
HISTORICAL_USD_TOTAL=561267.512908669
SALE_DATE_RANGE_UTC=2025-07-15 through 2026-09-17

PRICE_DISTRIBUTION_STATS=
canonical_value=price_usd_at_sale
MIN=0.000000000000000229775173567
P01=0.0560203945448
P05=0.124792
P10=0.2816
P25=0.575092425779
MEDIAN=1.076
P75=5.83866655916
P90=36.9557304435
P95=83.7062673734
P99=372.094615155
MAX=3633.61525388
zero_price_sales=0
negative_price_sales=0
nonfinite_or_missing_price_sales=0

RAW_GUN_DISTRIBUTION_REFERENCE=
min=0.00000000000001
p01=5
p05=13
p10=16
p25=24
median=90
p75=449
p90=2000
p95=4200
p99=18375.25
max=320000

CANDIDATE_BUCKET_MODEL_A=USD: <$5=16380; $5-$9.99=1543; $10-$24.99=1557; $25-$49.99=907; $50-$99.99=1025; $100+=874
CANDIDATE_BUCKET_MODEL_B=USD: <$10=17923; $10-$24.99=1557; $25-$49.99=907; $50-$99.99=1025; $100-$249.99=540; $250+=334
CANDIDATE_BUCKET_MODEL_C=USD: <$0.50=4850; $0.50-$0.99=5931; $1-$4.99=5599; $5-$9.99=1543; $10-$24.99=1557; $25-$99.99=1932; $100+=874

## Canonical Price Semantics

PRICE_RANGE_CANONICAL_VALUE_RECOMMENDATION=HISTORICAL_USD_AT_SALE
PRICE_RANGE_CANONICAL_REASONING=Use the stored price_usd_at_sale enrichment because public monetary boundaries are understandable, every current tracked sale has a finite historical USD value, and membership remains fixed when the current GUN price changes. Raw price_gun is immutable transaction value but produces less user-readable fiat ranges; current_gun_price must never be used for historical bucket membership.
PRICE_RANGE_REPRODUCIBILITY_GATE=PASS_FOR_CURRENT_SNAPSHOT
PRICE_RANGE_REPRODUCIBILITY_DETAIL=Classification uses only stored price_usd_at_sale and fixed boundaries. It is independent of the UI USD/GUN display toggle and current price.csv. Future refreshes may correct historical enrichment, but a rerun against the same snapshot is deterministic.
MISSING_HISTORICAL_USD_POLICY=Do not fall back to current_gun_price or invent a USD estimate. Exclude a sale from categorized range series only when its canonical historical USD value is missing/nonfinite, expose coverage diagnostics, and preserve the sale in all raw/other analytics data.

## Fixed V1 Bucket Contract

PRICE_BUCKET_MODEL_RECOMMENDATION=Seven fixed USD-at-sale buckets, distribution-informed but not quantile-defined; current counts are 4850, 5931, 5599, 1543, 1557, 1932, and 874 respectively.
BUCKET_BOUNDARY_CONTRACT=Mutually exclusive half-open intervals in ascending order: B0 $0.00 <= x < $0.50; B1 $0.50 <= x < $1.00; B2 $1.00 <= x < $5.00; B3 $5.00 <= x < $10.00; B4 $10.00 <= x < $25.00; B5 $25.00 <= x < $100.00; B6 $100.00 <= x. Labels are display abbreviations for these exact boundaries.
BUCKET_LABELS=<$0.50 | $0.50-$0.99 | $1-$4.99 | $5-$9.99 | $10-$24.99 | $25-$99.99 | $100+
BUCKET_ORDER=Low to high; use the same order for classification, legend, stack order, tooltip rows, and color mapping
BUCKET_EXHAUSTIVENESS=Every finite non-negative canonical price maps to exactly one bucket; negative, missing, and nonfinite values are invalid for this chart rather than silently coerced

OUTLIER_POLICY_RECOMMENDATION=Retain all finite non-negative rows under the existing sale validity rules; do not clip, cap, or delete valid whales. Keep B6 open-ended at $100+. The snapshot contains 874 sales at $100+ and a maximum historical USD value of $3633.61525388 (320000 GUN). One extremely small positive sale at 1e-14 GUN is retained as existing data and falls into B0; it is a data-quality diagnostic candidate, not a reason to mutate the source. Zero-price sales=0, negative sales=0, and USD values above $1000=122.

## Daily Chart Contract

DAILY_PRICE_RANGE_CHART_CONTRACT=Render a Plotly stacked area chart whose y-axis is count of sold items/sales, never monetary volume. Classify each valid sale by historical USD-at-sale, normalize sale_date to UTC day, apply the existing Market period bounds, group by UTC day and bucket, and render one area series per fixed bucket.
DAILY_X_AXIS=UTC calendar days, chronological ascending; use a complete daily date range between the selected period bounds and fill missing dates/buckets with zero so gaps are explicit rather than silently removed
DAILY_Y_AXIS=Number of sold item-sale records; integer tick/hover formatting; no sum of price_gun or price_usd_at_sale
DAILY_STACK_ORDER=<$0.50 at the bottom through $100+ at the top
DAILY_TOOLTIP=UTC date, one count line per visible bucket or Plotly unified hover equivalent, plus total sales for the date; labels must say sales/items, not volume
DAILY_LEGEND=Fixed low-to-high bucket order; same names/colors on every rerun
DAILY_PERIOD_BEHAVIOR=Reuse market_time_range ALL/12m/6m/3m and the existing latest-UTC-date anchor; do not add the future DAILY/MONTHLY selector in this task
DAILY_ZERO_DAYS=Yes; zero-count dates are represented in the complete axis and contribute no filled area
DAILY_USD_TOGGLE=No effect on classification, bucket labels, counts, or boundaries; chart title/annotation should make USD-at-sale semantics explicit

## Monthly Chart Contract

MONTHLY_PRICE_RANGE_CHART_CONTRACT=Render a Plotly stacked bar chart with the same seven historical-USD buckets, same classification function, same bucket order, and y-axis meaning as Daily. Aggregate sales by UTC calendar month and bucket.
MONTHLY_X_AXIS=UTC month boundaries represented by chronological YYYY-MM labels; use every month between selected period bounds, including zero-count months where the period axis requires them
MONTHLY_Y_AXIS=Number of sold item-sale records; integer counts, never traded monetary value
MONTHLY_STACK_ORDER=Identical to Daily: <$0.50 through $100+
MONTHLY_TOOLTIP=Month label, bucket label, and count of sold items; optionally include total sales for the month; no current GUN price estimate
MONTHLY_LEGEND=Same fixed bucket order and color mapping as Daily
MONTHLY_PERIOD_BEHAVIOR=Reuse existing period overlap semantics and latest-UTC-date anchor, then trim/reindex to chronological month starts; do not introduce VIEW controls yet
MONTHLY_SORTING=Chronological by month_start, never lexical display order

## Currency Toggle and Color Contracts

USD_GUN_TOGGLE_BEHAVIOR_RECOMMENDATION=OPTION_1_ALWAYS_HISTORICAL_USD_BUCKETS
USD_GUN_TOGGLE_REASONING=The chart is a count distribution with monetary bucket names. Switching the existing Market USD Price control must not reclassify sales or relabel USD boundaries as GUN. Keep the chart labeled USD AT SALE and optionally show a compact explanatory note; do not multiply by current_gun_price.

PRICE_RANGE_COLOR_CONTRACT=Use one deterministic seven-color OTG palette keyed by stable bucket id, shared by Daily and Monthly. Recommended low-to-high mapping: B0 #5B616A, B1 #808894, B2 #AEB5BD, B3 #D9DDE2, B4 #FF7A92, B5 #FF3D66, B6 #FF003A. Use the same mapping for area fills/lines, stacked bars, legend, and tooltip; test adjacent contrast on the black theme; never generate colors from row order or rerun randomness.

## Aggregation and Future View Architecture

AGGREGATION_ARCHITECTURE_RECOMMENDATION=Add a pure, testable price-range aggregation helper alongside the existing Market data layer. Load sales_enriched once through the existing @st.cache_data pattern keyed by manifest cache_buster; parse UTC timestamps and historical USD once; classify with a versioned fixed bucket definition; produce a small payload containing daily and monthly DataFrames already filtered/reindexed for the selected period. Keep Plotly construction in charts_market.py and keep ui/market_overview.py responsible only for loading/filtering/rendering. Do not recompute the full history per trace or per rerun.
AGGREGATION_COST_ESTIMATE=Current snapshot is 22286 rows; seven classifications and two group-bys are small. A full daily axis is 430 calendar days and the current monthly axis is 15 rows, so the resulting series are at most 3010 daily cells plus 105 monthly cells before period trimming.
AGGREGATION_CACHE_KEY=manifest created_at_utc/cache_buster plus a bucket-contract version; current_gun_price and show_usd must not invalidate or alter price-range classification
VIEW_SWITCH_COMPATIBILITY_GATE=PASS_BY_DESIGN_RECOMMENDATION
VIEW_SWITCH_COMPATIBILITY_DETAIL=Return {daily: aggregated daily series, monthly: aggregated monthly series} from one helper and expose separate build_daily_price_range_chart/build_monthly_price_range_chart functions. Task 05 can select one already-prepared frame without changing bucket definitions, period semantics, or chart builders.

## Task 158 Implementation Plan

TASK_158_IMPLEMENTATION_PLAN=
1. Add a pure bucket-definition/classification module with exact half-open boundaries, stable ids/labels, deterministic colors, finite/non-negative validation, and tests for every boundary.
2. Add a cached Market aggregation function using sales_enriched, manifest cache_buster, UTC day/month normalization, existing period bounds, complete zero-filled axes, and coverage diagnostics for missing historical USD.
3. Add Daily stacked-area and Monthly stacked-bar Plotly builders in charts_market.py using count y-values, identical series order/colors, accessible hover text, and stable legends.
4. Integrate both charts into the existing Market render order without changing current liquidity/volume calculations, sidebar period controls, or the future VIEW selector contract.
5. Add focused tests for source columns, bucket exhaustiveness, outliers, period filtering, UTC boundaries, zero dates/months, count-vs-volume semantics, USD toggle invariance, deterministic colors, and both Plotly trace types/stack modes.
6. Run the focused Market suite, then the repository suite once; deploy only to DEV after implementation approval. No database migration is required for the derived chart in the recommended design.

NO_RUNTIME_MUTATION_GATE=PASS
NO_DB_MUTATION_GATE=PASS
ECOSYSTEM_UNTOUCHED_GATE=PASS
LOGO_2_UNTOUCHED=YES_UNTRACKED

RESULT=SUCCESS
