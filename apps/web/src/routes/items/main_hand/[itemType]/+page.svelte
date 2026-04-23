<script lang="ts">
  import { page } from '$app/stores';
  import { onMount } from 'svelte';

  import { fetchItemDetail, type ItemDetail, type LeaderboardFilters } from '$lib/api';
  import {
    applyDraft,
    contentTypeLabel,
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
  import { contentTypes, fightScales, regions, type BuildSummary, type DistributionRow } from '$lib/api';

  type LoadState = 'loading' | 'ready' | 'error';

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

  function distributionLabel(row: DistributionRow, kind: 'content' | 'scale' | 'patch'): string {
    if (kind === 'content') {
      return contentTypeLabel((row.content_type as typeof contentTypes[number] | undefined) ?? 'unknown');
    }
    if (kind === 'scale') {
      return fightScaleLabel((row.fight_scale as typeof fightScales[number] | undefined) ?? 'unknown');
    }
    if (row.patch_id === null || row.patch_id === undefined) {
      return 'Unpatched';
    }
    return `Patch ${row.patch_id}`;
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
              <a class="build-card" href={buildHref(build.build_key)}>
                <div class="build-card-head">
                  <strong>{build.components?.main_hand_type ? parseItemType(build.components.main_hand_type).label : 'Build'}</strong>
                  <span class={`confidence ${confidenceClass(build.confidence)}`}>{build.confidence}</span>
                </div>
                <p>{buildMetrics(build)}</p>
                <code>{build.build_key}</code>
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
          <h2>Where this weapon performs</h2>
        </div>
      </div>

      <div class="distribution-grid">
        <div>
          <h3>Content</h3>
          <div class="distribution-list">
            {#each detail.distributions.by_content_type as row}
              <div class="distribution-row">
                <div class="distribution-copy">
                  <strong>{distributionLabel(row, 'content')}</strong>
                  <span>{formatPercent(row.kill_side_rate)} / {formatCompact(row.sample)} sample</span>
                </div>
                <div class="bar-track">
                  <span style={`width: ${Math.max(row.kill_side_rate * 100, 3)}%`}></span>
                </div>
              </div>
            {/each}
          </div>
        </div>

        <div>
          <h3>Scale</h3>
          <div class="distribution-list">
            {#each detail.distributions.by_fight_scale as row}
              <div class="distribution-row">
                <div class="distribution-copy">
                  <strong>{distributionLabel(row, 'scale')}</strong>
                  <span>{formatPercent(row.kill_side_rate)} / {formatCompact(row.sample)} sample</span>
                </div>
                <div class="bar-track">
                  <span style={`width: ${Math.max(row.kill_side_rate * 100, 3)}%`}></span>
                </div>
              </div>
            {/each}
          </div>
        </div>

        <div>
          <h3>Patch</h3>
          <div class="distribution-list">
            {#each detail.distributions.by_patch as row}
              <div class="distribution-row">
                <div class="distribution-copy">
                  <strong>{distributionLabel(row, 'patch')}</strong>
                  <span>{formatPercent(row.kill_side_rate)} / {formatCompact(row.sample)} sample</span>
                </div>
                <div class="bar-track">
                  <span style={`width: ${Math.max(row.kill_side_rate * 100, 3)}%`}></span>
                </div>
              </div>
            {/each}
          </div>
        </div>
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
    max-width: 1280px;
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
    grid-template-columns: 72px minmax(0, 1fr);
  }

  .hero img {
    background: #f1eee7;
    border: 1px solid var(--line);
    border-radius: 4px;
    height: 72px;
    object-fit: contain;
    padding: 4px;
    width: 72px;
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
    grid-template-columns: repeat(5, minmax(0, 1fr)) auto;
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
    gap: 6px;
    padding: 10px;
    text-decoration: none;
  }

  .build-card:hover strong {
    text-decoration: underline;
  }

  .build-card-head,
  .distribution-copy {
    align-items: baseline;
    display: flex;
    gap: 8px;
    justify-content: space-between;
  }

  .distribution-grid {
    display: grid;
    gap: 12px;
    grid-template-columns: repeat(3, minmax(0, 1fr));
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
    .distribution-grid,
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
  }
</style>
