# API Frontend Contract

Last updated: 2026-04-24

This document records the current read-only API contract that the web frontend should use.

It exists to keep frontend work consistent and to avoid accidental overfetching or query misuse.

## General Rules

- Base URL comes from `PUBLIC_API_BASE_URL`.
- All current frontend-facing endpoints are `GET`.
- Responses use the same outer shape:

```json
{
  "data": {},
  "meta": {}
}
```

- `meta.generated_at` is the server-side generation timestamp.
- `meta.cache_ttl_sec` is the API cache hint for ranking/detail reads.
- Frontend should treat `404` as “not found” and all other non-200 responses as generic temporary failure.

## Frontend Usage Rules

- Main leaderboard page should call only the leaderboard endpoint.
- Item detail should be requested only on the item detail page.
- Build detail should be requested only on the build detail page.
- Do not automatically chain:
  - leaderboard -> item detail
  - item detail -> build detail
- Preserve URL-driven filters when navigating between leaderboard, item detail, and build detail pages.
- Prefer a compact loading state and avoid duplicate retries from multiple reactive paths.

## Current Endpoints

### 1. Slot family leaderboard

`GET /v1/leaderboards/items/{slot}`

Purpose:
- family-first ranking table for `main_hand`, `head`, `armor`, `shoes`
- collapses tier and enchant duplicates into one family row before ranking

Supported path params:
- `slot`: supported backend slot such as `main_hand`, `head`, `armor`, `shoes`

Supported query params:
- `days`: integer, `1..90`
- `region`: `europe | americas | asia`
- `patch_id`: integer, optional
- `content_type`: `open_world | corrupted_dungeon | mists | hellgate | roads | abyssal | unknown`
- `fight_scale`: `solo | duo | small_party | party | large_party | zvz | unknown`
- `kill_area`: string, optional
- `limit`: integer, `1..100`
- `min_sample`: integer, `0..10000`

Current frontend recommendation:
- use `days`
- use `region`
- use `fight_scale`
- keep `limit`
- keep `min_sample`
- only use `content_type` or `patch_id` when the UI explicitly exposes them
- avoid `kill_area` for the main product flow unless upstream data quality improves

Example:

```text
/v1/leaderboards/items/main_hand?days=7&region=asia&fight_scale=duo&limit=20&min_sample=25
```

Important response fields:
- `family_key`
- `representative_item_type`
- `variant_count`
- `adjusted_score`
- `kill_side_rate`
- `pick_rate`
- `sample`
- `confidence`

Frontend note:
- this should be the default leaderboard for the redesigned web app
- main page and slot pages should use this endpoint instead of showing per-tier duplicates

### 2. Family detail

`GET /v1/families/{slot}/{family_key}`

Purpose:
- detail page for a weapon or armor family, aggregated across tier variants first

Supported path params:
- `slot`
- `family_key`

Supported query params:
- `days`
- `region`
- `patch_id`
- `content_type`
- `fight_scale`
- `kill_area`

Example:

```text
/v1/families/main_hand/MAIN_SWORD?days=7&region=asia&fight_scale=duo
```

Important response fields:
- `summary`
- `representative_item_type`
- `variants`
- `distributions.by_fight_scale`
- `builds.top_builds`

Frontend note:
- this is the preferred item page shape for the family-first redesign
- `variants` should be rendered as the tier breakdown under the family summary

### 3. Exact item detail

`GET /v1/items/{slot}/{item_type}`

Purpose:
- detail page for a specific item, currently main-hand focused in the web app

Supported path params:
- `slot`: one of the supported slots from the backend
- `item_type`: stable Albion item key

Supported query params:
- `days`
- `region`
- `patch_id`
- `content_type`
- `fight_scale`
- `kill_area`

Example:

```text
/v1/items/main_hand/T8_MAIN_SWORD?days=7&region=asia&fight_scale=duo
```

Important response fields:
- `summary`
- `distributions.by_content_type`
- `distributions.by_fight_scale`
- `distributions.by_patch`
- `builds.representative_build`
- `builds.top_builds`

Frontend note:
- the item detail page may link to build detail pages
- this endpoint should not be prefetched from the leaderboard page

### 4. Build detail

`GET /v1/builds/{build_key}`

Purpose:
- detail page for a specific build key

Supported path params:
- `build_key`

Supported query params:
- `days`
- `region`
- `patch_id`
- `content_type`
- `fight_scale`
- `kill_area`

Example:

```text
/v1/builds/HEAD|ARMOR|SHOES|WEAPON|OFF|CAPE?days=7&region=asia&fight_scale=duo
```

Important response fields:
- `components`
- `summary`
- `distributions.by_content_type`
- `distributions.by_fight_scale`
- `distributions.by_patch`

Frontend note:
- build detail should be reached from a direct click or deep link
- do not auto-open build detail during leaderboard load

## What The Frontend Is Doing Correctly Now

- The main page uses only the family leaderboard endpoint.
- Family detail and build detail are split into separate routes.
- Filters are carried through navigation in the URL.
- The main page no longer needs to auto-fetch build detail.

## Known Product Assumptions

- Upstream `KillArea` is currently coarse and often behaves like `OPEN_WORLD`.
- Exact map filtering is therefore not a primary frontend control.
- Human-readable labels should be shown first.
- Stable raw keys such as `item_type` and `build_key` remain the true API identifiers.

## Recommended Next Rules

- Keep the main page leaderboard-first and family-first.
- Add new frontend views only when there is a matching API endpoint with a stable contract.
- If frontend starts needing multiple endpoints on first paint, revisit the API shape before layering on more requests.
