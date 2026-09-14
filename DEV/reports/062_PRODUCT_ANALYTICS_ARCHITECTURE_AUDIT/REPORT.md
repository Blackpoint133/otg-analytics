# Report 062 — Product Analytics Architecture Audit

## 1. Executive Summary

**CURRENT ANALYTICS STATUS:** PARTIALLY OUTDATED.

The current first-party system has a sound privacy-conscious session writer,
V2 browser identity, append-only ITEM event stream, and read-only dashboard
queries. It no longer matches the expanded public product: public routing
supports TOP TRADERS (`trader`), while the session allowlist, database check,
dashboard labels, and campaign/post mode columns support only `item`,
`market`, and `top_items`.

**TOP TRADERS:** not correctly represented. `build_session_record()` silently
normalizes `trader` to `item`, so TOP TRADERS traffic is misclassified rather
than rejected. This is the highest-severity defect because it corrupts
surface-level interpretation while still appearing to be valid data.

## 2. Baseline Verification

- develop HEAD: `ee6ac9e4e70030b06f6daea748bfdc87fa642062` (matches required baseline)
- main HEAD: `dacee4c675419dea127ceb5e8a70e1a7ffc36a0` (matches required baseline)
- git status before audit: `?? img/gunz_scope/logo_2.png`

The untracked logo was pre-existing and was not touched. This audit changes
only this report.

## 3. Current Analytics Architecture

### Session collector and integration

`streamlit_opensea_sales/site_analytics.py` defines `VALID_MODES = {"item", "market", "top_items"}` and `record_current_session_once()` (symbols at lines 40 and 186). The application calls it in `app_opensea_sales.py` immediately after `mode_switch.render_mode_switch()` and before the analytics-mode branches (lines 133–141). `mode_switch.py` resolves both `trader` and `top_traders` to the internal mode `trader`; therefore the writer receives a value excluded by `VALID_MODES`.

`record_current_session_once()` stores a generated UUID in Streamlit session
state, uses attempted/recorded/failed state guards, writes once, and catches
writer failures so analytics cannot break the public UI. Its SQL uses
`ON CONFLICT (session_id) DO NOTHING`. It therefore produces at most one row
for a Streamlit session, not one row per mode visit or page/surface view.

`build_session_record()` (line 266) contains the decisive behavior:
`normalized_mode = mode if mode in VALID_MODES else "item"`. It retains an
`item_key` only for normalized `item`, and otherwise normalizes it to null.

### Identity, privacy, and write safety

`visitor_identity.py` implements the V2 random browser identifier and a
domain-separated HMAC hash. The session record stores hashes and normalized
metadata, not raw IP, browser ID, full user-agent, cookies, or full URLs.
`site_analytics.py` classifies bots and internal traffic and applies a global
write guard; database failures are swallowed/logged with sanitized context.
`visitor_dashboard_queries.py::_connect()` sets read-only PostgreSQL mode and
a statement timeout. Dashboard functions return aggregates or safe transient
drilldown fields rather than raw identity columns.

### Database tables

`sql/create_site_visit_sessions.sql` defines `public.site_visit_sessions`:
one row per attempted application session, with a unique `session_id`, V1/V2
identity hashes, first/last timestamps, mode, optional item key, path,
normalized referrer/source/UTM, device/browser/locale/timezone, and bot/internal
flags. Its `site_visit_sessions_mode_chk` allows only `item`, `market`, and
`top_items`.

`sql/create_site_item_events.sql` defines `public.site_item_events`: an
append-only event row keyed by identity `event_id`, with occurrence time,
parent session, optional V2 browser hash, item key, allowlisted event type,
`mode = 'item'`, and positive sequence number. The event types are
`initial_default`, `initial_explicit`, and `item_select`.

### Dashboard

`visitor_dashboard_queries.py::load_dashboard_data()` aggregates sessions,
V2 profiles, modes, acquisition, posts, item interest, and item activity.
`visitor_dashboard.py` displays these as Sessions, Unique Visitors, New vs
Returning, Mode Usage, Acquisition Sources, Campaign/Post Performance, Post
Performance, Item Interest, Item Activity, and Visitor Drilldown.

