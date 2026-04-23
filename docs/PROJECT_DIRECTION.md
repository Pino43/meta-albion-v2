# Project Direction

Last updated: 2026-04-23

This document records the current product direction, deployment assumptions, and UX preferences so future conversations do not need to rediscover them.

## Product Scope

- The current live scope is:
  - Railway collector worker
  - Railway Postgres
  - read-only Railway API
  - static SvelteKit web frontend
- Web, API, and collector are all in service of **Albion Online meta analysis** based on kill-event data.
- The current high-value user problem is **recent meta analysis**, especially the most recent 7 days.

## Deployment Direction

- Collector stays on Railway as a long-running worker.
- API stays on Railway as a separate read-only service.
- Web stays **static**.
- Preferred web stack:
  - SvelteKit
  - adapter-static
  - `ssr = false`
  - no Node runtime dependency in production
- Cloudflare Pages is the preferred web host for the static output.
- Cold-start-heavy SSR deployment is explicitly not desired.

## Database Direction

- Primary operational database is Railway Postgres.
- The project should support:
  - raw event ingestion
  - normalized loadouts
  - event context classification
  - daily aggregates
  - outcome/ranking aggregates
- Recent 7-day analysis is more important than long raw retention.
- It is acceptable to use retention/cleanup to control storage costs.

## Access and Safety

- Application services may use the operational `DATABASE_URL`.
- For testing/debugging outside the application path, prefer a separate read-only database account and URL.
- The user may manually verify Railway permissions and provide results back to the agent.
- Future agent work should not assume direct production DB write access.

## Gameinfo API Assumptions

- `Version` in kill events is treated as payload/schema version, not game patch version.
- Patch segmentation should be derived from `time_stamp` plus `game_patches`.
- Current observed `/events` behavior is coarse:
  - `KillArea` may be `OPEN_WORLD`
  - `Location` may be `null`
  - `Participants` may already include the `Killer`
- Because of that, frontend and analysis should prioritize coarse content types over exact map naming.

## Frontend UX Direction

- The frontend should feel closer to **op.gg** or **MetaTFT** than a general dashboard or landing page.
- The first screen should be the actual ranking experience.
- Primary goals:
  - table-first ranking view
  - high readability at a glance
  - fast comparison across rows
  - clean, compact filtering
  - clear visual hierarchy
- Avoid exposing low-value raw controls too early.
  - Exact `kill_area` / map filter should not be a primary control when the upstream data is mostly `open_world`.
- Prefer human-readable item/build labels over raw stable keys in the main UI.
- Raw stable keys such as `item_type` and `build_key` may still appear as secondary/reference text.

## Item Naming Direction

- Item naming is currently handled on the frontend with a local parser/mapping approach.
- This mapping should stay easy for the user to edit later.
- If a richer metadata source is adopted later, it should be layered in without breaking stable-key usage.

## Current Practical Priorities

1. Keep collector/API/data pipeline stable.
2. Improve web readability and ranking UX.
3. Maintain editable item-name mapping.
4. Keep production access safe and minimally privileged.

## Notes for Future Agents

- Read `AGENTS.md` first.
- Treat this file as the current product-direction snapshot.
- If a future conversation changes scope or UX goals, update this file along with `AGENTS.md`.
