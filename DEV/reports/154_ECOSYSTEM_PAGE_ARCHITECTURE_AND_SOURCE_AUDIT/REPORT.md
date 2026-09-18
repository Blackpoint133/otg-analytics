# Report 154 — Ecosystem Page Architecture and Source Audit

REPORT_SEQUENCE=154
RESULT=SUCCESS

## Baselines and scope

MAIN_BASELINE=9edb927dc25432effda8fe8ae353993d55297f4d
DEVELOP_BASELINE=9bbb69d1611d033bded0a66bfcb816f23305dc6f
NO_RUNTIME_MUTATION_GATE=PASS

This report is an architecture and source audit only. No application code,
database, environment, deployment, runtime, Caddy configuration, or image
asset was changed. The pre-existing untracked `img/gunz_scope/logo_2.png`
was not read, modified, added, or deleted.

## Product and navigation recommendation

ECOSYSTEM_ROUTE_RECOMMENDATION=ACCEPT `/?mode=ecosystem` as a top-level route

PAGE_TITLE=GUNZ ECOSYSTEM
PAGE_INTRODUCTION=Games, applications, infrastructure, marketplaces, and community tools connected to the GUNZ ecosystem.

NAVIGATION_RECOMMENDATION=Add ECOSYSTEM as a peer of ANALYTICS, ROADMAP, FEEDBACK, and LOG IN. Keep ITEM, MARKET, TOP ITEMS, and TOP TRADERS inside the existing ANALYTICS destination. Give ECOSYSTEM its own active state and do not map it to an analytics dropdown value.

The existing routing contract uses a closed mode set in `ui/mode_switch.py`.
The implementation task must add `ecosystem` deliberately to the top-level
route contract and branch before analytics-specific data loading. Existing
analytics modes and their query aliases must remain unchanged. The current
sidebar/logo and page-width conventions should be reused; Ecosystem should not
create a second navigation or layout system.

V1_SECTIONS=OFFICIAL ECOSYSTEM; MARKETPLACES; COMMUNITY ECOSYSTEM
V1_FILTER_UI=NONE
V1_PROJECT_COUNT=12

SELF_CARD_RECOMMENDATION=EXCLUDE

The product itself is already the site the visitor is using. A self-card would
repeat the primary destination, compete visually with the curated ecosystem
directory, and make an otherwise neutral classification system look like
self-promotion. It adds no navigation that the top-level site navigation does
not already provide. If a future ecosystem hub needs attribution, use a small
page footer/disclaimer or a single “About this directory” note instead of a
thirteenth project card.

## Catalog architecture

CATALOG_ARCHITECTURE_RECOMMENDATION=Use `streamlit_opensea_sales/config/ecosystem_projects.json` as one validated static catalog, loaded by a small Python loader/validator and rendered by a reusable Ecosystem page/card component. This is the repository-consistent option C: it follows the existing app-owned JSON configuration pattern, keeps data separate from presentation, avoids runtime network access, and makes a new project one record rather than one custom UI block.

The catalog root should contain `schema_version`, `updated_at`, and `projects`.
Each record should contain exactly the conceptual fields below, with optional
internal fields only when they do not affect presentation:

```text
id, name, type, category, description, url, logo_asset, source_url,
status, featured, tracking_key
```

Recommended validation rules are: unique stable `id`; `tracking_key == id`;
non-empty factual description; `url` and `source_url` are explicit HTTPS
URLs; `type` is one of `official`, `external_officially_linked`, or
`community`; category is from a small documented enum; `featured` is boolean;
and `logo_asset` may be null. The loader must reject malformed records rather
than render arbitrary URLs. Static catalog URLs are not user input.

`streamlit_opensea_sales/ecosystem_catalog.py` remains a reasonable loader
name, but it should not become a second source of card records. A Python module
may validate/load the JSON; the JSON should remain the single catalog source.

## Proposed V1 catalog