## 4. Current Public Product Surface

Current source routing exposes `item`, `market`, `top_items`, `trader` (also
the `top_traders` URL alias), `feedback`, `roadmap`, and the protected
`internal_analytics` route. The four analytics surfaces have substantial
controls: ITEM item/wallet/search/view/toggle controls; MARKET period and
metric toggles; TOP ITEMS filters/sort/period; and TOP TRADERS filter/sort/
profile/table controls.

Classification:

| Surface | Session/traffic analytics | Product event analytics | Classification |
|---|---|---|---|
| ITEM | Should | Yes, specialized ITEM events | Core product surface |
| MARKET | Should | Meaningful period/toggle changes | Core product surface |
| TOP ITEMS | Should | Meaningful filter/sort/period changes | Core product surface |
| TOP TRADERS | Should | Meaningful trader filter/sort changes | Core product surface; currently defective |
| FEEDBACK | Should for acquisition/traffic context | Optional for submission outcome, not message text | Public utility surface |
| ROADMAP | Optional traffic | Optional aggregate CTA/open event | Product decision required |
| GUIDE | Optional traffic | Optional if guide usage is a product question | Avoid cosmetic telemetry |
| LOG IN | No current enabled interaction | No | Disabled/coming-soon control |
| internal_analytics | No public analytics | No | Internal dashboard, exclude from public traffic |

## 5. Mode Taxonomy Audit

| Public surface | Public exists | Session accepts | DB accepts | Dashboard labels | Campaign/Post columns | Drilldown | Verdict |
|---|---:|---:|---:|---:|---:|---:|---|
| item | Yes | Yes | Yes | Yes | Yes | Yes | Correctly represented, subject to one-row/session limitation |
| market | Yes | Yes | Yes | Yes | Yes | Yes | Correctly represented, subject to one-row/session limitation |
| top_items | Yes | Yes | Yes | Yes | Yes | Yes | Correctly represented, subject to one-row/session limitation |
| trader | Yes (`trader`/`top_traders`) | No; falls through to `item` | No | No | No | Fallback raw `item` label | Misclassified as item by Python before DB; DB would reject literal trader |
| feedback | Yes, early-routed | Not recorded by the analytics call | N/A | N/A | N/A | N/A | Not tracked; product decision required |
| roadmap | Yes, early-routed/public redirect | Not recorded by analytics call | N/A | N/A | N/A | N/A | Not tracked |
| internal_analytics | Yes, protected | Not recorded by analytics call | N/A | N/A | N/A | N/A | Correctly excluded from public analytics |

## 6. TOP TRADERS Root-Cause Analysis

Exact chain:

1. `mode_switch.py` normalizes `top_traders` to `trader` and accepts it in
   its UI mode set.
2. `app_opensea_sales.py` calls `render_mode_switch()`, then passes
   `current_mode` to `record_current_session_once()` before entering the
   `trader` branch.
3. `site_analytics.py::build_session_record()` tests the mode against
   `VALID_MODES`; `trader` fails and becomes `item`.
4. The same function drops the item context unless the normalized mode is
   `item`, so a trader-first session is generally an item-mode row with a
   null item key.
5. `create_site_visit_sessions.sql` independently constrains mode to the
   three legacy values.
6. `visitor_dashboard.py::MODE_LABELS` contains only the same three keys,
   and `load_dashboard_data()` groups raw mode values and hard-codes only
   `item`, `market`, and `top_items` columns for post breakdowns.
7. Visitor timeline displays the stored mode through that same three-key
   label map.
8. Existing `tests/test_site_analytics.py::test_mode_values_are_whitelisted`
   explicitly preserves invalid-to-item fallback; dashboard tests assert the
   three-key label set. These are obsolete contracts for the expanded product.

Thus TOP TRADERS is not silently ignored at the application surface and is
not rejected in normal operation; it is silently **misclassified as ITEM**.
If the writer were changed only to pass literal `trader`, the current DB
constraint would reject it, so schema and writer rollout must be coordinated.

## 7. Metric Integrity Assessment

