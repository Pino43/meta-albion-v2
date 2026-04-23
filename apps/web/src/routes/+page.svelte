<script lang="ts">
  import { onMount } from 'svelte';

  import { fetchLeaderboard, type MainHandLeaderboardRow, type LeaderboardFilters } from '$lib/api';
  import {
    applyDraft,
    contentTypeLabel,
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
  import {
    confidenceClass,
    formatCompact,
    formatPercent,
    formatSignedPercent,
    formatTimestamp
  } from '$lib/format';
  import { itemImageUrl, parseItemType } from '$lib/item';
  import { contentTypes, fightScales, regions } from '$lib/api';

  type LoadState = 'loading' | 'ready' | 'error';

  let initialized = false;
  let filters: LeaderboardFilters = defaultFilters();
  let draft: FilterDraft = draftFromFilters(filters);
  let rows: MainHandLeaderboardRow[] = [];
  let state: LoadState = 'loading';
  let apiStatus: LoadState = 'loading';
  let lastUpdated: string | null = null;
  let requestId = 0;

  $: leaderboardKey = initialized ? JSON.stringify(filters) : '';
  $: if (leaderboardKey) {
    void loadLeaderboard();
  }

  $: if (initialized) {
    syncUrl();
  }

  $: filterSummary = summarizeFilters(filters);
  $: topAdjustedRow = rows[0] ?? null;
  $: topPickRow = [...rows].sort((left, right) => (right.pick_rate ?? 0) - (left.pick_rate ?? 0))[0] ?? null;
  $: totalSample = rows.reduce((sum, row) => sum + row.sample, 0);

  onMount(() => {
    const params = new URLSearchParams(window.location.search);
    const nextFilters = filtersFromParams(params);
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
    const params = filtersToParams(filters);
    const query = params.toString();
    history.replaceState(null, '', query ? `?${query}` : window.location.pathname);
  }

  async function loadLeaderboard() {
    const current = ++requestId;
    state = 'loading';
    apiStatus = 'loading';

    try {
      const result = await fetchLeaderboard(filters);
      if (current !== requestId) return;

      rows = result.data;
      lastUpdated = result.meta.generated_at ?? null;
      state = 'ready';
      apiStatus = 'ready';
    } catch {
      if (current !== requestId) return;

      rows = [];
      lastUpdated = null;
      state = 'error';
      apiStatus = 'error';
    }
  }

  function itemHref(itemType: string): string {
    const params = filtersToParams(filters).toString();
    return `/items/main_hand/${encodeURIComponent(itemType)}${params ? `?${params}` : ''}`;
  }

  function buildHref(buildKey: string): string {
    const params = filtersToParams(filters).toString();
    return `/builds/${encodeURIComponent(buildKey)}${params ? `?${params}` : ''}`;
  }
</script>

<svelte:head>
  <title>Albion Analytics Meta Lab</title>
  <meta
    name="description"
    content="Fast main-hand rankings for Albion Online with a table-first meta dashboard."
  />
</svelte:head>

<main class="page">
  <header class="surface topbar">
    <div class="title-block">
      <p class="eyebrow">Albion Analytics</p>
      <div class="title-row">
        <h1>Main-hand rankings</h1>
        <div class="header-meta">
          <span class={`status-chip ${apiStatus}`}>
            {apiStatus === 'ready'
              ? 'API connected'
              : apiStatus === 'error'
                ? 'API issue'
                : 'Checking API'}
          </span>
          <span class="status-chip neutral">Updated {formatTimestamp(lastUpdated)}</span>
        </div>
      </div>
      <p class="title-copy">
        Read the current weapon meta quickly, then open a weapon page or build page only when you
        want more detail.
      </p>
    </div>

    <dl class="snapshot-grid">
      <div class="snapshot-card">
        <dt>Adjusted leader</dt>
        <dd>{topAdjustedRow ? parseItemType(topAdjustedRow.item_type).label : 'Waiting for data'}</dd>
      </div>
      <div class="snapshot-card">
        <dt>Pick-rate leader</dt>
        <dd>{topPickRow ? parseItemType(topPickRow.item_type).label : 'Waiting for data'}</dd>
      </div>
      <div class="snapshot-card">
        <dt>Visible rows</dt>
        <dd>{rows.length}</dd>
      </div>
      <div class="snapshot-card">
        <dt>Total sample</dt>
        <dd>{formatCompact(totalSample)}</dd>
      </div>
    </dl>
  </header>

  <form class="surface toolbar" on:submit|preventDefault={applyFilters}>
    <div class="toolbar-grid">
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
        Content
        <select bind:value={draft.contentType}>
          {#each contentTypes as option}
            <option value={option}>{contentTypeLabel(option)}</option>
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
        Patch
        <input bind:value={draft.patchIdInput} inputmode="numeric" placeholder="Any" />
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
        <button class="secondary-button" type="button" on:click={resetFilters}>Reset</button>
        <button class="primary-button" type="submit">Update</button>
      </div>
    </div>

    <div class="toolbar-summary">
      <div class="summary-block">
        <span>Current slice</span>
        <strong>{filterSummary}</strong>
      </div>
      <div class="summary-block">
        <span>Page focus</span>
        <strong>Leaderboard first, detail pages on demand</strong>
      </div>
    </div>
  </form>

  <section class="surface panel">
    <header class="panel-head">
      <div>
        <p class="eyebrow">Leaderboard</p>
        <h2>Weapon table</h2>
      </div>
      <span>Open a weapon page or build page only when you want the deep view.</span>
    </header>

    {#if state === 'loading'}
      <div class="loading-table" aria-label="Loading leaderboard">
        {#each Array(10) as _}
          <div class="loading-row"></div>
        {/each}
      </div>
    {:else if state === 'error'}
      <div class="empty-state">
        <h3>API connection issue.</h3>
        <p>Ranking data could not be loaded. Please try again in a moment.</p>
        <button class="secondary-button" type="button" on:click={() => void loadLeaderboard()}>
          Retry
        </button>
      </div>
    {:else if rows.length === 0}
      <div class="empty-state">
        <h3>No rankings for this slice.</h3>
        <p>Try a broader region, a wider time range, or a lower sample gate.</p>
      </div>
    {:else}
      <div class="table-scroll">
        <table class="rank-table">
          <thead>
            <tr>
              <th class="rank-col">#</th>
              <th>Weapon</th>
              <th class="metric-col">Adjusted</th>
              <th class="metric-col">Kill-side</th>
              <th class="metric-col">Pick rate</th>
              <th class="metric-col">Sample</th>
              <th class="metric-col">Confidence</th>
              <th>Top build</th>
            </tr>
          </thead>
          <tbody>
            {#each rows as row, index}
              {@const parsed = parseItemType(row.item_type)}
              <tr>
                <td class="rank-col">{index + 1}</td>
                <td>
                  <a class="weapon-link" href={itemHref(row.item_type)}>
                    <img alt={parsed.label} src={itemImageUrl(row.item_type)} loading="lazy" />
                    <span class="weapon-copy">
                      <strong>{parsed.label}</strong>
                      <span class="weapon-meta">
                        <span class="tier-tag">{parsed.tier}{parsed.enchantment}</span>
                        <code>{row.item_type}</code>
                      </span>
                    </span>
                  </a>
                </td>
                <td class:positive={row.adjusted_score >= 0}>{formatSignedPercent(row.adjusted_score)}</td>
                <td>{formatPercent(row.kill_side_rate)}</td>
                <td>{formatPercent(row.pick_rate)}</td>
                <td>{formatCompact(row.sample)}</td>
                <td>
                  <span class={`confidence ${confidenceClass(row.confidence)}`}>{row.confidence}</span>
                </td>
                <td>
                  {#if row.top_build_key}
                    <a class="build-link" href={buildHref(row.top_build_key)}>
                      Open build
                    </a>
                  {:else}
                    <span class="empty-copy">No build data</span>
                  {/if}
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
  :global(:root) {
    --bg: #efeeea;
    --surface: #fbfaf7;
    --surface-strong: #131313;
    --surface-muted: #f3f1ec;
    --line: #d8d1c5;
    --line-strong: #252525;
    --text: #121212;
    --text-soft: #666056;
    --accent: #c6922c;
    --accent-soft: #f5e6c4;
  }

  :global(*) {
    box-sizing: border-box;
  }

  :global(body) {
    margin: 0;
    background: linear-gradient(180deg, #141414 0 96px, var(--bg) 96px 100%);
    color: var(--text);
    font-family: 'IBM Plex Sans', 'Segoe UI Variable Text', 'Segoe UI', sans-serif;
  }

  :global(button),
  :global(input),
  :global(select) {
    font: inherit;
  }

  :global(code) {
    font-family: 'IBM Plex Mono', 'Cascadia Code', Consolas, monospace;
  }

  h1,
  h2,
  h3,
  p,
  dl,
  dt,
  dd {
    margin: 0;
  }

  .page {
    display: grid;
    gap: 12px;
    margin: 0 auto;
    max-width: 1460px;
    padding: 14px;
  }

  .surface,
  .snapshot-card {
    background: var(--surface);
    border: 1px solid var(--line);
    border-radius: 4px;
  }

  .surface {
    padding: 14px;
  }

  .eyebrow,
  label,
  .snapshot-card dt {
    color: var(--text-soft);
    font-size: 11px;
    font-weight: 700;
    letter-spacing: 0.08em;
    text-transform: uppercase;
  }

  .topbar {
    background: var(--surface-strong);
    border-color: var(--line-strong);
    color: #f6f3ed;
    display: grid;
    gap: 14px;
    grid-template-columns: minmax(0, 1.4fr) minmax(0, 1fr);
    padding: 16px;
  }

  .title-block {
    display: grid;
    gap: 8px;
  }

  .title-row {
    align-items: start;
    display: flex;
    gap: 12px;
    justify-content: space-between;
  }

  .title-row h1 {
    font-size: 30px;
    letter-spacing: -0.04em;
    line-height: 1;
  }

  .title-copy {
    color: #cbc2b2;
    font-size: 13px;
    line-height: 1.5;
    max-width: 66ch;
  }

  .header-meta {
    display: flex;
    flex-wrap: wrap;
    gap: 6px;
    justify-content: flex-end;
  }

  .status-chip {
    align-items: center;
    border: 1px solid #3a352e;
    border-radius: 4px;
    display: inline-flex;
    font-size: 11px;
    font-weight: 700;
    min-height: 28px;
    padding: 0 10px;
    text-transform: uppercase;
    white-space: nowrap;
  }

  .status-chip.neutral {
    background: #1d1c1a;
    color: #d5cdbf;
  }

  .status-chip.loading {
    background: #211d16;
    border-color: #7d6330;
    color: #d9b56d;
  }

  .status-chip.ready {
    background: #1e1d18;
    border-color: #8d6d31;
    color: #efca7c;
  }

  .status-chip.error {
    background: #261816;
    border-color: #8b4d3c;
    color: #efb58b;
  }

  .snapshot-grid {
    display: grid;
    gap: 8px;
    grid-template-columns: repeat(2, minmax(0, 1fr));
  }

  .snapshot-card {
    background: #1c1b19;
    border-color: #2f2c27;
    display: grid;
    gap: 6px;
    min-height: 72px;
    padding: 12px;
  }

  .snapshot-card dt {
    color: #aea390;
  }

  .snapshot-card dd {
    color: #fffdf8;
    font-size: 16px;
    font-weight: 700;
    line-height: 1.2;
    overflow-wrap: anywhere;
  }

  .toolbar {
    display: grid;
    gap: 12px;
  }

  .toolbar-grid {
    align-items: end;
    display: grid;
    gap: 10px;
    grid-template-columns: repeat(7, minmax(0, 1fr)) auto;
  }

  label {
    display: grid;
    gap: 5px;
  }

  input,
  select {
    background: var(--surface-muted);
    border: 1px solid var(--line);
    border-radius: 4px;
    color: var(--text);
    min-height: 34px;
    padding: 0 10px;
  }

  .filter-actions {
    display: flex;
    gap: 8px;
    justify-content: flex-end;
  }

  .primary-button,
  .secondary-button {
    border-radius: 4px;
    cursor: pointer;
    font-size: 12px;
    font-weight: 700;
    min-height: 34px;
    padding: 0 12px;
  }

  .primary-button {
    background: var(--surface-strong);
    border: 1px solid var(--surface-strong);
    color: #f7f3ea;
  }

  .secondary-button {
    background: transparent;
    border: 1px solid var(--line);
    color: var(--text);
  }

  .toolbar-summary {
    border-top: 1px solid var(--line);
    display: flex;
    gap: 10px;
    justify-content: space-between;
    padding-top: 10px;
  }

  .summary-block {
    display: grid;
    gap: 4px;
  }

  .summary-block span,
  .panel-head span,
  .empty-state p,
  .empty-copy {
    color: var(--text-soft);
    font-size: 12px;
    line-height: 1.45;
    overflow-wrap: anywhere;
  }

  .summary-block strong {
    font-size: 13px;
    overflow-wrap: anywhere;
  }

  .panel-head {
    align-items: baseline;
    border-bottom: 1px solid var(--line);
    display: flex;
    gap: 8px;
    justify-content: space-between;
    padding-bottom: 10px;
  }

  .panel-head h2 {
    font-size: 20px;
    letter-spacing: -0.03em;
    line-height: 1.05;
  }

  .loading-table {
    display: grid;
    gap: 8px;
    margin-top: 12px;
  }

  .loading-row {
    animation: pulse 1.1s ease-in-out infinite;
    background: linear-gradient(90deg, #efebe3, #fbfaf7, #efebe3);
    border-radius: 4px;
    height: 54px;
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

  .empty-state {
    display: grid;
    gap: 8px;
    justify-items: start;
    padding: 18px 0 4px;
  }

  .table-scroll {
    margin-top: 10px;
    overflow: auto;
  }

  .rank-table {
    border-collapse: collapse;
    min-width: 980px;
    width: 100%;
  }

  .rank-table th,
  .rank-table td {
    border-bottom: 1px solid var(--line);
    padding: 10px 8px;
    text-align: left;
    vertical-align: middle;
  }

  .rank-table th {
    background: var(--surface);
    color: var(--text-soft);
    font-size: 11px;
    font-weight: 700;
    position: sticky;
    text-transform: uppercase;
    top: 0;
    z-index: 1;
  }

  .rank-col {
    width: 54px;
    white-space: nowrap;
  }

  .metric-col {
    width: 104px;
    white-space: nowrap;
  }

  .weapon-link {
    align-items: center;
    color: inherit;
    display: grid;
    gap: 10px;
    grid-template-columns: 42px minmax(0, 1fr);
    min-width: 0;
    text-decoration: none;
  }

  .weapon-link:hover strong,
  .build-link:hover {
    text-decoration: underline;
  }

  .weapon-link img {
    background: #f1eee7;
    border: 1px solid var(--line);
    border-radius: 4px;
    height: 42px;
    object-fit: contain;
    padding: 3px;
    width: 42px;
  }

  .weapon-copy {
    display: grid;
    gap: 4px;
    min-width: 0;
  }

  .weapon-copy strong,
  .build-link,
  .snapshot-card dd {
    overflow-wrap: anywhere;
  }

  .weapon-meta {
    align-items: center;
    display: flex;
    flex-wrap: wrap;
    gap: 6px;
  }

  .tier-tag {
    align-items: center;
    background: var(--accent-soft);
    border: 1px solid #deb970;
    border-radius: 4px;
    color: #684b17;
    display: inline-flex;
    font-size: 10px;
    font-weight: 700;
    min-height: 22px;
    padding: 0 8px;
    text-transform: uppercase;
    white-space: nowrap;
  }

  code {
    color: #847869;
    font-size: 10px;
    line-height: 1.45;
    overflow-wrap: anywhere;
  }

  .positive {
    color: #9a6810;
    font-weight: 700;
  }

  .confidence {
    align-items: center;
    border: 1px solid var(--line);
    border-radius: 4px;
    display: inline-flex;
    font-size: 10px;
    font-weight: 700;
    min-height: 24px;
    padding: 0 8px;
    text-transform: uppercase;
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

  .build-link {
    color: var(--text);
    font-size: 12px;
    font-weight: 700;
    text-decoration: none;
  }

  @media (max-width: 1240px) {
    .topbar {
      grid-template-columns: 1fr;
    }

    .toolbar-grid {
      grid-template-columns: repeat(4, minmax(0, 1fr));
    }

    .filter-actions {
      grid-column: span 4;
    }
  }

  @media (max-width: 840px) {
    .page {
      padding: 10px;
    }

    .title-row,
    .panel-head,
    .toolbar-summary {
      align-items: start;
      display: grid;
      gap: 6px;
      justify-content: start;
    }

    .header-meta {
      justify-content: flex-start;
    }

    .snapshot-grid,
    .toolbar-grid {
      grid-template-columns: 1fr;
    }

    .filter-actions {
      grid-column: auto;
      justify-content: stretch;
    }

    .filter-actions :global(button) {
      flex: 1;
    }
  }
</style>