OFFICIAL_PROJECT_COUNT=8
EXTERNAL_MARKETPLACE_COUNT=1
COMMUNITY_PROJECT_COUNT=3

### Official ecosystem

ID=gunz
NAME=GUNZ
TYPE=official
CLASSIFICATION=OFFICIAL
CATEGORY=network
CANONICAL_URL=https://gunbygunz.com/
SOURCE_URL=https://gunbygunz.com/
SOURCE_VERIFICATION=PASS_OFFICIAL_GUNZ_HOMEPAGE
ASSET_STATE=OFFICIAL_SOURCE_AVAILABLE
DESCRIPTION_DRAFT=GUNZ is Gunzilla Games’ gaming-focused Layer-1 network and the base ecosystem for GUNZ-powered games and services.
LOGO_ASSET=null
STATUS=verified
FEATURED=true
TRACKING_KEY=gunz

ID=off_the_grid
NAME=OFF THE GRID
TYPE=official
CLASSIFICATION=OFFICIAL
CATEGORY=game
CANONICAL_URL=https://gameoffthegrid.com/
SOURCE_URL=https://gunbygunz.com/games/
SOURCE_VERIFICATION=PASS_OFFICIAL_GUNZ_GAMES_PAGE_AND_OFFICIAL_GAME_SITE
ASSET_STATE=EXISTING_LOCAL
DESCRIPTION_DRAFT=Gunzilla’s flagship game and a GUNZ-powered ecosystem entry point.
LOGO_ASSET=img/Off_The_Grid_Logo.png
STATUS=verified
FEATURED=true
TRACKING_KEY=off_the_grid

ID=technocore
NAME=TECHNOCORE
TYPE=official
CLASSIFICATION=OFFICIAL
CATEGORY=game
CANONICAL_URL=https://gunbygunz.com/technocore/
SOURCE_URL=https://gunbygunz.com/games/; https://play.google.com/store/apps/details?id=com.gunzillagames.technocore
SOURCE_VERIFICATION=PASS_OFFICIAL_GUNZ_TECHNOCORE_PAGE_AND_GUNZILLA_GOOGLE_PLAY_LISTING
ASSET_STATE=OFFICIAL_SOURCE_AVAILABLE
DESCRIPTION_DRAFT=A mobile GUNZ game built around drone missions, HEX items, and item decoding/trading.
LOGO_ASSET=null
STATUS=verified
FEATURED=false
TRACKING_KEY=technocore

ID=otg_companion
NAME=OFF THE GRID COMPANION
TYPE=official
CLASSIFICATION=OFFICIAL
CATEGORY=player_app
CANONICAL_URL=https://play.google.com/store/apps/details?id=com.gunzillagames.otg
SOURCE_URL=https://play.google.com/store/apps/details?id=com.gunzillagames.otg
SOURCE_VERIFICATION=PASS_GOOGLE_PLAY_TITLE_AND_GUNZILLA_GAMES_PUBLISHER
ASSET_STATE=OFFICIAL_SOURCE_AVAILABLE
DESCRIPTION_DRAFT=The official companion app for player stats, teammate discovery, social connections, communication, and game news.
LOGO_ASSET=null
STATUS=verified
FEATURED=false
TRACKING_KEY=otg_companion

ID=gunz_wallet
NAME=GUNZ WALLET
TYPE=official
CLASSIFICATION=OFFICIAL
CATEGORY=wallet
CANONICAL_URL=https://play.google.com/store/apps/details?id=com.gunzillagames.walletapp
SOURCE_URL=https://play.google.com/store/apps/developer?id=Gunzilla+Games
SOURCE_VERIFICATION=PASS_GOOGLE_PLAY_GUNZILLA_GAMES_LISTING_AND_GUNZ_WALLET_TITLE
ASSET_STATE=OFFICIAL_SOURCE_AVAILABLE
DESCRIPTION_DRAFT=The official Gunzilla wallet for managing GUNZ tokens, NFTs, and supported GUNZ marketplace assets.
LOGO_ASSET=null
STATUS=verified
FEATURED=false
TRACKING_KEY=gunz_wallet