| Metric | Current status | Trader impact | Historical reliability | Explanation |
|---|---|---|---|---|
| Total Sessions | CORRECT for rows written | Unchanged total, wrong surface attribution | Reliable as session-row count | Trader rows are still inserted as item rows |
| Unique Visitors | CORRECT overall | No direct impact | Reliable overall, not surface-specific | Hash aggregation is mode-independent |
| New / Returning | CORRECT overall | No direct impact | Reliable under current one-row/session semantics | Profile counts do not depend on mode |
| Latest Visit | CORRECT overall | No direct impact | Reliable for stored rows | Timestamp is persisted |
| Traffic Over Time | CORRECT overall | No direct impact | Reliable overall | Groups all human/non-internal rows |
| Mode Usage | MISCLASSIFIED | Trader counted as Item; Trader absent | Not reliable for trader-era surface usage | Groups stored legacy mode |
| ITEM session counts | OVERCOUNTED / MISCLASSIFIED | Trader-first sessions enter Item, often without item key | Not reliable before boundary | `trader` fallback is `item` |
| Item Interest | OVERCOUNTED for missing-context diagnostic; item-key rows unaffected | Trader-first null-item rows inflate missing context | Partial only | item-interest filters `s.mode='item'`; null item count catches fallback rows |
| Item Activity | CORRECT for persisted ITEM events | No trader event is written | Reliable for stored item events | `site_item_events` is explicitly item-only and joins item sessions |
| Item-missing-context diagnostics | OVERCOUNTED / MISCLASSIFIED | Trader-first rows resemble item sessions missing context | Not repairable reliably | Null item + mode item is ambiguous |
| Acquisition sources | CORRECT overall; MISCLASSIFIED by mode if segmented | Source totals retained, trader source attribution absent | Overall reliable, surface split unreliable | Source fields are stored independently |
| Campaign/Post totals | CORRECT overall; MISCLASSIFIED mode columns | Trader rows land in item column | Overall partial; per-mode unreliable | Post query hard-codes item/market/top_items columns |
| Visitor drilldown | MISCLASSIFIED mode | Timeline shows Item Analytics/raw item fallback | Visitor identity/timestamps reliable; surface history not | Timeline selects stored mode and maps only legacy labels |
| Item selections | CORRECT for recorded ITEM events | No trader selection event exists | Reliable for event rows | Separate allowlisted item event stream |

## 8. Product Feature Coverage Matrix

| Interaction | Current tracking | Assessment |
|---|---|---|
| Open ITEM / initial context | session row; ITEM initial event path | Partially tracked; first surface only |
| Explicit ITEM selection | `site_item_events` `item_select` | Accurately tracked |
| ITEM live search use | None | Not tracked; appropriate unless product needs aggregate search usage |
| ITEM wallet apply/clear | None | Not tracked; future `filter_apply/clear` categorical events are optional |
| ITEM CHART/TABLE switch | None | Not tracked |
| ITEM USD Price / Trend Line | None | Not tracked; instrument only if decisions require it |
| MARKET open | session row | Partially tracked; first surface only |
| MARKET period/range and metric toggles | None | Not tracked |
| TOP ITEMS open | session row | Partially tracked; first surface only |
| TOP ITEMS sort/period/class/USD controls | None | Not tracked |
| TOP TRADERS open | session row misclassified as item | Misclassified |
| TOP TRADERS filter apply/clear | None | Not tracked |
| TOP TRADERS EARNED/INVESTED/SOLD/TRADES sort | None | Not tracked |
| Profile/card interactions | None | Not tracked; likely optional and should avoid telemetry by default |
| Analytics-mode navigation | No pageview/event; session is one-time | Partially/inferred only |
| FEEDBACK | Early route; feedback storage is separate from visitor analytics | Separate functional record, not traffic analytics |
| ROADMAP / GUIDE | No visitor event | Optional product decision |
| LOG IN | Disabled | Should not be tracked |
| UTM/referrer acquisition | Normalized into session row | Accurately tracked for recorded sessions |

## 9. Session Semantics Audit

