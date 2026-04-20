<script lang="ts">
  import { onMount } from 'svelte';

  import {
    fetchRankings,
    perspectives,
    regions,
    slots,
    type BuildRanking,
    type ItemRanking,
    type RankingFilters,
    type RankingMeta,
    type RankingMode
  } from '$lib/api';
  import { itemImageUrl, mainItemFromBuildKey, parseItemType } from '$lib/item';

  const dayOptions = [1, 7, 30];
  const limitOptions = [10, 20, 50, 100];

  let filters: RankingFilters = {
    mode: 'items',
    slot: 'main_hand',
    days: 7,
    region: 'all',
    perspective: 'killer',
    limit: 20
  };
  let rows: Array<ItemRanking | BuildRanking> = [];
  let meta: RankingMeta | null = null;
  let loading = true;
  let error = '';
  let initialized = false;
  $: queryKey = JSON.stringify(filters);

  $: if (initialized && queryKey) {
    void load();
  }

  onMount(() => {
    const params = new URLSearchParams(window.location.search);
    filters = {
      mode: readChoice(params.get('mode'), ['items', 'builds'], filters.mode),
      slot: readChoice(params.get('slot'), slots, filters.slot),
      days: readNumber(params.get('days'), dayOptions, filters.days),
      region: readChoice(params.get('region'), regions, filters.region),
      perspective: readChoice(params.get('perspective'), perspectives, filters.perspective),
      limit: readNumber(params.get('limit'), limitOptions, filters.limit)
    };
    initialized = true;
  });

  function readChoice<T extends string>(value: string | null, allowed: readonly T[], fallback: T): T {
    return allowed.includes(value as T) ? (value as T) : fallback;
  }

  function readNumber(value: string | null, allowed: readonly number[], fallback: number): number {
    const parsed = Number(value);
    return allowed.includes(parsed) ? parsed : fallback;
  }

  async function load() {
    const current = { ...filters };
    loading = true;
    error = '';
    updateUrl(current);
    try {
      const result = await fetchRankings(current);
      rows = result.data;
      meta = result.meta;
    } catch (err) {
      rows = [];
      meta = null;
      error = err instanceof Error ? err.message : 'Unable to load rankings';
    } finally {
      loading = false;
    }
  }

  function updateUrl(current: RankingFilters) {
    const params = new URLSearchParams({
      mode: current.mode,
      days: String(current.days),
      perspective: current.perspective,
      limit: String(current.limit)
    });
    if (current.mode === 'items') {
      params.set('slot', current.slot);
    }
    if (current.region !== 'all') {
      params.set('region', current.region);
    }
    history.replaceState(null, '', `?${params.toString()}`);
  }

  function setMode(mode: RankingMode) {
    filters = { ...filters, mode };
  }

  function itemForRow(row: ItemRanking | BuildRanking): string | null {
    if ('item_type' in row) {
      return row.item_type;
    }
    return mainItemFromBuildKey(row.build_key);
  }

  function formatNumber(value: number | null | undefined): string {
    if (value === null || value === undefined) return '-';
    return new Intl.NumberFormat('en-US', { maximumFractionDigits: 1 }).format(value);
  }

  function formatFame(value: number): string {
    return new Intl.NumberFormat('en-US', { notation: 'compact' }).format(value);
  }
</script>

<svelte:head>
  <title>Albion Analytics</title>
  <meta
    name="description"
    content="Recent Albion Online item and build rankings by region and perspective."
  />
</svelte:head>

