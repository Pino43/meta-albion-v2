<svelte:options runes={false} />

<script lang="ts">
  import { onMount } from 'svelte';

  import { page } from '$app/stores';
  import { fetchItemFamilyDetail, fightScales, regions, type BuildComponents, type BuildSummary, type FightScaleFilter, type ItemFamilyDetail, type LeaderboardFilters } from '$lib/api';
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
  import { confidenceClass, formatCompact, formatDecimal, formatPercent, formatSignedPercent } from '$lib/format';
  import { itemImageUrl, labelForFamilyKey, parseItemType } from '$lib/item';
  import { slotLabels, type DashboardSlot } from '$lib/slots';

  type LoadState = 'loading' | 'ready' | 'error';
  type BuildComponentView = {
    slot: string;
    slotShort: string;
    itemType: string;
    label: string;
  };

  const buildSlotOrder: Array<[keyof BuildComponents, string, string]> = [
    ['head_type', 'Head', 'H'],
    ['armor_type', 'Chest', 'C'],
    ['shoes_type', 'Shoes', 'S'],
    ['main_hand_type', 'Main hand', 'MH'],
    ['off_hand_type', 'Off hand', 'OH'],
    ['cape_type', 'Cape', 'CP']
  ];

  export let data: { slot: DashboardSlot; familyKey: string };

  let initialized = false;
  let filters: LeaderboardFilters = defaultFilters();
  let draft: FilterDraft = draftFromFilters(filters);
  let detail: ItemFamilyDetail | null = null;
  let buildDetail: ItemFamilyDetail | null = null;
  let state: LoadState = 'loading';
  let buildState: LoadState = 'loading';
  let buildScale: FightScaleFilter = 'all';
  let requestId = 0;
  let buildRequestId = 0;
  const buildScaleOptions = fightScales.filter((value) => value !== 'unknown');

  $: slot = data.slot;
  $: familyKey = decodeURIComponent(data.familyKey ?? $page.params.familyKey ?? '');
  $: familyLabel = labelForFamilyKey(familyKey);
  $: detailKey = initialized ? JSON.stringify({ slot, familyKey, filters }) : '';
  $: if (detailKey) {
    void loadDetail();
  }
  $: buildDetailKey = initialized ? JSON.stringify({ slot, familyKey, filters, buildScale }) : '';
  $: if (buildDetailKey) {
    void loadBuildDetail();
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
    const current = ++requestId;
    state = 'loading';

    try {
      const result = await fetchItemFamilyDetail(slot, familyKey, detailFiltersFrom(filters));
      if (current !== requestId) return;
      detail = result.data;
      state = 'ready';
    } catch {
      if (current !== requestId) return;
      detail = null;
      state = 'error';
    }
  }

  async function loadBuildDetail() {
    const current = ++buildRequestId;
    buildState = 'loading';

    try {
      const buildFilters = {
        ...detailFiltersFrom(filters),
        fightScale: buildScale
      };
      const result = await fetchItemFamilyDetail(slot, familyKey, buildFilters);
      if (current !== buildRequestId) return;
      buildDetail = result.data;
      buildState = 'ready';
    } catch {
      if (current !== buildRequestId) return;
      buildDetail = null;
      buildState = 'error';
    }
  }

  function backHref(): string {
    const params = filtersToParams(filters).toString();
    const basePath = slot === 'main_hand' ? '/' : `/items/${slot}`;
    return `${basePath}${params ? `?${params}` : ''}`;
  }

  function buildHref(buildKey: string): string {
    const params = filtersToParams(filters).toString();
    return `/builds/${encodeURIComponent(buildKey)}${params ? `?${params}` : ''}`;
  }

  function metricsFor(summary: ItemFamilyDetail['summary']) {
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
      .map(([key, slotLabel, slotShort]) => {
        const itemType = components[key];
        if (!itemType) return null;
        return {
          slot: slotLabel,
          slotShort,
          itemType,
          label: parseItemType(itemType).label
        };
      })
      .filter((value): value is BuildComponentView => value !== null);
  }
