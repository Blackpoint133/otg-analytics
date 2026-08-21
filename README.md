# OTG Analytics

OTG Analytics is an independent, community-built analytics product for Off The Grid marketplace activity.

Live site: https://otgos.run.place

## Independence

OTG Analytics is an independent community project. It is not operated by, affiliated with, sponsored by, endorsed by, or otherwise officially connected to Gunzilla Games or the official Off The Grid team.

## Current product

The public product currently provides:

- Item Analytics
- Market Analytics
- Top Items Analytics
- a public roadmap
- public Terms, Privacy and Disclaimer pages

## Architecture boundary

This repository contains the public analytics application and its public-facing documentation. Production data ingestion and enrichment are operated separately and are not part of this repository.

Production market datasets and runtime state are intentionally excluded from Git. The application is not currently a fully self-contained local demo for third parties; prepared data and database dependencies remain external. Synthetic fixtures, schema documentation and a more complete local-development mode may be added later.

## Environment

Copy the variable names from `.env.example` into a local environment and provide values outside Git. Never commit `.env`, database credentials, analytics HMAC secrets or production data.

## Technology

The application is built around Python and Streamlit, with local prepared market-data contracts and optional PostgreSQL-backed first-party visitor analytics. See `docs/architecture.md` for the public high-level boundary.

## Legal

- [Terms](https://otgos.run.place/legal/terms)
- [Privacy](https://otgos.run.place/legal/privacy)
- [Disclaimer](https://otgos.run.place/legal/disclaimer)

## Development transparency

This repository is intended to provide users and potential contributors with a transparent public development history for OTG Analytics. Private ingestion systems, production data, server state and credentials are deliberately kept outside the repository.

## Source availability

This repository is published for transparency and source inspection. It is not currently distributed under an open-source license. No additional rights to use, modify, or redistribute the source are granted except where separately stated.