<main class="page-shell">
  <section class="toolbar" aria-label="Ranking filters">
    <div class="brand">
      <span class="brand-mark">AA</span>
      <div>
        <p class="eyebrow">Albion Analytics</p>
        <h1>Recent Meta Rankings</h1>
      </div>
    </div>

    <div class="mode-switch" aria-label="Ranking mode">
      <button class:active={filters.mode === 'items'} on:click={() => setMode('items')}>Items</button>
      <button class:active={filters.mode === 'builds'} on:click={() => setMode('builds')}>Builds</button>
    </div>

    <label>
      Region
      <select bind:value={filters.region}>
        {#each regions as region}
          <option value={region}>{region === 'all' ? 'All regions' : region}</option>
        {/each}
      </select>
    </label>

    <label>
      Days
      <select bind:value={filters.days}>
        {#each dayOptions as days}
          <option value={days}>{days}</option>
        {/each}
      </select>
    </label>

    <label>
      Perspective
      <select bind:value={filters.perspective}>
        {#each perspectives as perspective}
          <option value={perspective}>{perspective}</option>
        {/each}
      </select>
    </label>

    {#if filters.mode === 'items'}
      <label>
        Slot
        <select bind:value={filters.slot}>
          {#each slots as slot}
            <option value={slot}>{slot.replaceAll('_', ' ')}</option>
          {/each}
        </select>
      </label>
    {/if}

    <label>
      Limit
      <select bind:value={filters.limit}>
        {#each limitOptions as limit}
          <option value={limit}>{limit}</option>
        {/each}
      </select>
    </label>
  </section>

  <section class="summary" aria-live="polite">
    <div>
      <strong>{filters.mode === 'items' ? 'Item usage' : 'Build usage'}</strong>
      <span>
        {filters.perspective} perspective, {filters.region === 'all' ? 'all regions' : filters.region},
        last {filters.days} day{filters.days > 1 ? 's' : ''}
      </span>
    </div>
    {#if meta?.generated_at}
      <time datetime={meta.generated_at}>Updated {new Date(meta.generated_at).toLocaleTimeString()}</time>
    {/if}
  </section>

  <section class="ranking-surface">
    {#if loading}
      <div class="loading-grid" aria-label="Loading rankings">
        {#each Array(8) as _}
          <div class="loading-row"></div>
        {/each}
      </div>
    {:else if error}
      <div class="empty-state">
        <h2>Rankings are taking a breather.</h2>
        <p>{error}</p>
      </div>
    {:else if rows.length === 0}
      <div class="empty-state">
        <h2>No rankings yet.</h2>
        <p>Try another region, perspective, or time window.</p>
      </div>
    {:else}
      <table>
        <thead>
          <tr>
            <th>Rank</th>
            <th>{filters.mode === 'items' ? 'Item' : 'Build'}</th>
            <th>Uses</th>
            <th>Events</th>
            <th>Avg IP</th>
            <th>Avg Players</th>
            <th>Kill Fame</th>
          </tr>
        </thead>
        <tbody>
          {#each rows as row, index}
            {@const itemType = itemForRow(row)}
            {@const parsed = itemType ? parseItemType(itemType) : null}
            <tr>
              <td class="rank">#{index + 1}</td>
              <td>
                <div class="entity">
                  {#if itemType}
                    <img src={itemImageUrl(itemType)} alt="" loading="lazy" />
                  {/if}
                  <div>
                    <strong>{'item_type' in row ? parsed?.label : row.build_key}</strong>
                    <span>
                      {'item_type' in row
                        ? `${parsed?.tier ?? ''}${parsed?.enchantment ?? ''} - ${row.item_type}`
                        : itemType ?? 'mixed build'}
                    </span>
                  </div>
                </div>
              </td>
              <td>{formatNumber(row.uses)}</td>
              <td>{formatNumber(row.events)}</td>
              <td>{formatNumber(row.avg_item_power)}</td>
              <td>{formatNumber(row.avg_participants)}</td>
              <td>{formatFame(row.total_kill_fame)}</td>
            </tr>
          {/each}
        </tbody>
      </table>
    {/if}
  </section>
</main>

<style>
  :global(*) {
    box-sizing: border-box;
  }

  :global(body) {
    margin: 0;
    background: #f4f7f3;
    color: #101010;
    font-family:
      Inter, ui-sans-serif, system-ui, -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;
  }

  :global(button),
  :global(select) {
    font: inherit;
  }

  .page-shell {
    min-height: 100vh;
    padding: 24px;
  }

  .toolbar {
    align-items: end;
    display: grid;
    gap: 14px;
    grid-template-columns: minmax(260px, 1fr) repeat(5, minmax(120px, auto));
    margin: 0 auto 18px;
    max-width: 1280px;
  }

  .brand {
    align-items: center;
    display: flex;
    gap: 14px;
  }

  .brand-mark {
    align-items: center;
    background: #101010;
    border-radius: 8px;
    color: #dbf264;
    display: inline-flex;
    font-weight: 800;
    height: 52px;
    justify-content: center;
    width: 52px;
  }

  .eyebrow {
    color: #4b6357;
    font-size: 13px;
    font-weight: 700;
    margin: 0 0 3px;
    text-transform: uppercase;
  }

  h1 {
    font-size: 26px;
    line-height: 1.15;
    margin: 0;
  }

  label {
    color: #40554b;
    display: grid;
    font-size: 13px;
    font-weight: 700;
    gap: 6px;
  }

  select,
  .mode-switch,
  .ranking-surface,
  .summary {
    background: #ffffff;
    border: 1px solid #d8e0db;
    border-radius: 8px;
  }

  select {
    color: #101010;
    min-height: 40px;
    padding: 0 10px;
  }

  .mode-switch {
    display: flex;
    min-height: 40px;
    padding: 3px;
  }

  .mode-switch button {
    background: transparent;
    border: 0;
    border-radius: 6px;
    color: #40554b;
    cursor: pointer;
    font-weight: 800;
    padding: 0 14px;
  }

  .mode-switch button.active {
    background: #dbf264;
    color: #101010;
  }

  .summary,
  .ranking-surface {
    margin: 0 auto;
    max-width: 1280px;
  }

  .summary {
    align-items: center;
    display: flex;
    justify-content: space-between;
    margin-bottom: 12px;
    padding: 14px 16px;
  }

  .summary div {
    display: grid;
    gap: 4px;
  }

  .summary span,
  .summary time {
    color: #5f6f68;
    font-size: 14px;
  }

  .ranking-surface {
    overflow-x: auto;
  }

  table {
    border-collapse: collapse;
    min-width: 920px;
    width: 100%;
  }

  th,
  td {
    border-bottom: 1px solid #e4e9e6;
    padding: 13px 14px;
    text-align: left;
    vertical-align: middle;
  }

  th {
    color: #4b6357;
    font-size: 12px;
    text-transform: uppercase;
  }

  td {
    font-size: 14px;
  }

  .rank {
    color: #e14b4b;
    font-weight: 800;
    width: 76px;
  }

  .entity {
    align-items: center;
    display: flex;
    gap: 12px;
    min-width: 360px;
  }

  .entity img {
    background: #eef3ef;
    border: 1px solid #d8e0db;
    border-radius: 8px;
    height: 48px;
    object-fit: contain;
    padding: 3px;
    width: 48px;
  }

  .entity div {
    display: grid;
    gap: 4px;
  }

  .entity strong {
    max-width: 560px;
    overflow-wrap: anywhere;
  }

  .entity span {
    color: #5f6f68;
    font-size: 12px;
    overflow-wrap: anywhere;
  }

  .loading-grid {
    display: grid;
    gap: 8px;
    padding: 14px;
  }

  .loading-row {
    animation: pulse 1.2s ease-in-out infinite;
    background: linear-gradient(90deg, #edf2ee, #ffffff, #edf2ee);
    border-radius: 8px;
    height: 54px;
  }

  .empty-state {
    padding: 40px 18px;
    text-align: center;
  }

  .empty-state h2 {
    margin: 0 0 8px;
  }

  .empty-state p {
    color: #5f6f68;
    margin: 0;
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

  @media (max-width: 900px) {
    .page-shell {
      padding: 14px;
    }

    .toolbar {
      grid-template-columns: 1fr 1fr;
    }

    .brand {
      grid-column: 1 / -1;
    }

    .summary {
      align-items: start;
      display: grid;
      gap: 8px;
    }
  }
</style>