ID=gunzscan
NAME=GUNZSCAN
TYPE=official
CLASSIFICATION=OFFICIAL
CATEGORY=blockchain
CANONICAL_URL=https://gunzscan.io/
SOURCE_URL=https://gunbygunz.com/gun/
SOURCE_VERIFICATION=PASS_OFFICIAL_GUNZ_DOCUMENTATION_REFERENCE_AND_EXPLORER
ASSET_STATE=OFFICIAL_SOURCE_AVAILABLE
DESCRIPTION_DRAFT=The GUNZ blockchain explorer for inspecting public chain activity and assets.
LOGO_ASSET=null
STATUS=verified
FEATURED=false
TRACKING_KEY=gunzscan

ID=gunz_bridge
NAME=GUNZ BRIDGE
TYPE=official
CLASSIFICATION=OFFICIAL
CATEGORY=blockchain
CANONICAL_URL=https://bridge.gunzchain.io/
SOURCE_URL=https://gunbygunz.com/gun/
SOURCE_VERIFICATION=PASS_OFFICIAL_GUNZ_PAGE_LINKS_TO_GUNZ_L1_BRIDGE
ASSET_STATE=OFFICIAL_SOURCE_AVAILABLE
DESCRIPTION_DRAFT=The official GUNZ bridge for moving supported assets between GUNZ and connected networks.
LOGO_ASSET=null
STATUS=verified
FEATURED=false
TRACKING_KEY=gunz_bridge

ID=gunz_developers
NAME=GUNZ DEVELOPERS
TYPE=official
CLASSIFICATION=OFFICIAL
CATEGORY=developer
CANONICAL_URL=https://gunbygunz.com/develop/
SOURCE_URL=https://www.gunbygunz.com/documentation/; https://gunbygunz.com/develop/
SOURCE_VERIFICATION=PASS_OFFICIAL_PRODUCTION_DEVELOPER_LANDING_PAGE; PROVIDED_DOCUMENTATION_URL_NOT_USED_AS_PRIMARY_WHILE_CURRENT_PRODUCTION_DESTINATION_IS_DEVELOP
ASSET_STATE=OFFICIAL_SOURCE_AVAILABLE
DESCRIPTION_DRAFT=The official production developer landing page for GUNZ APIs, wallet/mobile SDKs, marketplace, scanner, and ecosystem onboarding.
LOGO_ASSET=null
STATUS=verified
FEATURED=false
TRACKING_KEY=gunz_developers

The supplied `www.gunbygunz.com/documentation/` source was audited, but the
production `/develop/` landing page is the safer V1 primary destination. Do not
use the obsolete `dev-test.gunbygunz.com` documentation result. If the exact
production documentation endpoint becomes verifiable during implementation,
it may replace `/develop/` without changing the card’s classification.

### Marketplace

ID=opensea_otg
NAME=OFF THE GRID ON OPENSEA
TYPE=external_officially_linked
CLASSIFICATION=EXTERNAL MARKETPLACE
CATEGORY=marketplace
CANONICAL_URL=https://opensea.io/collection/off-the-grid/
SOURCE_URL=https://opensea.io/collection/off-the-grid/; https://gunbygunz.com/
SOURCE_VERIFICATION=PASS_USER_PROVIDED_COLLECTION_TARGET; OFFICIAL_GUNZ_MATERIALS_REFERENCE_OPEN_SEA_VENUES
ASSET_STATE=SOURCE_REQUIRED
DESCRIPTION_DRAFT=An external OpenSea venue for Off The Grid assets; it is a marketplace destination, not a Gunzilla product.
LOGO_ASSET=null
STATUS=verified_external
FEATURED=true
TRACKING_KEY=opensea_otg

