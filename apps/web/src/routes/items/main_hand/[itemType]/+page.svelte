<script lang="ts">
  import { page } from '$app/stores';
  import { onMount } from 'svelte';

  import { fetchItemDetail, type BuildComponents, type ItemDetail, type LeaderboardFilters } from '$lib/api';
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
    confidenceClass,
    formatCompact,
    formatDecimal,
    formatPercent,
    formatSignedPercent
  } from '$lib/format';
  import { itemImageUrl, parseItemType } from '$lib/item';
  import { fightScales, regions, type BuildSummary } from '$lib/api';

  type LoadState = 'loading' | 'ready' | 'error';
  type BuildComponentView = {
    slot: string;
    slotShort: string;
    itemType: string;
    label: string;
  };

  const buildSlotOrder: Array<[keyof BuildComponents, string, string]> = [
    ['head_type', 'Head', 'H'],
    ['armor_type', 'Armor', 'A'],
    ['shoes_type', 'Shoes', 'S'],
    ['main_hand_type', 'Main hand', 'MH'],
    ['off_hand_type', 'Off hand', 'OH'],
    ['cape_type', 'Cape', 'C']
  ];

  let initialized = false;
  let filters: LeaderboardFilters = defaultFilters();
  let draft: FilterDraft = draftFromFilters(filters);
  let detail: ItemDetail | null = null;
  let state: LoadState = 'loading';
  let requestId = 0;

  $: itemType = decodeURIComponent($page.params.itemType ?? '');
  $: parsedItem = itemType ? parseItemType(itemType) : null;
  $: detailKey = initialized ? JSON.stringify({ itemType, filters }) : '';
  $: if (detailKey) {
    void loadDetail();
  }
  $: if (initialized) {
    syncUrl();
  }
  $: filterSummary = summarizeFilters(filters);

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
    if (!itemType) return;

    const current = ++requestId;
    state = 'loading';

    try {
      const result = await fetchItemDetail('main_hand', itemType, detailFiltersFrom(filters));
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

  function buildHref(buildKey: string): string {
    const params = filtersToParams(filters).toString();
    return `/builds/${encodeURIComponent(buildKey)}${params ? `?${params}` : ''}`;
  }

  function metricsFor(summary: ItemDetail['summary']) {
    return [
      { label: 'Adjusted', value: formatSignedPercent(summary.adjusted_score), positive: summary.adjusted_score >= 0 },
      { label: 'Kill-side', value: formatPercent(summary.kill_side_rate), positive: false },
      { label: 'K/D', value: formatDecimal(summary.kd_ratio), positive: false },
      { label: 'Sample', value: formatCompact(summary.sample), positive: false },
      { label: 'Pick rate', value: formatPercent(summary.pick_rate), positive: false },
      { label: 'Avg IP', value: formatDecimal(summary.avg_item_power, 0), positive: false }
    ];
  }

  function buildMetrics(build: BuildSummary) {
    return `${formatSignedPercent(build.adjusted_score)} adjusted / ${formatCompact(build.sample)} sample`;
  }

  function buildComponents(components: BuildComponents | undefined): BuildComponentView[] {
    if (!components) return [];

    return buildSlotOrder
      .map(([key, slot, slotShort]) => {
        const itemType = components[key];
        if (!itemType) return null;
        return {
          slot,
          slotShort,
          itemType,
          label: parseItemType(itemType).label
        };
      })
      .filter((value): value is BuildComponentView => value !== null);
  }

</script>

<svelte:head>
  <title>{parsedItem ? `${parsedItem.label} - Albion Analytics` : 'Weapon detail - Albion Analytics'}</title>
</svelte:head>

<main class="page">
  <div class="crumb-row">
    <a class="crumb-link" href={backHref()}>Back to rankings</a>
    <span>/</span>
    <span>{parsedItem ? parsedItem.label : 'Weapon detail'}</span>
  </div>

  <header class="surface hero">
    {#if parsedItem}
      <img alt={parsedItem.label} src={itemImageUrl(itemType)} loading="lazy" />
      <div class="hero-copy">
        <p class="eyebrow">Weapon detail</p>
        <div class="hero-title">
          <h1>{parsedItem.label}</h1>
          <span class="tier-tag">{parsedItem.tier}{parsedItem.enchantment}</span>
        </div>
        <p class="hero-subtitle">{filterSummary}</p>
        <code>{itemType}</code>
      </div>
    {/if}
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
    <section class="surface loading-block" aria-label="Loading item detail"></section>
  {:else if state === 'error' || !detail}
    <section class="surface empty-state">
      <h2>Weapon detail unavailable.</h2>
      <p>The selected weapon could not be loaded right now.</p>
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
            <p class="eyebrow">Builds</p>
            <h2>Top combinations</h2>
          </div>
          <span>Move into a full build page when you want the whole loadout.</span>
        </div>
        <div class="build-list">
          {#if detail.builds.top_builds.length === 0}
            <p class="empty-copy">No build rows yet for this weapon.</p>
          {:else}
            {#each detail.builds.top_builds as build}
              {@const previewComponents = buildComponents(build.components)}
              <a class="build-card" href={buildHref(build.build_key)}>
                <div class="build-card-head">
                  <strong>Build preview</strong>
                  <span class={`confidence ${confidenceClass(build.confidence)}`}>{build.confidence}</span>
                </div>
                <p class="build-card-copy">{buildMetrics(build)}</p>

                {#if previewComponents.length > 0}
                  <div class="build-preview" aria-label="Build loadout preview">
                    {#each previewComponents as component}
                      <div
                        class="build-piece"
                        aria-label={`${component.slot}: ${component.label}`}
                        title={`${component.slot}: ${component.label}`}
                      >
                        <img alt={component.label} src={itemImageUrl(component.itemType)} loading="lazy" />
                        <span>{component.slotShort}</span>
                      </div>
                    {/each}
                  </div>
                {/if}

                <div class="build-card-footer">
                  <span>{previewComponents.length} pieces</span>
                  <code>{build.build_key}</code>
                </div>
              </a>
            {/each}
          {/if}
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
              <strong>{fightScaleLabel((row.fight_scale as typeof fightScales[number] | undefined) ?? 'unknown')}</strong>
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
    border-radius: 4px;
    padding: 14px;
  }

  .hero {
    align-items: center;
    display: grid;
    gap: 14px;
    grid-template-columns: 112px minmax(0, 1fr);
  }

  .hero img {
    height: 112px;
    object-fit: contain;
    width: 112px;
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

  .hero-title {
    align-items: center;
    display: flex;
    flex-wrap: wrap;
    gap: 8px;
  }

  .hero-title h1 {
    font-size: 30px;
    letter-spacing: -0.04em;
    line-height: 1;
  }

  .hero-subtitle,
  .section-head span,
  .distribution-copy span,
  .empty-copy,
  .empty-state p {
    color: var(--text-soft);
    font-size: 12px;
    line-height: 1.45;
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

  .build-list,
  .distribution-list {
    display: grid;
    gap: 8px;
  }

  .build-card {
    background: var(--surface-muted);
    border: 1px solid var(--line);
    border-radius: 4px;
    color: inherit;
    display: grid;
    gap: 8px;
    padding: 10px;
    text-decoration: none;
  }

  .build-card:hover strong {
    text-decoration: underline;
  }

  .build-card-copy {
    color: var(--text-soft);
    font-size: 12px;
    line-height: 1.45;
  }

  .build-card-head,
  .distribution-copy {
    align-items: baseline;
    display: flex;
    gap: 8px;
    justify-content: space-between;
  }

  .build-preview {
    display: grid;
    gap: 8px;
    grid-template-columns: repeat(6, minmax(0, 1fr));
  }

  .build-piece {
    background: var(--surface);
    border: 1px solid var(--line);
    border-radius: 4px;
    display: grid;
    min-height: 64px;
    padding: 6px;
    place-items: center;
    position: relative;
  }

  .build-piece img {
    height: 50px;
    object-fit: contain;
    width: 50px;
  }

  .build-piece span {
    background: rgba(19, 19, 19, 0.92);
    border-radius: 3px;
    color: #f7f3ea;
    font-size: 9px;
    font-weight: 700;
    left: 4px;
    line-height: 1;
    padding: 3px 4px;
    position: absolute;
    text-transform: uppercase;
    top: 4px;
  }

  .build-card-footer {
    align-items: center;
    display: flex;
    gap: 8px;
    justify-content: space-between;
  }

  .build-card-footer span {
    color: var(--text-soft);
    font-size: 11px;
    font-weight: 700;
    letter-spacing: 0.04em;
    text-transform: uppercase;
  }

  .distribution-row {
    display: grid;
    gap: 6px;
  }

  .bar-track {
    background: #ece7dc;
    border-radius: 2px;
    height: 8px;
    overflow: hidden;
  }

  .bar-track span {
    background: linear-gradient(90deg, #453011, var(--accent));
    display: block;
    height: 100%;
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

  @media (max-width: 980px) {
    .content-grid,
    .metric-strip,
    .toolbar-grid {
      grid-template-columns: 1fr;
    }

    .build-preview {
      grid-template-columns: repeat(3, minmax(0, 1fr));
    }

    .filter-actions {
      justify-content: stretch;
    }

    .filter-actions :global(button) {
      flex: 1;
    }
  }
</style>