`record_current_session_once()` is session analytics plus an initial surface
snapshot, not a pageview table and not a complete surface-usage table. The
attempted/recorded state keys and unique `session_id` mean one row per
Streamlit session, with the first successful mode written. A later navigation
within that same Streamlit session is invisible to this table. Consequently,
Mode Usage cannot be interpreted as true page/surface usage; it represents
the first mode observed per Streamlit session. Acquisition and session
identity are partially separated from product interaction: acquisition is on
the session row, while only ITEM selection has a specialized append-only
event stream.

## 10. Privacy and Data-Minimization Audit

The architecture is privacy-conscious: no raw IP is persisted, the legacy
visitor hash is HMAC-derived, V2 browser identity is random and
domain-separated before hashing, raw browser IDs are not SQL parameters,
user-agent is reduced to device/browser classifications, referrer is reduced
to host/source, UTM fields are bounded/normalized, item keys are sanitized,
and bot/internal flags are persisted for filtering. Dashboard connections
are read-only and drilldown excludes raw identity columns; transient profile
keys remain server-side and UI aliases are non-hash-derived.

Future product events MUST NOT store full wallet addresses, raw browser IDs,
raw IP, raw user-agent, raw item/trader search text, arbitrary query-string
contents, or full referrer URLs. Trader username should not be stored as
telemetry merely because it is displayed; use an allowlisted categorical
control/value where needed. Prefer normalized values such as `wallet_filter`
with `applied`/`cleared`, `sort=trades`, `period=7d`, `view=table`, or a
boolean toggle category. Store referrer host and allowlisted UTM dimensions,
not full URLs. HMAC secrets remain server-side.

## 11. Historical Data / Backfill Feasibility

**Classification: BACKFILL NOT RELIABLE** for separating historical TOP
TRADERS from ITEM. Persisted rows contain the normalized mode, optional item
key, path, normalized UTM, referrer host, and timestamps, but not the original
`mode` query parameter or a surface-navigation event. A trader-first row may
be `mode=item, item_key=NULL`, which is also a legitimate item session with
missing item context. It cannot be reliably separated after the fact.

Overall session totals, identity counts, time trends, acquisition totals,
and persisted ITEM event aggregates remain useful. Mode-specific ITEM and
campaign/post columns are not trustworthy for the affected history. A future
implementation should document a migration boundary: data before the
corrective deployment remains legacy/ambiguous; data after successful schema,
writer, and dashboard rollout is the trustworthy mode boundary. No invented
backfill is recommended.

## 12. Dashboard Gap Analysis

| Section | Current source/correctness | Trader effect | Conceptual home |
|---|---|---|---|
| Sessions | `load_dashboard_data` total session rows; correct overall | None total | Traffic / Acquisition |
| Unique Visitors | V2 hash distinct count; correct overall | None total | Traffic / Acquisition |
| New / Returning | V2 session-count/first-seen CTE; correct overall | None overall | Traffic / Acquisition |
| Latest Visit | max session timestamp; correct | None | Traffic / Acquisition |
| Traffic Over Time | session time buckets; correct overall | None | Traffic / Acquisition |
| Mode Usage | raw mode group; trader absent and item-inflated | Misclassified | Product Usage (after repair) |
| Acquisition Sources | normalized source/referrer/UTM | Surface split unavailable | Traffic / Acquisition |
| Campaign / Post Performance | UTM/post grouped with legacy mode columns | trader in item/absent as trader | Traffic / Acquisition |
| Post Performance | same post aggregate | same | Traffic / Acquisition |
| Item Interest | `s.mode='item'` session aggregation | fallback trader may inflate null-context count | Product Usage / Item |
| Item Activity | `site_item_events` joined to item sessions | trader absent | Product Usage / Item |
| Visitor Drilldown | safe session timeline + item activity | stored trader displayed as Item | Traffic timeline + Product Usage detail |

Recommended conceptual dashboard split: Traffic/Acquisition for sessions,
visitors, new/returning, sources, campaigns/posts, device/browser, and trends;
Product Usage for surface usage, ITEM selections, filters, sorts, periods,
view modes, and other allowlisted feature events.

## 13. Recommended Target Architecture

Recommend a three-responsibility model:

1. Keep `site_visit_sessions` as acquisition/session analytics, but expand
   its allowlisted surface taxonomy and make its semantics explicit as one
   initial session/surface record, not pageviews.
