<script lang="ts">
  import { page } from '$app/stores';
  import { onMount } from 'svelte';

  import { fetchBuildDetail, type BuildComponents, type BuildDetail, type DistributionRow, type LeaderboardFilters } from '$lib/api';
  import {
    applyDraft,
    dayOptions,
    defaultFilters,
    detailFiltersFrom,
    draftFromFilters,
    filtersFromParams,
    filtersToParams,
    fightScaleLabel,
    regionLabel,
    summarizeFilters,
    type FilterDraft
  } from '$lib/filters';
  import {
    formatCompact,
    formatDecimal,
    formatPercent,
    formatSignedPercent
  } from '$lib/format';
  import { familyKeyFromItemType, itemImageUrl, mainItemFromBuildKey, parseItemType } from '$lib/item';
  import { fightScales, regions } from '$lib/api';

  type LoadState = 'loading' | 'ready' | 'error';
  type ComponentView = {
    slot: string;
    itemType: string;
    label: string;
  };

  const buildSlotOrder: Array<[keyof BuildComponents, string]> = [
    ['head_type', 'Head'],
    ['armor_type', 'Armor'],
    ['shoes_type', 'Shoes'],
    ['main_hand_type', 'Main hand'],
    ['off_hand_type', 'Off hand'],
    ['cape_type', 'Cape']
  ];

  let initialized = false;
  let filters: LeaderboardFilters = defaultFilters();
  let draft: FilterDraft = draftFromFilters(filters);
  let detail: BuildDetail | null = null;
  let state: LoadState = 'loading';
  let requestId = 0;

  $: buildKey = decodeURIComponent($page.params.buildKey ?? '');
  $: detailKey = initialized ? JSON.stringify({ buildKey, filters }) : '';
  $: if (detailKey) {
    void loadDetail();
  }
  $: if (initialized) {
    syncUrl();
  }
  $: filterSummary = summarizeFilters(filters);
  $: mainHandItemType = detail ? detail.components.main_hand_type : mainItemFromBuildKey(buildKey);
  $: mainHandHref = itemHref(mainHandItemType);
  $: buildComponentViews = detail ? buildComponents(detail.components) : [];

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
    const params = filtersToParams(filters).toString();
    history.replaceState(null, '', `${window.location.pathname}${params ? `?${params}` : ''}`);
  }

  async function loadDetail() {
    if (!buildKey) return;

    const current = ++requestId;
    state = 'loading';

    try {
      const result = await fetchBuildDetail(buildKey, detailFiltersFrom(filters));
      if (current !== requestId) return;
      detail = result.data;
      state = 'ready';
    } catch {
      if (current !== requestId) return;
      detail = null;
      state = 'error';
    }
  }

  function backHref(): string {
    const params = filtersToParams(filters).toString();
    return `/${params ? `?${params}` : ''}`;
  }

  function itemHref(itemType: string | null): string | null {
    if (!itemType) return null;
    const params = filtersToParams(filters).toString();
    return `/families/main_hand/${encodeURIComponent(familyKeyFromItemType(itemType))}${params ? `?${params}` : ''}`;
  }

  function metricsFor(summary: BuildDetail['summary']) {
    return [
      { label: 'Adjusted', value: formatSignedPercent(summary.adjusted_score), positive: summary.adjusted_score >= 0 },
      { label: 'Kill-side', value: formatPercent(summary.kill_side_rate), positive: false },
      { label: 'K/D', value: formatDecimal(summary.kd_ratio), positive: false },
      { label: 'Sample', value: formatCompact(summary.sample), positive: false },
      { label: 'Pick rate', value: formatPercent(summary.pick_rate), positive: false },
      { label: 'Avg IP', value: formatDecimal(summary.avg_item_power, 0), positive: false }
    ];
  }

  function distributionLabel(row: DistributionRow): string {
    return fightScaleLabel((row.fight_scale as typeof fightScales[number] | undefined) ?? 'unknown');
  }

  function buildComponents(components: BuildComponents): ComponentView[] {
    return buildSlotOrder
      .map(([key, slot]) => {
        const itemType = components[key];
        if (!itemType) return null;
        return {
          slot,
          itemType,
          label: parseItemType(itemType).label
        };
      })
      .filter((value): value is ComponentView => value !== null);
  }
