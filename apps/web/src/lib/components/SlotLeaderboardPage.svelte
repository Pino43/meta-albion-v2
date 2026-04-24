<svelte:options runes={false} />

<script lang="ts">
  import { onMount } from 'svelte';

  import { fetchItemFamilyLeaderboard, fightScales, regions, type ItemFamilyLeaderboardRow, type LeaderboardFilters } from '$lib/api';
  import {
    applyDraft,
    dayOptions,
    defaultFilters,
    draftFromFilters,
    filtersFromParams,
    filtersToParams,
    fightScaleLabel,
    limitOptions,
    minSampleOptions,
    regionLabel,
    summarizeFilters,
    type FilterDraft
  } from '$lib/filters';
  import { confidenceClass, formatCompact, formatPercent, formatSignedPercent } from '$lib/format';
  import { itemImageUrl, labelForFamilyKey } from '$lib/item';
  import { slotHeadings, slotLabels, type DashboardSlot } from '$lib/slots';

  type LoadState = 'loading' | 'ready' | 'error';

  export let slot: DashboardSlot = 'main_hand';

  let initialized = false;
  let filters: LeaderboardFilters = defaultFilters();
  let draft: FilterDraft = draftFromFilters(filters);
  let rows: ItemFamilyLeaderboardRow[] = [];
  let state: LoadState = 'loading';
  let apiStatus: LoadState = 'loading';
  let requestId = 0;

  $: pageTitle = slotHeadings[slot];
  $: filterSummary = summarizeFilters(filters);
  $: leadRow = rows[0] ?? null;
  $: topPickRow =
    rows.reduce<ItemFamilyLeaderboardRow | null>((best, row) => {
      if (best === null) return row;
      return (row.pick_rate ?? 0) > (best.pick_rate ?? 0) ? row : best;
    }, null);
  $: totalSample = rows.reduce((sum, row) => sum + row.sample, 0);
  $: queryString = (() => {
    const query = filtersToParams(filters).toString();
    return query ? `?${query}` : '';
  })();
  $: loadKey = initialized ? JSON.stringify({ slot, filters }) : '';
  $: if (loadKey) {
    void loadLeaderboard();
  }

  onMount(() => {
    const nextFilters = filtersFromParams(new URLSearchParams(window.location.search));
    filters = nextFilters;
    draft = draftFromFilters(nextFilters);
    initialized = true;
  });

  function applyFilters() {
    filters = applyDraft(draft);
  }

  function resetFilters() {
    const next = defaultFilters();
    filters = next;
    draft = draftFromFilters(next);
  }

  function syncUrl() {
    const query = filtersToParams(filters).toString();
    history.replaceState(null, '', `${window.location.pathname}${query ? `?${query}` : ''}`);
  }

  $: if (initialized) {
    syncUrl();
  }

  async function loadLeaderboard() {
    const current = ++requestId;
    state = 'loading';
    apiStatus = 'loading';

    try {
      const result = await fetchItemFamilyLeaderboard(slot, filters);
      if (current !== requestId) return;
      rows = result.data;
      state = 'ready';
      apiStatus = 'ready';
    } catch {
      if (current !== requestId) return;
      rows = [];
      state = 'error';
      apiStatus = 'error';
    }
  }

  function familyHref(familyKey: string): string {
    return `/families/${slot}/${encodeURIComponent(familyKey)}${queryString}`;
  }
</script>

<svelte:head>
  <title>{pageTitle} - Albion Analytics</title>
</svelte:head>