OpenSea must never be rendered with the OFFICIAL badge. The card may say
“External marketplace” and, if needed, “linked venue” without implying
ownership or endorsement beyond the documented link context.

### Community ecosystem

ID=gunzscope
NAME=GUNZSCOPE
TYPE=community
CLASSIFICATION=COMMUNITY
CATEGORY=analytics
CANONICAL_URL=https://gunzscope.xyz/
SOURCE_URL=https://gunzscope.xyz/
SOURCE_VERIFICATION=PASS_PUBLIC_SITE_IDENTIFIES_OTG_PORTFOLIO_AND_ON_CHAIN_INTELLIGENCE; NO_FIRST_PARTY_OWNERSHIP_CLAIM
ASSET_STATE=EXISTING_LOCAL
DESCRIPTION_DRAFT=An independent OTG/GUNZ portfolio and on-chain intelligence tool for item, identity, acquisition, and valuation analysis.
LOGO_ASSET=img/gunz_scope/logo_1.png
STATUS=verified_community
FEATURED=false
TRACKING_KEY=gunzscope

ID=otgstats
NAME=OTG STATS
TYPE=community
CLASSIFICATION=COMMUNITY
CATEGORY=game_tools
CANONICAL_URL=https://www.otgstats.com/
SOURCE_URL=https://www.otgstats.com/
SOURCE_VERIFICATION=PASS_USER_PROVIDED_PUBLIC_PROJECT_SOURCE; COMMUNITY_TOOL_CLASSIFICATION_REQUIRED
ASSET_STATE=SOURCE_REQUIRED
DESCRIPTION_DRAFT=An independent Off The Grid weapon database and loadout/statistics tool.
LOGO_ASSET=null
STATUS=source_reviewed
FEATURED=false
TRACKING_KEY=otgstats

ID=walletzero
NAME=WALLETZERO
TYPE=community
CLASSIFICATION=COMMUNITY
CATEGORY=wallet
CANONICAL_URL=https://walletzero.io/
SOURCE_URL=https://walletzero.io/
SOURCE_VERIFICATION=PASS_PUBLIC_SITE_DESCRIBES_INDEPENDENT_NON_CUSTODIAL_GUN_TOOLING; NO_GUNZILLA_OWNERSHIP_CLAIM
ASSET_STATE=SOURCE_REQUIRED
DESCRIPTION_DRAFT=An independent non-custodial wallet and multi-chain GUN tooling project; it is not a Gunzilla wallet.
LOGO_ASSET=null
STATUS=verified_community
FEATURED=false
TRACKING_KEY=walletzero

## Classification and source gates

OFFICIAL_COMMUNITY_CLASSIFICATION_GATE=PASS
OPENSEA_CLASSIFICATION_GATE=PASS_EXTERNAL_MARKETPLACE_NOT_OFFICIAL
WALLETZERO_CLASSIFICATION_GATE=PASS_COMMUNITY_NOT_OFFICIAL
COMPANION_APP_SOURCE_GATE=PASS_GOOGLE_PLAY_GUNZILLA_PUBLISHER
GUNZ_WALLET_SOURCE_GATE=PASS_GOOGLE_PLAY_GUNZILLA_PUBLISHER
GUNZSCAN_SOURCE_GATE=PASS_OFFICIAL_GUNZ_REFERENCE
GUNZ_BRIDGE_SOURCE_GATE=PASS_OFFICIAL_GUNZ_LINK_TO_BRIDGE

The source set is intentionally closed to the twelve user-specified projects.
No search-discovered project was added. Official/community distinctions are
based on first-party ownership or official source context, not on visual
similarity, proximity to a game, or a project’s use of GUNZ.

## Feedback context and routing implications

FEEDBACK_ECOSYSTEM_CONTEXT_RECOMMENDATION=ADOPT in Task 155 only if Ecosystem cards/page expose the existing feedback entry point; pass `source=ecosystem` through the same feedback context/back-navigation contract. If Task 155 intentionally has no Ecosystem feedback entry point, retain the existing source values and do not synthesize an ecosystem source.

