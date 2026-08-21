# OTG Analytics public architecture

The public repository documents the analytics product boundary, not the private production infrastructure.

```text
Browser
   |
   v
Public routing / static delivery
   |
   +--> Streamlit OTG Analytics application
   |
   +--> Standalone ROADMAP and legal pages
   |
   v
Prepared market-data and analytics contracts

Visitor analytics
   |
   v
PostgreSQL

External/private ingestion and enrichment layer
```

The application consumes prepared market data and may write first-party visitor-session analytics to PostgreSQL using environment-provided credentials. Production ingestion and enrichment are operated separately and are intentionally outside this repository. No private hostnames, service configuration, credentials, bot systems, parser systems or deployment internals are documented here.