<main class="page-shell">
  <section class="hero">
    <div class="hero-copy">
      <p class="eyebrow">Albion Analytics</p>
      <h1>{pageTitle}</h1>
      <p class="hero-text">
        Tier duplicates are collapsed first, so you can read the meta by weapon or armor family
        before drilling into exact variants.
      </p>
    </div>

    <div class="hero-stats">
      <div class="stat-card">
        <span>Adjusted leader</span>
        <strong>{leadRow ? labelForFamilyKey(leadRow.family_key) : 'Waiting for data'}</strong>
      </div>
      <div class="stat-card">
        <span>Pick-rate leader</span>
        <strong>{topPickRow ? labelForFamilyKey(topPickRow.family_key) : 'Waiting for data'}</strong>
      </div>
      <div class="stat-card">
        <span>Visible families</span>
        <strong>{rows.length}</strong>
      </div>
      <div class="stat-card">
        <span>Total sample</span>
        <strong>{formatCompact(totalSample)}</strong>
      </div>
    </div>
  </section>

  <section class="toolbar surface">
    <div class="toolbar-head">
      <div>
        <p class="eyebrow">Filters</p>
        <h2>{slotLabels[slot]} snapshot</h2>
      </div>
      <div class={`api-indicator ${apiStatus}`}>
        {apiStatus === 'ready'
          ? 'API connected'
          : apiStatus === 'error'
            ? 'API issue'
            : 'Checking API'}
      </div>
    </div>

    <form class="toolbar-grid" on:submit|preventDefault={applyFilters}>
      <label>
        Days
        <select bind:value={draft.days}>
          {#each dayOptions as option}
            <option value={option}>{option}d</option>
          {/each}
        </select>
      </label>

      <label>
        Region
        <select bind:value={draft.region}>
          {#each regions as region}
            <option value={region}>{regionLabel(region)}</option>
          {/each}
        </select>
      </label>

      <label>
        Scale
        <select bind:value={draft.fightScale}>
          {#each fightScales as option}
            <option value={option}>{fightScaleLabel(option)}</option>
          {/each}
        </select>
      </label>

      <label>
        Rows
        <select bind:value={draft.limit}>
          {#each limitOptions as option}
            <option value={option}>{option}</option>
          {/each}
        </select>
      </label>

      <label>
        Min sample
        <select bind:value={draft.minSample}>
          {#each minSampleOptions as option}
            <option value={option}>{option}</option>
          {/each}
        </select>
      </label>

      <div class="filter-actions">
        <button class="button button-muted" type="button" on:click={resetFilters}>Reset</button>
        <button class="button button-strong" type="submit">Update</button>
      </div>
    </form>

    <p class="toolbar-summary">{filterSummary}</p>
  </section>

  <section class="surface table-panel">
    <div class="panel-head">
      <div>
        <p class="eyebrow">Families</p>
        <h2>{slotLabels[slot]} leaderboard</h2>
      </div>
      <span>Click through when you want the per-tier breakdown and top builds.</span>
    </div>

    {#if state === 'loading'}
      <div class="loading-table" aria-label="Loading leaderboard">
        {#each Array(10) as _}
          <div class="loading-row"></div>
        {/each}
      </div>
    {:else if state === 'error'}
      <div class="empty-state">
        <h3>API connection issue.</h3>
        <p>Family rankings could not be loaded. Please try again in a moment.</p>
        <button class="button button-muted" type="button" on:click={() => void loadLeaderboard()}>
          Retry
        </button>
      </div>
    {:else if rows.length === 0}
      <div class="empty-state">
        <h3>No families for this slice.</h3>
        <p>Try a broader region, wider time window, or lower sample gate.</p>
      </div>
    {:else}
      <div class="table-scroll">
        <table class="rank-table">
          <thead>
            <tr>
              <th>#</th>
              <th>{slotLabels[slot]}</th>
              <th>Variants</th>
              <th>Adjusted</th>
              <th>Kill-side</th>
              <th>Pick rate</th>
              <th>Sample</th>
              <th>Confidence</th>
            </tr>
          </thead>
          <tbody>
            {#each rows as row, index}
              <tr>
                <td class="rank-index">{index + 1}</td>
                <td>
                  <a class="item-link" href={familyHref(row.family_key)}>
                    <img
                      alt={labelForFamilyKey(row.family_key)}
                      src={itemImageUrl(row.representative_item_type)}
                      loading="lazy"
                    />
                    <span class="item-copy">
                      <strong>{labelForFamilyKey(row.family_key)}</strong>
                      <code>{row.family_key}</code>
                    </span>
                  </a>
                </td>
                <td>{row.variant_count}</td>
                <td class:positive={row.adjusted_score >= 0}>{formatSignedPercent(row.adjusted_score)}</td>
                <td>{formatPercent(row.kill_side_rate)}</td>
                <td>{formatPercent(row.pick_rate)}</td>
                <td>{formatCompact(row.sample)}</td>
                <td>
                  <span class={`confidence ${confidenceClass(row.confidence)}`}>{row.confidence}</span>
                </td>
              </tr>
            {/each}
          </tbody>
        </table>
      </div>
    {/if}
  </section>
</main>

<style>
  .page-shell {
    display: grid;
    gap: 16px;
  }

  .surface {
    background: var(--surface);
    border: 1px solid var(--line);
    padding: 20px;
  }

  .hero {
    background: var(--surface-strong);
    border: 1px solid var(--line-strong);
    color: var(--surface);
    display: grid;
    gap: 20px;
    grid-template-columns: minmax(0, 1.35fr) minmax(0, 1fr);
    padding: 22px;
  }

  .hero-copy,
  .hero-stats,
  .toolbar {
    display: grid;
    gap: 12px;
  }

  .eyebrow,
  label,
  .stat-card span,
  .rank-table th {
    color: var(--text-soft);
    font-size: 11px;
    font-weight: 700;
    letter-spacing: 0.08em;
    text-transform: uppercase;
  }

  .hero .eyebrow,
  .hero .stat-card span {
    color: #b8afa2;
  }

  h1,
  h2,
  h3,
  p {
    margin: 0;
  }

  h1 {
    font-size: 34px;
    line-height: 1;
  }

  h2 {
    font-size: 24px;
    line-height: 1.05;
  }

  .hero-text,
  .panel-head span,
  .toolbar-summary,
  .empty-state p {
    color: var(--text-soft);
    font-size: 13px;
    line-height: 1.5;
  }

  .hero-text {
    color: #d3cbc1;
    max-width: 60ch;
  }

  .hero-stats {
    grid-template-columns: repeat(2, minmax(0, 1fr));
  }

  .stat-card {
    background: #1a1a1a;
    border: 1px solid #33312d;
    display: grid;
    gap: 8px;
    min-height: 88px;
    padding: 14px;
  }

  .stat-card strong {
    color: #f5f1e8;
    font-size: 16px;
    line-height: 1.25;
    overflow-wrap: anywhere;
  }

  .toolbar-head,
  .panel-head {
    align-items: baseline;
    display: flex;
    gap: 12px;
    justify-content: space-between;
  }

  .api-indicator,
  .confidence {
    border: 1px solid var(--line);
    display: inline-flex;
    font-size: 11px;
    font-weight: 700;
    min-height: 28px;
    padding: 0 10px;
    text-transform: uppercase;
    align-items: center;
  }

  .api-indicator.loading {
    background: var(--surface-muted);
  }

  .api-indicator.ready {
    background: #f6edd8;
    border-color: #d2b06c;
    color: #6d511a;
  }

  .api-indicator.error {
    background: #f8e8e2;
    border-color: #c99584;
    color: #7b3d2d;
  }

  .toolbar-grid {
    align-items: end;
    display: grid;
    gap: 12px;
    grid-template-columns: repeat(5, minmax(0, 1fr)) auto;
  }

  label {
    display: grid;
    gap: 6px;
  }

  select {
    background: #fff;
    border: 1px solid var(--line);
    min-height: 38px;
    padding: 0 10px;
  }

  .filter-actions {
    display: flex;
    gap: 8px;
    justify-content: flex-end;
  }

  .button {
    border: 1px solid var(--line);
    cursor: pointer;
    font-size: 12px;
    font-weight: 700;
    min-height: 38px;
    padding: 0 14px;
  }

  .button-strong {
    background: var(--surface-strong);
    border-color: var(--surface-strong);
    color: var(--surface);
  }

  .button-muted {
    background: transparent;
    color: var(--text);
  }

  .table-panel {
    display: grid;
    gap: 12px;
  }

  .table-scroll {
    overflow: auto;
  }

  .rank-table {
    border-collapse: collapse;
    min-width: 960px;
    width: 100%;
  }

  .rank-table th,
  .rank-table td {
    border-bottom: 1px solid var(--line);
    padding: 12px 10px;
    text-align: left;
    vertical-align: middle;
  }

  .rank-table th {
    background: var(--surface);
    position: sticky;
    top: 0;
    z-index: 1;
  }

  .rank-index {
    width: 52px;
  }

  .item-link {
    align-items: center;
    color: inherit;
    display: grid;
    gap: 14px;
    grid-template-columns: 58px minmax(0, 1fr);
    text-decoration: none;
  }

  .item-link img {
    height: 58px;
    object-fit: contain;
    width: 58px;
  }

  .item-copy {
    display: grid;
    gap: 4px;
    min-width: 0;
  }

  .item-copy strong,
  .item-copy code {
    overflow-wrap: anywhere;
  }

  code {
    color: #756d63;
    font-family: 'IBM Plex Mono', 'Cascadia Code', Consolas, monospace;
    font-size: 10px;
  }

  .positive {
    color: #9a6810;
    font-weight: 700;
  }

  .confidence.low {
    background: #f2f0eb;
    color: #696157;
  }

  .confidence.medium {
    background: #fbf0d9;
    border-color: #d6b272;
    color: #7b581b;
  }

  .confidence.high {
    background: #191919;
    border-color: #191919;
    color: #f2cb80;
  }

  .loading-table {
    display: grid;
    gap: 8px;
  }

  .loading-row {
    animation: pulse 1.1s ease-in-out infinite;
    background: linear-gradient(90deg, #efebe3, #fbfaf7, #efebe3);
    height: 56px;
  }

  .empty-state {
    display: grid;
    gap: 8px;
    justify-items: start;
    padding: 12px 0;
  }

  @keyframes pulse {
    0%,
    100% {
      opacity: 0.65;
    }
    50% {
      opacity: 1;
    }
  }

  @media (max-width: 1100px) {
    .hero,
    .toolbar-grid {
      grid-template-columns: 1fr;
    }

    .filter-actions {
      justify-content: stretch;
    }

    .filter-actions :global(button) {
      flex: 1;
    }
  }

  @media (max-width: 720px) {
    .hero-stats {
      grid-template-columns: 1fr;
    }
  }
</style>