FEEDBACK_SCHEMA_IMPLICATION=The current application and database do not support ecosystem as a durable feedback source. `ui/mode_switch.py` and `ui/feedback.py` need normalization, label, back-target, and allowed-source updates; `feedback_store.py` needs its source enum updated; `feedback_notifications.py` needs a source label mapping; and `sql/create_user_feedback.sql` plus a forward migration must extend the source_mode CHECK constraint. Existing source handling also has a roadmap/unknown compatibility edge that should be tested rather than silently copied. No migration is performed in Task 154.

ECOSYSTEM_ANALYTICS_SCHEMA_IMPLICATION=If Ecosystem page opens and outbound clicks are recorded as first-class analytics, `site_analytics.py` and the site-visit mode CHECK constraint need `ecosystem`; product-event validation and the product-events CHECK/shape constraints need an `ecosystem` surface and `outbound_click` event. This is a Task 155 migration decision, not a Task 154 change.

## Visual and responsive architecture

VISUAL_DIRECTION=Use the current OTG dark analytical shell: strict dark background, existing content width/alignment, thin neutral borders, restrained #FF003A accent, white/grey type, and compact analytical spacing. Do not copy the GUNZ site, use giant hero artwork, add gradient-heavy Web3 styling, or introduce a second design system.

DESKTOP_LAYOUT_RECOMMENDATION=At viewport width >=1025px, render a reusable card grid at three equal columns inside the existing Streamlit block container/content alignment. Use consistent card geometry, a compact logo area, classification/category metadata, title, two-to-three-line description, and a bottom-aligned VISIT action. Use the existing page padding and border/color tokens.

TABLET_LAYOUT_RECOMMENDATION=At 769–1024px, use two equal columns with the same card min-height and spacing. This is one additional page-specific breakpoint that complements the existing navigation’s 768px breakpoint; do not create a new global responsive system.

MOBILE_LAYOUT_RECOMMENDATION=At <=768px, use one column, full available width, compact horizontal padding, and no horizontal scrolling. Keep the badge, title, description, and Visit action readable at the existing mobile control/font scale.

The page should not include category filters, search, tabs, carousels, or other
controls in V1. Twelve curated cards are small enough to scan, and controls
would make a directory feel like a second analytics surface. Section headings
provide the needed grouping.

## Card, asset, security, and tracking contracts

CARD_CONTRACT=Every card is data-driven and renders LOGO, classification badge, category label, NAME, compact factual description, and VISIT. External links use target=_blank and rel=noopener noreferrer. The card never renders arbitrary HTML or user-supplied URLs.

ASSET_ACQUISITION_PLAN=Prefer small local, provenance-documented assets in a dedicated ecosystem asset folder during Task 155. Reuse `img/Off_The_Grid_Logo.png` and `img/gunz_scope/logo_1.png` only after dimensions/format review. Do not touch `img/gunz_scope/logo_2.png`. For missing logos, first use an official source asset or a restrained text/initial fallback; do not hotlink at runtime, scrape screenshots, or substitute screenshots for logos. Optimize local images to reasonable card dimensions and record source/provenance in documentation or catalog metadata.

ASSET_AUDIT_SUMMARY=Local relevant assets found: Off The Grid logo and the tracked GUNZscope logo_1. No verified local assets were found for GUNZ, Technocore, Companion, GUNZ Wallet, GUNZscan, GUNZ Bridge, developer landing, OpenSea, OTG Stats, or WalletZero. Their per-card states are recorded above.

SECURITY_GATE=PASS_STATIC_HTTPS_ALLOWLIST_NO_USER_URLS_NO_IFRAMES_NO_EXTERNAL_SCRIPTS_NO_CREDENTIALS