2. Keep `site_item_events` as the specialized ITEM context/activity stream;
   retain `item_select` there as the canonical item-selection event rather
   than duplicating it in a general table.
3. Add a general append-only `site_product_events` table for meaningful
   non-ITEM UI/product actions and subsequent surface interactions.

An alternative is to put every event into one universal table. That would
simplify ingestion but weakens the stable ITEM event contract and makes
item-specific joins/diagnostics less clear. A session-only expansion would be
lower risk but cannot represent repeated mode navigation or feature usage.
The recommended split preserves both strengths without treating every click
as telemetry.

## 14. Proposed Minimal Product Event Taxonomy

Allowlist a small vocabulary: `surface_open`, `filter_apply`,
`filter_clear`, `sort_change`, `period_change`, `view_change`, and
`toggle_change`. Keep `item_select` only in `site_item_events` to avoid
duplicates. Use dimensions such as `surface`, `control`, and normalized
allowlisted values; do not emit autocomplete keystrokes, each focus, hover,
or cosmetic clicks. `surface_open` should represent an actual mode entry or
post-load surface transition, with deduplication rules rather than every
Streamlit rerun.

## 15. Proposed Data Model

Design only; no SQL was created. A minimal general event record should have:

- `event_id` (server-generated UUID or identity)
- `occurred_at_utc`, `created_at_utc`
- nullable `parent_session_id`
- nullable V2 `browser_visitor_hash` plus `identity_version`
- allowlisted `surface/mode`
- allowlisted `event_type`
- allowlisted `control/action`
- normalized categorical `value` where necessary
- optional positive per-session `sequence_no`
- bot/internal filtering fields or a safe join to session classification

Allowlist modes (`item`, `market`, `top_items`, `trader`) and event types/
controls in code and schema. Values should be bounded enums such as
`7d`, `chart`, `usd`, `trades`, `applied`, and `cleared`. Do not accept
free-form wallet, username, search, query-string, URL, IP, or browser-ID
payloads. Architecture-level indexes should support occurred time + surface/
event type, parent session + sequence, and V2 browser hash + time; confirm
actual workload before adding indexes.

## 16. Recommended Implementation Sequence

1. Define the canonical surface taxonomy and migration boundary, including
   whether `trader` is the stored name and whether aliases normalize to it.
2. Apply a backward-compatible database migration: expand the session mode
   constraint and any mode index/query contract before enabling writes.
3. Update the Python allowlist/normalization and writer tests; remove silent
   invalid-to-item fallback for known public modes, while retaining safe
   handling for unknown input.
4. Update dashboard mode labels, mode aggregation, campaign/post columns,
   and drilldown mapping; add explicit trader coverage tests.
5. Stage and verify schema/writer/dashboard compatibility, including public
   UI failure isolation, before production rollout.
6. Add the general product-event schema and read/write safety infrastructure
   as a separate change; preserve ITEM events as the canonical item stream.
7. Instrument only selected meaningful controls with rerun-safe event IDs/
   sequence rules; never instrument per-keystroke autocomplete input.
8. Add Product Usage dashboard queries/sections with allowlisted dimensions.
9. Document the migration boundary and historical ambiguity in dashboard
   help text and operational runbooks.

Schema/writer/dashboard correctness should be one tightly coordinated core
task (with staging migration), while product events and UI/dashboard usage
should be split to reduce rollback and cardinality risk.

## 17. Recommended Task Split

- **063A — Core TOP TRADERS analytics correctness:** schema mode constraint,
  Python allowlist/normalization, session writer, dashboard labels/queries,
  campaign/post/drilldown support, obsolete tests, migration boundary, and
  staging verification. No new feature telemetry.
- **063B — Product-event infrastructure:** design and migrate the general
  append-only event table, allowlists, writer, privacy guards, deduplication,
  read-only query primitives, and tests. Keep ITEM events unchanged.
- **063C — Product instrumentation and dashboard:** instrument selected
  controls/mode transitions, add Product Usage aggregates/UI, and verify no
  duplicate events across Streamlit reruns.
- **063D — Historical/dashboard communication:** publish the boundary and
  label legacy ranges as ambiguous if needed; do not fabricate trader
  backfill.