</script>

<svelte:head>
  <title>Build detail - Albion Analytics</title>
</svelte:head>

<main class="page">
  <div class="crumb-row">
    <a class="crumb-link" href={backHref()}>Back to rankings</a>
    {#if mainHandHref}
      <span>/</span>
      <a class="crumb-link" href={mainHandHref}>Weapon page</a>
    {/if}
    <span>/</span>
    <span>Build detail</span>
  </div>

  <header class="surface hero">
    <div class="hero-copy">
      <p class="eyebrow">Build detail</p>
      <div class="hero-title">
        <h1>{mainHandItemType ? parseItemType(mainHandItemType).label : 'Build breakdown'}</h1>
      </div>
      <p class="hero-subtitle">{filterSummary}</p>
      <code>{buildKey}</code>
    </div>
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
        Scale
        <select bind:value={draft.fightScale}>
          {#each fightScales as option}
            <option value={option}>{fightScaleLabel(option)}</option>
          {/each}
        </select>
      </label>

      <div class="filter-actions">
        <button class="secondary-button" type="button" on:click={resetFilters}>Reset</button>
        <button class="primary-button" type="submit">Update</button>
      </div>
    </div>
  </form>

  {#if state === 'loading'}
    <section class="surface loading-block" aria-label="Loading build detail"></section>
  {:else if state === 'error' || !detail}
    <section class="surface empty-state">
      <h2>Build detail unavailable.</h2>
      <p>The selected build could not be loaded right now.</p>
      <button class="secondary-button" type="button" on:click={() => void loadDetail()}>Retry</button>
    </section>
  {:else}
    <section class="content-grid">
      <section class="surface">
        <p class="eyebrow">Summary</p>
        <dl class="metric-strip">
          {#each metricsFor(detail.summary) as metric}
            <div>
              <dt>{metric.label}</dt>
              <dd class:positive={metric.positive}>{metric.value}</dd>
            </div>
          {/each}
        </dl>
      </section>

      <section class="surface">
        <div class="section-head">
          <div>
            <p class="eyebrow">Pieces</p>
            <h2>Loadout</h2>
          </div>
          <span>{buildComponentViews.length} tracked slots</span>
        </div>

        <div class="component-grid">
          {#each buildComponentViews as component}
            <div class="component-tile">
              <img alt={component.label} src={itemImageUrl(component.itemType)} loading="lazy" />
              <strong>{component.slot}</strong>
              <span>{component.label}</span>
              <code>{component.itemType}</code>
            </div>
          {/each}
        </div>
      </section>
    </section>

    <section class="surface">
      <div class="section-head">
        <div>
          <p class="eyebrow">Distribution</p>
          <h2>Fight scale split</h2>
        </div>
      </div>

      <div class="distribution-list">
        {#each detail.distributions.by_fight_scale as row}
          <div class="distribution-row">
            <div class="distribution-copy">
              <strong>{distributionLabel(row)}</strong>
              <span>{formatPercent(row.kill_side_rate)} / {formatCompact(row.sample)} sample</span>
            </div>
            <div class="bar-track">
              <span style={`width: ${Math.max(row.kill_side_rate * 100, 3)}%`}></span>
            </div>
          </div>
        {/each}
      </div>
    </section>
  {/if}
</main>

<style>
  :global(:root) {
    --bg: #efeeea;
    --surface: #fbfaf7;
    --surface-muted: #f3f1ec;
    --line: #d8d1c5;
    --text: #121212;
    --text-soft: #666056;
    --surface-strong: #131313;
    --accent: #c6922c;
    --accent-soft: #f5e6c4;
  }

  :global(*) {
    box-sizing: border-box;
  }

  :global(body) {
    margin: 0;
    background: var(--bg);
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
    max-width: var(--page-width);
    padding: 18px 14px 24px;
  }

  .crumb-row {
    align-items: center;
    color: var(--text-soft);
    display: flex;
    flex-wrap: wrap;
    gap: 8px;
    font-size: 12px;
  }

  .crumb-link {
    color: var(--text);
    font-weight: 700;
    text-decoration: none;
  }

  .surface {
    background: var(--surface);
    border: 1px solid var(--line);
    padding: 14px;
  }

  .hero {
    display: grid;
    gap: 8px;
  }

  .hero-copy {
    display: grid;
    gap: 6px;
  }

  .eyebrow,
  label,
  .metric-strip dt {
    color: var(--text-soft);
    font-size: 11px;
    font-weight: 700;
    letter-spacing: 0.08em;
    text-transform: uppercase;
  }

  .hero-title h1 {
    font-size: 30px;
    letter-spacing: -0.04em;
    line-height: 1;
  }

  .hero-subtitle,
  .section-head span,
  .distribution-copy span,
  .empty-state p {
    color: var(--text-soft);
    font-size: 12px;
    line-height: 1.45;
  }

  code {
    color: #847869;
    font-size: 10px;
    line-height: 1.45;
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
    grid-template-columns: repeat(3, minmax(0, 1fr)) auto;
  }

  label {
    display: grid;
    gap: 5px;
  }

  select {
    background: var(--surface-muted);
    border: 1px solid var(--line);
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

  .loading-block {
    min-height: 240px;
  }

  .empty-state {
    display: grid;
    gap: 8px;
    justify-items: start;
  }

  .content-grid {
    display: grid;
    gap: 12px;
    grid-template-columns: minmax(0, 1fr) minmax(320px, 420px);
  }

  .metric-strip {
    display: grid;
    gap: 0 10px;
    grid-template-columns: repeat(3, minmax(0, 1fr));
  }

  .metric-strip div {
    border-bottom: 1px solid var(--line);
    padding: 10px 0;
  }

  .metric-strip dd {
    font-size: 15px;
    font-weight: 700;
    margin-top: 3px;
  }

  .positive {
    color: #9a6810;
    font-weight: 700;
  }

  .section-head {
    align-items: baseline;
    display: flex;
    gap: 8px;
    justify-content: space-between;
    margin-bottom: 10px;
  }

  .section-head h2 {
    font-size: 20px;
    letter-spacing: -0.03em;
    line-height: 1.05;
  }

  .component-grid,
  .distribution-list {
    display: grid;
    gap: 8px;
  }

  .component-grid {
    grid-template-columns: repeat(2, minmax(0, 1fr));
  }

  .component-tile {
    background: var(--surface-muted);
    border: 1px solid var(--line);
    display: grid;
    gap: 6px;
    justify-items: start;
    min-height: 132px;
    padding: 10px;
  }

  .component-tile img {
    height: 58px;
    object-fit: contain;
    width: 58px;
  }

  .distribution-row {
    display: grid;
    gap: 6px;
  }

  .distribution-copy {
    align-items: baseline;
    display: flex;
    gap: 8px;
    justify-content: space-between;
  }

  .bar-track {
    background: #ece7dc;
    height: 8px;
    overflow: hidden;
  }

  .bar-track span {
    background: linear-gradient(90deg, #453011, #c6922c);
    display: block;
    height: 100%;
  }

  @media (max-width: 980px) {
    .content-grid,
    .metric-strip,
    .toolbar-grid,
    .component-grid {
      grid-template-columns: 1fr;
    }

    .filter-actions {
      justify-content: stretch;
    }

    .filter-actions :global(button) {
      flex: 1;
    }
  }
</style>