OUTBOUND_TRACKING_ARCHITECTURE=Extend the existing product-event contract with `surface=ecosystem`, `event_type=outbound_click`, `control_key=<catalog id>`, and `value_key=<classification>_<category>`. Use a minimal same-origin reusable link component or equivalent existing component pattern: it receives only validated catalog records, opens the static URL immediately in a new tab with noopener/noreferrer, and emits one server-side event using the existing anonymous parent-session/product-event path. The event payload contains only the stable project id and classification/category; it must not include URL query data, referrers, credentials, or arbitrary user input. Do not use a delayed JavaScript fetch, iframe, external script, or invasive global click interception. If the current Streamlit event lifecycle cannot guarantee both navigation and recording without a component, document the limitation and use a same-origin redirect/recording endpoint in a follow-up rather than silently claiming reliability.

OUTBOUND_TRACKING_IMPLEMENTATION_IMPLICATIONS=Add `outbound_click` to the validated event shape and update the database CHECK/shape migration in Task 155. Make the component idempotent per click cycle so rerenders cannot duplicate events. Keep tracking optional/fail-soft: event failure must not block the external destination or alter card selection/navigation.

## Task 155 implementation and test plan

TASK_155_IMPLEMENTATION_PLAN=1) Add and validate the static JSON catalog. 2) Add a top-level ecosystem route and active navigation state without changing existing analytics mode semantics. 3) Render the three sections through one reusable card/grid component. 4) Add local assets/fallbacks with provenance, leaving the untracked logo_2 untouched. 5) Decide and, if approved, implement ecosystem feedback context plus the required application and DB migrations. 6) Extend product-event validation/storage for outbound clicks. 7) Add focused tests, run the existing suite once, deploy only to DEV/8504, and perform owner visual validation before any production consideration.

TASK_155_TEST_MATRIX=
1. `/?mode=ecosystem` is recognized and renders the Ecosystem page.
2. ECOSYSTEM has the correct top-level active navigation state.
3. ITEM, MARKET, TOP ITEMS, TOP TRADERS, ROADMAP, FEEDBACK, and existing aliases remain unchanged.
4. Catalog project IDs and tracking keys are unique and stable.
5. Every catalog URL/source URL is explicit HTTPS and passes the static allowlist.
6. Classifications are restricted to official, external_officially_linked, and community.
7. OpenSea is external marketplace, never official.
8. WalletZero is community, never official.
9. The companion app and GUNZ Wallet resolve to the Gunzilla Games Google Play publisher/products.
10. GUNZscan, GUNZ Bridge, and developer destination resolve to verified official sources.
11. Sections and card order match the curated V1 catalog; no filter UI is rendered.
12. Desktop/tablet/mobile grid contract is 3/2/1 cards per row at the specified breakpoints.
13. Card geometry, badge/category/name/description/Visit anatomy, and missing-logo fallback are deterministic.
14. External anchors have `target=_blank` and `rel=noopener noreferrer`; no iframe/script injection occurs.
15. Outbound event shape is surface=ecosystem, event_type=outbound_click, control_key=project id, and valid classification/category value_key.
16. A click records at most one event and external navigation is not delayed or blocked when event recording fails.
17. If ecosystem feedback is adopted, source normalization, label/back navigation, notification mapping, DB CHECK migration, and one-event submission are tested.
18. Profile sync, OpenSea credentials, feedback persistence, existing analytics calculations, and production deployment behavior have no regression.
19. The page is accessible without depending on remote asset loads; missing or failed logos use the declared fallback.
20. No runtime, DB, environment, Caddy, 8501, 8502, or 8504 mutation occurs during the implementation test fixture phase.

## Final audit gates

SOURCE_SCOPE_GATE=PASS_TWELVE_USER_SPECIFIED_PROJECTS_ONLY
NO_MARKETING_COPY_GATE=PASS_COMPACT_FACTUAL_DESCRIPTIONS
NO_SELF_PROMOTION_GATE=PASS_SELF_CARD_EXCLUDED
NO_RUNTIME_MUTATION_GATE=PASS
RESULT=SUCCESS
