# Report 159 — Sales by Item Class Data and Taxonomy Audit

REPORT_SEQUENCE=159
RESULT=SUCCESS

MAIN_BASELINE=9edb927dc25432effda8fe8ae353993d55297f4d
DEVELOP_BASELINE=437ff936a57bff6fdc63408c2d52321181fbfd34

ITEM_CLASS_SOURCE=streamlit_opensea_sales/data_opensea_sales/item_class_snapshot.json; source precedence public.item_metadata_current.class then public.common_data.class fallback
ITEM_CLASS_SNAPSHOT_ROWS=3361
DISTINCT_CLASS_COUNT=6

DATASET_NOTE=Current DEV sales_enriched files contain 22297 rows; the previously cited 22286 figure is stale and is not used as runtime logic.

CLASS_DISTRIBUTION=
Customization Item | ITEM_COUNT=885 | SALE_COUNT=10913 | SALE_SHARE_PERCENT=48.9438
Weapon | ITEM_COUNT=155 | SALE_COUNT=6019 | SALE_SHARE_PERCENT=26.9947
Body Part | ITEM_COUNT=25 | SALE_COUNT=2394 | SALE_SHARE_PERCENT=10.7369
Weapon Skin | ITEM_COUNT=1252 | SALE_COUNT=1036 | SALE_SHARE_PERCENT=4.6464
Weapon Attachment | ITEM_COUNT=861 | SALE_COUNT=1024 | SALE_SHARE_PERCENT=4.5925
Profile Customization | ITEM_COUNT=183 | SALE_COUNT=349 | SALE_SHARE_PERCENT=1.5652

TOTAL_SALES=22297
MAPPED_CLASS_SALES=21735
UNMAPPED_CLASS_SALES=562
CLASS_MAPPING_COVERAGE_PERCENT=97.4795
UNMAPPED_UNIQUE_ITEMS=34
UNMAPPED_ITEM_EXAMPLES=PHOSPHOR FURY; Ichnya; Yankee Doodle Damage Set; Mrs Crackhead Santa; Kochi Tinsel Terror; Il Silenzio

SALES_ITEM_FIELD=name
SNAPSHOT_ITEM_KEY_FIELD=items.<name>
SALES_TO_CLASS_JOIN_CONTRACT=Exact name first; then existing unique outer-whitespace alias semantics from item_class_data.class_for_name. No case folding or fuzzy matching.

CLASS_NORMALIZATION_REQUIRED=YES
CLASS_NORMALIZATION_RECOMMENDATION=Normalize only transaction item-name boundaries for joining: preserve exact match first, then trim leading/trailing whitespace only when the trimmed snapshot key maps unambiguously. Preserve all six stored class labels exactly; do not merge case, singular/plural, legacy, or UNKNOWN-like values.
NORMALIZED_MAPPING_RESULT=All 562 exact-name misses uniquely resolve to snapshot keys after outer-whitespace trimming; no case collisions, trim collisions, empty classes, or UNKNOWN-like class labels found. Expected residual unmapped sales after this safe rule=0.

CLASS_SERIES_STRATEGY=ALL_CLASSES_WITH_COMPACT_LEGEND
CLASS_SERIES_FEASIBILITY=Six current categorical series are manageable for Daily area, Monthly bars, desktop legend, and mobile compact legend. Do not collapse into OTHER. Keep a conditional UNCLASSIFIED series for future residuals.
CLASS_COLOR_MAP=Customization Item=#FF003A; Weapon=#FF8A65; Body Part=#67C77A; Weapon Skin=#8F78C6; Weapon Attachment=#5DA9E9; Profile Customization=#D8C3A5; UNCLASSIFIED=#6B6B73
CLASS_COLOR_RULE=Deterministic categorical mapping, stable in Daily and Monthly, with muted existing OTG-compatible colors and no random palette generation.

DAILY_ITEM_CLASS_CHART_CONTRACT=Prepared UTC daily rows; complete calendar-day axis with zero-filled class/date combinations; stacked area; Y=sales count; stable class order/color; unified hover uses one shared date, one prepared Total sales row, and one row per class; no repeated Total sales per trace.
MONTHLY_ITEM_CLASS_CHART_CONTRACT=Prepared chronological UTC calendar-month rows; zero-filled required months; stacked bars; Y=sales count; same class order/colors as Daily; unified hover uses one shared month, one prepared Total sales row, and one row per class.

ITEM_CLASS_DERIVED_SCHEMA_RECOMMENDATION=Extend market_overview_enriched/market_expansion_metrics.json with versioned sales_by_item_class. Use classes=[{id,name,order,color}], coverage={total_sales,mapped_class_sales,unmapped_class_sales,mapping_coverage_percent}, and daily/monthly rows containing date/month,total_sales, and ordered counts=[{class_id,sales}]. Include class_source, item_class_snapshot generated_at/hash, source_market_build_id, and source_latest_date. Validate exact class IDs/order, integer nonnegative counts, row totals, coverage, and snapshot/build identity. Frontend reads only this prepared artifact.
ITEM_CLASS_FRONTEND_RAW_SALES_SCAN_REQUIRED=NO

ITEM_CLASS_REFRESH_ORDER_GATE=FAIL
REFRESH_ORDER_RECOMMENDATION=The current production DerivedRefresh builds market expansion before MetadataRefresh refreshes item_class_snapshot; therefore taxonomy freshness is not guaranteed. For Task 160 or later, make item_class_snapshot refresh an explicit successful prerequisite immediately before the item-class-aware expansion build, preserve atomic snapshot publication, and carry snapshot identity into the expansion artifact. The same source snapshot must be used by the builder and validated by the reader; fail closed without replacing the last valid expansion on source-refresh failure.

MARKET_TOGGLE_INVARIANCE_CONTRACT=PASS_BY_DESIGN; USD PRICE, TOKEN PRICE, and UNIQUE WALLETS must not be inputs to class membership or sales counts. Existing ALL/12 MONTH/6 MONTH/3 MONTH bounds remain the sole period filter.
UNMAPPED_CLASS_POLICY=Include explicit UNCLASSIFIED in the prepared classes and chart whenever any sale remains unresolved after exact plus unique outer-trim resolution; never silently drop it. Current audit resolves all 562 apparent misses, so current normalized residual is zero.

TASK_160_IMPLEMENTATION_PLAN=Add a pure item-class contract/resolver using the existing snapshot and safe trim alias behavior; update the derived builder after the freshness-order correction; publish validated sales_by_item_class with snapshot/build identity and UTC daily/monthly zero-filled rows; extend the expansion reader fail-closed while preserving older artifacts; add Daily stacked-area and Monthly stacked-bar builders with deterministic categorical colors and the Task 158A single-total hover helper; integrate after the existing Market charts without changing Price Range; update the Market guide; add taxonomy/join/coverage/schema/reconciliation/toggle/hover tests; build the current DEV artifact; deploy only 8504; verify routes and hand off for owner visual validation.

NO_RUNTIME_MUTATION_GATE=PASS
NO_DB_MUTATION_GATE=PASS
PRICE_RANGE_UNTOUCHED_GATE=PASS
ECOSYSTEM_UNTOUCHED_GATE=PASS
LOGO_2_UNTOUCHED=YES_UNTRACKED