</script>

<svelte:head>
  <title>{familyLabel} - Albion Analytics</title>
</svelte:head>

<main class="page-shell">
  <div class="crumb-row">
    <a href={backHref()}>Back to {slotLabels[slot].toLowerCase()}</a>
    <span>/</span>
    <span>{familyLabel}</span>
  </div>

  <section class="surface hero">
    <img
      alt={familyLabel}
      src={itemImageUrl(detail?.representative_item_type ?? `T4_${familyKey}`)}
      loading="lazy"
    />
    <div class="hero-copy">
      <p class="eyebrow">{slotLabels[slot]}</p>
      <h1>{familyLabel}</h1>
      <p class="hero-text">
        Family-first view. Start with the overall weapon or armor line, then compare tier variants
        below.
      </p>
      <code>{familyKey}</code>
      <span class="hero-summary">{filterSummary}</span>
    </div>
  </section>

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
        <button class="button button-muted" type="button" on:click={resetFilters}>Reset</button>
        <button class="button button-strong" type="submit">Update</button>
      </div>
    </div>
  </form>

  {#if state === 'loading'}
    <section class="surface loading-block" aria-label="Loading family detail"></section>
  {:else if state === 'error' || !detail}
    <section class="surface empty-state">
      <h2>Family detail unavailable.</h2>
      <p>The selected item family could not be loaded right now.</p>
      <button class="button button-muted" type="button" on:click={() => void loadDetail()}>Retry</button>
    </section>
  {:else}
    <section class="detail-grid">
      <div class="primary-column">
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
          <label class="inline-filter">
            Build scale
            <select bind:value={buildScale}>
              {#each buildScaleOptions as option}
                <option value={option}>{fightScaleLabel(option)}</option>
              {/each}
            </select>
          </label>
        </div>

        <div class="build-list">
          {#if buildState === 'loading'}
            <div class="build-loading" aria-label="Loading build list"></div>
          {:else if buildState === 'error' || !buildDetail}
            <div class="empty-state compact">
              <h3>Builds unavailable.</h3>
              <p>The selected build scale could not be loaded right now.</p>
              <button class="button button-muted" type="button" on:click={() => void loadBuildDetail()}>Retry</button>
            </div>
          {:else if buildDetail.builds.top_builds.length === 0}
            <p class="empty-copy">No build rows yet for this family.</p>
          {:else}
            {#each buildDetail.builds.top_builds as build}
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
              </a>
            {/each}
          {/if}
        </div>
      </section>
      </div>

      <div class="side-column">
        <section class="surface">
          <div class="section-head">
            <div>
              <p class="eyebrow">Variants</p>
              <h2>Tier breakdown</h2>
            </div>
            <span>{detail.variants.length} tracked variants</span>
          </div>

          <div class="variant-list">
            {#each detail.variants as variant}
              {@const parsed = parseItemType(variant.item_type)}
              <div class="variant-row">
                <div class="variant-copy">
                  <img alt={parsed.label} src={itemImageUrl(variant.item_type)} loading="lazy" />
                  <div>
                    <strong>{parsed.tier}{parsed.enchantment}</strong>
                    <code>{variant.item_type}</code>
                  </div>
                </div>
                <div class="variant-metrics">
                  <span>{formatSignedPercent(variant.adjusted_score)}</span>
                  <span>{formatCompact(variant.sample)}</span>
                </div>
              </div>
            {/each}
          </div>
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
      </div>
    </section>
  {/if}
</main>

<style>
  .page-shell {
    display: grid;
    gap: 16px;
  }

  .crumb-row {
    align-items: center;
    color: var(--text-soft);
    display: flex;
    flex-wrap: wrap;
    gap: 8px;
    font-size: 12px;
    margin-bottom: 6px;
  }

  .crumb-row a {
    color: var(--text);
    font-weight: 700;
    text-decoration: none;
  }

  .surface {
    background: var(--surface);
    border: 1px solid var(--line);
    padding: 20px;
  }

  .hero {
    align-items: center;
    display: grid;
    gap: 18px;
    grid-template-columns: 118px minmax(0, 1fr);
  }

  .hero img {
    height: 118px;
    object-fit: contain;
    width: 118px;
  }

  .hero-copy,
  .toolbar,
  .build-list,
  .distribution-list,
  .variant-list,
  .primary-column,
  .side-column {
    display: grid;
    gap: 12px;
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

  h1,
  h2,
  p,
  dl,
  dt,
  dd {
    margin: 0;
  }

  h1 {
    font-size: 34px;
    line-height: 1;
  }

  h2 {
    font-size: 22px;
    line-height: 1.05;
  }

  .hero-text,
  .hero-summary,
  .section-head span,
  .distribution-copy span,
  .empty-copy,
  .empty-state p,
  .build-card-copy {
    color: var(--text-soft);
    font-size: 13px;
    line-height: 1.5;
  }

  code {
    color: #756d63;
    font-family: 'IBM Plex Mono', 'Cascadia Code', Consolas, monospace;
    font-size: 10px;
    overflow-wrap: anywhere;
  }

  .toolbar-grid {
    align-items: end;
    display: grid;
    gap: 12px;
    grid-template-columns: repeat(3, minmax(0, 1fr)) auto;
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

  .loading-block {
    min-height: 240px;
  }

  .empty-state {
    display: grid;
    gap: 8px;
    justify-items: start;
  }

  .detail-grid {
    display: grid;
    gap: 16px;
    grid-template-columns: minmax(0, 1fr) minmax(340px, 440px);
  }

  .metric-strip {
    display: grid;
    gap: 0 12px;
    grid-template-columns: repeat(3, minmax(0, 1fr));
  }

  .metric-strip div {
    border-bottom: 1px solid var(--line);
    padding: 10px 0;
  }

  .metric-strip dd {
    font-size: 15px;
    font-weight: 700;
    margin-top: 4px;
  }

  .positive {
    color: #9a6810;
    font-weight: 700;
  }

  .section-head,
  .distribution-copy,
  .build-card-head,
  .variant-row,
  .variant-copy,
  .variant-metrics {
    align-items: center;
    display: flex;
    gap: 10px;
    justify-content: space-between;
  }

  .inline-filter {
    min-width: 170px;
  }

  .inline-filter select {
    min-height: 34px;
  }

  .variant-list {
    gap: 8px;
  }

  .variant-row {
    border: 1px solid var(--line);
    padding: 10px 12px;
  }

  .variant-copy {
    gap: 12px;
    justify-content: flex-start;
  }

  .variant-copy img {
    height: 52px;
    object-fit: contain;
    width: 52px;
  }

  .variant-copy div {
    display: grid;
    gap: 4px;
  }

  .variant-metrics {
    color: var(--text-soft);
    flex-wrap: wrap;
    font-size: 12px;
  }

  .build-card {
    background: var(--surface-muted);
    border: 1px solid var(--line);
    color: inherit;
    display: grid;
    gap: 10px;
    padding: 12px;
    text-decoration: none;
  }

  .build-preview {
    display: grid;
    gap: 8px;
    grid-template-columns: repeat(6, minmax(0, 1fr));
  }

  .build-piece {
    background: var(--surface);
    border: 1px solid var(--line);
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

  .bar-track {
    background: #ece7dc;
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

  .build-loading {
    animation: pulse 1.1s ease-in-out infinite;
    background: linear-gradient(90deg, #efebe3, #fbfaf7, #efebe3);
    height: 120px;
  }

  .empty-state.compact {
    padding: 0;
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

  @media (max-width: 980px) {
    .hero,
    .detail-grid,
    .metric-strip,
    .toolbar-grid {
      grid-template-columns: 1fr;
    }

    .filter-actions {
      justify-content: stretch;
    }

    .filter-actions :global(button) {
      flex: 1;
    }

    .build-preview {
      grid-template-columns: repeat(3, minmax(0, 1fr));
    }
  }
</style>