## 18. Risk Register

| Risk | Severity / likelihood | Mitigation |
|---|---|---|
| Historical mode interpretation becomes overstated | High / High | Preserve legacy boundary; label pre-boundary data ambiguous |
| DB constraint deployed after writer | High / Medium | Migration-first compatibility window and staging rehearsal |
| Writer failure affects public UI | High / Low | Keep short timeout, write guard, exception isolation, metrics/log redaction |
| Duplicate events from reruns/callbacks | High / High | server event IDs, session sequence, idempotency rules, tests |
| Product event cardinality explosion | Medium / High | small allowlist, categorical values, no keystrokes/hover |
| Privacy regression from wallet/search capture | High / Medium | prohibit raw fields; code/schema allowlists and review |
| Performance impact of new writes/queries | Medium / Medium | append-only bounded writes, indexes by time/surface, timeouts, aggregate queries |
| Old tests preserve obsolete three-mode contract | Medium / High | update contracts only in implementation task with explicit trader cases |
| Dashboard cache hides rollout changes | Medium / Medium | cache invalidation/versioning and post-migration smoke queries |
| Staging/production schema mismatch | High / Medium | migration checksum/order checks and deploy gate |
| Duplicate item selection streams | Medium / Medium | keep `site_item_events.item_select` canonical; do not duplicate |
| Unknown modes become unsafe rows | Medium / Medium | allow known `trader`; reject/normalize unknown safely without mapping known public modes |

## 19. Tests / Contracts That Must Change

Current obsolete contracts include `tests/test_site_analytics.py::test_mode_values_are_whitelisted`, which asserts invalid modes become `item`, and `tests/test_visitor_dashboard.py::test_mode_labels_are_dashboard_safe`, which asserts exactly three labels. Relevant dashboard source tests also encode `s.mode = 'item'` for item-interest correctness; those should remain for ITEM queries but gain explicit trader isolation tests. New tests must cover the complete trader chain, DB-accepted taxonomy, post columns, timeline labels, migration boundary, event deduplication, and privacy. No tests were changed in this audit.

## 20. Files Likely To Change In Implementation

These are recommendations only; none were changed here:

- `streamlit_opensea_sales/site_analytics.py`
- `streamlit_opensea_sales/app_opensea_sales.py` only if page-transition/session semantics are revised
- `streamlit_opensea_sales/visitor_dashboard.py`
- `streamlit_opensea_sales/visitor_dashboard_queries.py`
- `sql/create_site_visit_sessions.sql` or a new ordered migration
- `tests/test_site_analytics.py`
- `tests/test_visitor_dashboard.py`
- new product-event writer/query modules, migration, tests, and selected UI instrumentation files for later 063B/063C

## 21. Commands / Verification Performed

- Baseline `git rev-parse` checks: PASS; exact required develop and main SHAs matched.
- `git status --short`: only pre-existing `?? img/gunz_scope/logo_2.png` before audit.
- `python -m pytest tests/test_site_analytics.py tests/test_visitor_dashboard.py tests/test_item_full_wallet_search.py`: **ERROR during collection** of `test_item_full_wallet_search.py` because `plotly` is unavailable (`ModuleNotFoundError: No module named 'plotly'`). The run collected 61 items and 60 tests were collected before the error; no tests were modified.
- `python -m compileall streamlit_opensea_sales`: PASS.
- `python -m pip check`: PASS (`No broken requirements found`).
- `git diff --check`: PASS after report creation.
- No staging restart, database write, application change, SQL change, or production operation was performed.

## 22. Final Verdict

The current system is **PARTIALLY OUTDATED**, not wholly unsound. Its
privacy, identity, failure-isolation, ITEM event, and read-only dashboard
foundations are usable. The expanded product’s TOP TRADERS surface is not
represented correctly: known `trader` traffic is silently stored as `item`,
while schema and dashboard contracts independently omit it. This is a
correctness and interpretation defect, not a reason to infer historical
trader usage. The next implementation should first repair the mode taxonomy
end-to-end and establish a migration boundary, then add small, privacy-safe
product events in separate tasks.

