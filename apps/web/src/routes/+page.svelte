<script lang="ts">
  import { onMount } from 'svelte';

  import {
    contentTypes,
    fetchBuildDetail,
    fetchItemDetail,
    fetchLeaderboard,
    fightScales,
    regions,
    type BuildComponents,
    type BuildDetail,
    type BuildSummary,
    type Confidence,
    type ContentTypeFilter,
    type DetailFilters,
    type DistributionRow,
    type FightScaleFilter,
    type ItemDetail,
    type LeaderboardFilters,
    type MainHandLeaderboardRow,
    type Region
  } from '$lib/api';
  import { itemImageUrl, parseItemType } from '$lib/item';

  type LoadState = 'idle' | 'loading' | 'ready' | 'error';

  type FilterDraft = {
    days: number;
    region: Region;
    patchIdInput: string;
    contentType: ContentTypeFilter;
    fightScale: FightScaleFilter;
    limit: number;
    minSample: number;
  };

  type ComponentView = {
    slot: string;
    itemType: string;
    label: string;
  };

  const dayOptions = [1, 7, 14, 30] as const;
  const limitOptions = [10, 20, 50, 100] as const;
  const minSampleOptions = [0, 25, 100, 250] as const;
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
  let leaderboardRows: MainHandLeaderboardRow[] = [];
  let selectedItemType: string | null = null;
  let selectedBuildKey: string | null = null;
  let itemDetail: ItemDetail | null = null;
  let buildDetail: BuildDetail | null = null;
  let leaderboardState: LoadState = 'loading';
  let itemState: LoadState = 'idle';
  let buildState: LoadState = 'idle';
  let apiStatus: LoadState = 'loading';
  let lastUpdated: string | null = null;
  let leaderboardRequestId = 0;
  let itemRequestId = 0;
  let buildRequestId = 0;

  $: leaderboardKey = initialized ? JSON.stringify(filters) : '';
  $: if (leaderboardKey) {
    void loadLeaderboard();
  }

  $: itemKey = initialized && selectedItemType ? JSON.stringify({ filters, selectedItemType }) : '';
  $: if (itemKey) {
    void loadItemDetail();
  } else if (initialized) {
    itemDetail = null;
    itemState = 'idle';
  }

  $: buildKeyQuery =
    initialized && selectedBuildKey ? JSON.stringify({ filters, selectedBuildKey }) : '';
  $: if (buildKeyQuery) {
    void loadBuildDetail();
  } else if (initialized) {
    buildDetail = null;
    buildState = 'idle';
  }

  $: urlState =
    initialized && JSON.stringify({ filters, selectedItemType, selectedBuildKey, leaderboardRows });
  $: if (urlState) {
    syncUrl();
  }

  $: filterSummary = summarizeFilters(filters);
  $: selectedLeaderboardRow =
    selectedItemType === null
      ? null
      : leaderboardRows.find((row) => row.item_type === selectedItemType) ?? null;
  $: selectedItemParsed = selectedItemType ? parseItemType(selectedItemType) : null;
  $: topAdjustedRow = leaderboardRows[0] ?? null;
  $: topPickRow =
    [...leaderboardRows].sort(
      (left, right) => (right.pick_rate ?? 0) - (left.pick_rate ?? 0)
    )[0] ?? null;
  $: totalSample = leaderboardRows.reduce((sum, row) => sum + row.sample, 0);
  $: buildComponentViews = buildDetail ? buildComponents(buildDetail.components) : [];

  onMount(() => {
    const params = new URLSearchParams(window.location.search);
    const nextFilters = filtersFromParams(params);
    filters = nextFilters;
    draft = draftFromFilters(nextFilters);
    selectedItemType = sanitizeText(params.get('item'));
    selectedBuildKey = sanitizeText(params.get('build'));
    initialized = true;
  });

  function defaultFilters(): LeaderboardFilters {
    return {
      days: 7,
      region: 'all',
      patchId: null,
      contentType: 'all',
      fightScale: 'all',
      limit: 20,
      minSample: 25
    };
  }

  function draftFromFilters(value: LeaderboardFilters): FilterDraft {
    return {
      days: value.days,
      region: value.region,
      patchIdInput: value.patchId === null ? '' : String(value.patchId),
      contentType: value.contentType,
      fightScale: value.fightScale,
      limit: value.limit,
      minSample: value.minSample
    };
  }

  function parseChoice<T extends string>(value: string | null, allowed: readonly T[], fallback: T): T {
    return value && allowed.includes(value as T) ? (value as T) : fallback;
  }

  function parseNumberChoice(
    value: string | null,
    allowed: readonly number[],
    fallback: number
  ): number {
    const parsed = Number(value);
    return allowed.includes(parsed) ? parsed : fallback;
  }

  function sanitizeText(value: string | null): string | null {
    const normalized = value?.trim();
    return normalized ? normalized : null;
  }

  function parsePatchId(value: string): number | null {
    const parsed = Number.parseInt(value, 10);
    return Number.isFinite(parsed) && parsed >= 0 ? parsed : null;
  }

  function filtersFromParams(params: URLSearchParams): LeaderboardFilters {
    const fallback = defaultFilters();
    return {
      days: parseNumberChoice(params.get('days'), dayOptions, fallback.days),
      region: parseChoice(params.get('region'), regions, fallback.region),
      patchId: parsePatchId(params.get('patch_id') ?? ''),
      contentType: parseChoice(params.get('content_type'), contentTypes, fallback.contentType),
      fightScale: parseChoice(params.get('fight_scale'), fightScales, fallback.fightScale),
      limit: parseNumberChoice(params.get('limit'), limitOptions, fallback.limit),
      minSample: parseNumberChoice(params.get('min_sample'), minSampleOptions, fallback.minSample)
    };
  }

  function detailFiltersFrom(value: LeaderboardFilters): DetailFilters {
    return {
      days: value.days,
      region: value.region,
      patchId: value.patchId,
      contentType: value.contentType,
      fightScale: value.fightScale
    };
  }

  function applyFilters() {
    filters = {
      days: draft.days,
      region: draft.region,
      patchId: parsePatchId(draft.patchIdInput),
      contentType: draft.contentType,
      fightScale: draft.fightScale,
      limit: draft.limit,
      minSample: draft.minSample
    };
  }

  function resetFilters() {
    const next = defaultFilters();
    filters = next;
    draft = draftFromFilters(next);
  }

  function syncUrl() {
    const params = new URLSearchParams();
    params.set('days', String(filters.days));
    if (filters.region !== 'all') params.set('region', filters.region);
    if (filters.patchId !== null) params.set('patch_id', String(filters.patchId));
    if (filters.contentType !== 'all') params.set('content_type', filters.contentType);
    if (filters.fightScale !== 'all') params.set('fight_scale', filters.fightScale);
    if (filters.limit !== defaultFilters().limit) params.set('limit', String(filters.limit));
    if (filters.minSample !== defaultFilters().minSample) {
      params.set('min_sample', String(filters.minSample));
    }
    if (selectedItemType) params.set('item', selectedItemType);
    if (selectedBuildKey) params.set('build', selectedBuildKey);
    history.replaceState(null, '', `?${params.toString()}`);
  }

  async function loadLeaderboard() {
    const requestId = ++leaderboardRequestId;
    leaderboardState = 'loading';
    apiStatus = 'loading';

    try {
      const result = await fetchLeaderboard(filters);
      if (requestId !== leaderboardRequestId) return;

      leaderboardRows = result.data;
      lastUpdated = result.meta.generated_at ?? null;
      leaderboardState = 'ready';
      apiStatus = 'ready';

      const hasSelectedItem =
        selectedItemType !== null && leaderboardRows.some((row) => row.item_type === selectedItemType);
      selectedItemType = hasSelectedItem ? selectedItemType : leaderboardRows[0]?.item_type ?? null;
      if (selectedItemType === null) {
        selectedBuildKey = null;
      }
    } catch {
      if (requestId !== leaderboardRequestId) return;

      leaderboardRows = [];
      selectedItemType = null;
      selectedBuildKey = null;
      itemDetail = null;
      buildDetail = null;
      leaderboardState = 'error';
      apiStatus = 'error';
    }
  }

  async function loadItemDetail() {
    if (!selectedItemType) return;

    const requestId = ++itemRequestId;
    itemState = 'loading';

    try {
      const result = await fetchItemDetail('main_hand', selectedItemType, detailFiltersFrom(filters));
      if (requestId !== itemRequestId) return;

      itemDetail = result.data;
      itemState = 'ready';

      const candidateKeys = itemDetail.builds.top_builds.map((build) => build.build_key);
      if (!selectedBuildKey || !candidateKeys.includes(selectedBuildKey)) {
        selectedBuildKey = itemDetail.builds.representative_build?.build_key ?? null;
      }
    } catch {
      if (requestId !== itemRequestId) return;

      itemDetail = null;
      selectedBuildKey = null;
      itemState = 'error';
    }
  }

  async function loadBuildDetail() {
    if (!selectedBuildKey) return;

    const requestId = ++buildRequestId;
    buildState = 'loading';

    try {
      const result = await fetchBuildDetail(selectedBuildKey, detailFiltersFrom(filters));
      if (requestId !== buildRequestId) return;

      buildDetail = result.data;
      buildState = 'ready';
    } catch {
      if (requestId !== buildRequestId) return;

      buildDetail = null;
      buildState = 'error';
    }
  }

  function selectItem(itemType: string) {
    if (selectedItemType === itemType) return;
    selectedItemType = itemType;
    selectedBuildKey = null;
  }

  function selectBuild(buildKey: string) {
    selectedBuildKey = buildKey;
  }

  function selectTableRow(event: KeyboardEvent, itemType: string) {
    if (event.key === 'Enter' || event.key === ' ') {
      event.preventDefault();
      selectItem(itemType);
    }
  }

  function summarizeFilters(value: LeaderboardFilters): string {
    const labels = [
      `${value.days}d window`,
      regionLabel(value.region),
      contentTypeLabel(value.contentType),
      fightScaleLabel(value.fightScale)
    ];
    if (value.patchId !== null) labels.push(`Patch ${value.patchId}`);
    return labels.join(' / ');
  }

  function regionLabel(value: Region): string {
    if (value === 'all') return 'All regions';
    return value.charAt(0).toUpperCase() + value.slice(1);
  }

  function contentTypeLabel(value: ContentTypeFilter): string {
    if (value === 'all') return 'All content';
    if (value === 'open_world') return 'Open world';
    return value.replaceAll('_', ' ');
  }

  function fightScaleLabel(value: FightScaleFilter): string {
    if (value === 'all') return 'All scales';
    return value.replaceAll('_', ' ');
  }

  function formatDecimal(value: number | null | undefined, digits = 2): string {
    if (value === null || value === undefined) return '-';
    return new Intl.NumberFormat('en-US', {
      minimumFractionDigits: 0,
      maximumFractionDigits: digits
    }).format(value);
  }

  function formatSignedPercent(value: number | null | undefined): string {
    if (value === null || value === undefined) return '-';
    return `${value >= 0 ? '+' : ''}${(value * 100).toFixed(1)}%`;
  }

  function formatPercent(value: number | null | undefined): string {
    if (value === null || value === undefined) return '-';
    return `${(value * 100).toFixed(1)}%`;
  }

  function formatCompact(value: number | null | undefined): string {
    if (value === null || value === undefined) return '-';
    return new Intl.NumberFormat('en-US', {
      notation: 'compact',
      maximumFractionDigits: 1
    }).format(value);
  }

  function formatTimestamp(value: string | null): string {
    if (!value) return 'Not yet updated';
    return new Date(value).toLocaleString();
  }

  function confidenceTone(value: Confidence): string {
    return value;
  }

  function metricsFor(summary: MainHandLeaderboardRow | ItemDetail['summary'] | BuildDetail['summary']) {
    return [
      { label: 'Adjusted', value: formatSignedPercent(summary.adjusted_score), tone: summary.adjusted_score >= 0 },
      { label: 'Kill-side', value: formatPercent(summary.kill_side_rate), tone: false },
      { label: 'K/D', value: formatDecimal(summary.kd_ratio), tone: false },
      { label: 'Sample', value: formatDecimal(summary.sample, 0), tone: false },
      { label: 'Pick rate', value: formatPercent(summary.pick_rate), tone: false },
      { label: 'Avg IP', value: formatDecimal(summary.avg_item_power, 0), tone: false }
    ];
  }

  function distributionLabel(row: DistributionRow, kind: 'content' | 'scale' | 'patch'): string {
    if (kind === 'content') {
      return contentTypeLabel((row.content_type as ContentTypeFilter | undefined) ?? 'unknown');
    }
    if (kind === 'scale') {
      return fightScaleLabel((row.fight_scale as FightScaleFilter | undefined) ?? 'unknown');
    }
    if (row.patch_id === null || row.patch_id === undefined) {
      return 'Unpatched';
    }
    return `Patch ${row.patch_id}`;
  }

  function itemLabel(itemType: string): string {
    return parseItemType(itemType).label;
  }

  function tierBadge(itemType: string): string {
    const parsed = parseItemType(itemType);
    return `${parsed.tier}${parsed.enchantment}`;
  }

  function buildComponents(components: BuildComponents): ComponentView[] {
    return buildSlotOrder
      .map(([key, slot]) => {
        const itemType = components[key];
        if (!itemType) return null;
        return { slot, itemType, label: itemLabel(itemType) };
      })
      .filter((value): value is ComponentView => value !== null);
  }
</script>

<svelte:head>
  <title>Albion Analytics Meta Lab</title>
  <meta
    name="description"
    content="Read Albion Online main-hand rankings with a table-first meta dashboard."
  />
</svelte:head>

<main class="page">
  <section class="hero-band">
    <div class="hero-copy">
      <p class="eyebrow">Albion Analytics</p>
      <h1>Main-hand meta at a glance</h1>
      <p class="hero-text">
        A cleaner, table-first ranking view for current weapon performance, confidence, and build
        context.
      </p>
      <div class="hero-stats">
        <div class="hero-stat">
          <span>Top adjusted</span>
          <strong>{topAdjustedRow ? itemLabel(topAdjustedRow.item_type) : 'Waiting for data'}</strong>
        </div>
        <div class="hero-stat">
          <span>Highest pick rate</span>
          <strong>{topPickRow ? itemLabel(topPickRow.item_type) : 'Waiting for data'}</strong>
        </div>
        <div class="hero-stat">
          <span>Rows in slice</span>
          <strong>{leaderboardRows.length}</strong>
        </div>
        <div class="hero-stat">
          <span>Total sample</span>
          <strong>{formatCompact(totalSample)}</strong>
        </div>
      </div>
    </div>

    <form class="filter-panel" on:submit|preventDefault={applyFilters}>
      <div class="filter-row">
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
      </div>

      <div class="filter-row secondary-row">
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
          <button class="primary-button" type="submit">Update</button>
          <button class="secondary-button" type="button" on:click={resetFilters}>Reset</button>
        </div>
      </div>
    </form>
  </section>

  <section class="summary-band">
    <div class="summary-copy">
      <strong>Current slice</strong>
      <span>{filterSummary}</span>
    </div>
    <div class="summary-meta">
      <span class="timestamp">Updated {formatTimestamp(lastUpdated)}</span>
      <span class={`api-pill ${apiStatus}`}>
        {apiStatus === 'ready'
          ? 'API connected'
          : apiStatus === 'error'
            ? 'API issue'
            : 'Checking API'}
      </span>
    </div>
  </section>

  <section class="content-grid">
    <section class="surface leaderboard-panel" aria-label="Main-hand leaderboard">
      <header class="panel-head">
        <div>
          <p class="eyebrow">Leaderboard</p>
          <h2>Weapon rankings</h2>
        </div>
        <span>Adjusted score, pick rate, and sample strength in one scan.</span>
      </header>

      {#if leaderboardState === 'loading'}
        <div class="loading-table" aria-label="Loading leaderboard">
          {#each Array(8) as _}
            <div class="loading-row"></div>
          {/each}
        </div>
      {:else if leaderboardState === 'error'}
        <div class="empty-state">
          <h3>API connection issue.</h3>
          <p>Ranking data could not be loaded. Please try again in a moment.</p>
          <button class="secondary-button" type="button" on:click={() => void loadLeaderboard()}>
            Retry
          </button>
        </div>
      {:else if leaderboardRows.length === 0}
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
              </tr>
            </thead>
            <tbody>
              {#each leaderboardRows as row, index}
                {@const parsed = parseItemType(row.item_type)}
                <tr
                  class:selected={row.item_type === selectedItemType}
                  role="button"
                  tabindex="0"
                  aria-label={`Open ${parsed.label} detail`}
                  on:click={() => selectItem(row.item_type)}
                  on:keydown={(event) => selectTableRow(event, row.item_type)}
                >
                  <td class="rank-col">#{index + 1}</td>
                  <td>
                    <div class="weapon-cell">
                      <img alt={parsed.label} src={itemImageUrl(row.item_type)} loading="lazy" />
                      <div class="weapon-copy">
                        <strong>{parsed.label}</strong>
                        <span>{tierBadge(row.item_type)}</span>
                        <code>{row.item_type}</code>
                      </div>
                    </div>
                  </td>
                  <td class:positive={row.adjusted_score >= 0}>{formatSignedPercent(row.adjusted_score)}</td>
                  <td>{formatPercent(row.kill_side_rate)}</td>
                  <td>{formatPercent(row.pick_rate)}</td>
                  <td>{formatDecimal(row.sample, 0)}</td>
                  <td>
                    <span class={`confidence ${confidenceTone(row.confidence)}`}>{row.confidence}</span>
                  </td>
                </tr>
              {/each}
            </tbody>
          </table>
        </div>
      {/if}
    </section>

    <aside class="detail-column">
      <section class="surface detail-panel">
        <header class="panel-head">
          <div>
            <p class="eyebrow">Selected weapon</p>
            <h2>{selectedItemParsed ? selectedItemParsed.label : 'Choose a weapon'}</h2>
          </div>
          {#if selectedItemParsed}
            <span>{selectedItemParsed.tier}{selectedItemParsed.enchantment}</span>
          {/if}
        </header>

        {#if itemState === 'loading'}
          <div class="loading-block"></div>
        {:else if itemState === 'error'}
          <div class="empty-state compact">
            <h3>Item detail unavailable.</h3>
            <p>The selected weapon could not be loaded right now.</p>
            <button class="secondary-button" type="button" on:click={() => void loadItemDetail()}>
              Retry
            </button>
          </div>
        {:else if itemDetail && selectedItemParsed}
          <div class="selection-header">
            <img alt={selectedItemParsed.label} src={itemImageUrl(itemDetail.item_type)} loading="lazy" />
            <div>
              <strong>{selectedItemParsed.label}</strong>
              <span>{itemDetail.item_type}</span>
            </div>
          </div>

          <dl class="metric-strip">
            {#each metricsFor(itemDetail.summary) as metric}
              <div>
                <dt>{metric.label}</dt>
                <dd class:positive={metric.tone}>{metric.value}</dd>
              </div>
            {/each}
          </dl>

          <section class="detail-block">
            <div class="block-head">
              <h3>Top builds</h3>
              <span>Appearance first, adjusted score second.</span>
            </div>
            {#if itemDetail.builds.top_builds.length === 0}
              <p class="empty-copy">No build rows for this slice.</p>
            {:else}
              <div class="build-stack">
                {#each itemDetail.builds.top_builds as build}
                  <button
                    class:selected={build.build_key === selectedBuildKey}
                    class="build-row"
                    type="button"
                    on:click={() => selectBuild(build.build_key)}
                  >
                    <div class="build-row-main">
                      <strong>{formatSignedPercent(build.adjusted_score)}</strong>
                      <span>{formatDecimal(build.sample, 0)} sample</span>
                    </div>
                    <div class="build-row-copy">
                      {#if build.components}
                        {#each buildComponents(build.components) as component}
                          <span>{component.slot}: {component.label}</span>
                        {/each}
                      {/if}
                    </div>
                    <code>{build.build_key}</code>
                  </button>
                {/each}
              </div>
            {/if}
          </section>

          <section class="detail-block">
            <div class="block-head">
              <h3>Distribution</h3>
              <span>How this weapon performs across content, scale, and patch.</span>
            </div>
            <div class="distribution-grid">
              <div>
                <h4>Content</h4>
                <div class="distribution-list">
                  {#each itemDetail.distributions.by_content_type as row}
                    <div class="distribution-row">
                      <div class="distribution-copy">
                        <strong>{distributionLabel(row, 'content')}</strong>
                        <span>{formatPercent(row.kill_side_rate)} / {formatDecimal(row.sample, 0)} sample</span>
                      </div>
                      <div class="bar-track">
                        <span style={`width: ${Math.max(row.kill_side_rate * 100, 3)}%`}></span>
                      </div>
                    </div>
                  {/each}
                </div>
              </div>

              <div>
                <h4>Scale</h4>
                <div class="distribution-list">
                  {#each itemDetail.distributions.by_fight_scale as row}
                    <div class="distribution-row">
                      <div class="distribution-copy">
                        <strong>{distributionLabel(row, 'scale')}</strong>
                        <span>{formatPercent(row.kill_side_rate)} / {formatDecimal(row.sample, 0)} sample</span>
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
        {:else}
          <div class="empty-state compact">
            <h3>Select a weapon.</h3>
            <p>The first row opens automatically when leaderboard data is available.</p>
          </div>
        {/if}
      </section>

      <section class="surface detail-panel">
        <header class="panel-head">
          <div>
            <p class="eyebrow">Selected build</p>
            <h2>{selectedBuildKey ? 'Build breakdown' : 'Choose a build'}</h2>
          </div>
          {#if buildDetail}
            <span>{buildComponentViews.length} pieces</span>
          {/if}
        </header>

        {#if buildState === 'loading'}
          <div class="loading-block short"></div>
        {:else if buildState === 'error'}
          <div class="empty-state compact">
            <h3>Build detail unavailable.</h3>
            <p>The selected build could not be loaded right now.</p>
            <button class="secondary-button" type="button" on:click={() => void loadBuildDetail()}>
              Retry
            </button>
          </div>
        {:else if buildDetail}
          <dl class="metric-strip">
            {#each metricsFor(buildDetail.summary) as metric}
              <div>
                <dt>{metric.label}</dt>
                <dd class:positive={metric.tone}>{metric.value}</dd>
              </div>
            {/each}
          </dl>

          <section class="detail-block">
            <div class="block-head">
              <h3>Loadout</h3>
              <span>The selected build components in slot order.</span>
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

          <section class="detail-block">
            <div class="block-head">
              <h3>Context split</h3>
              <span>Quick view of content and scale distribution.</span>
            </div>
            <div class="distribution-grid">
              <div>
                <h4>Content</h4>
                <div class="distribution-list">
                  {#each buildDetail.distributions.by_content_type as row}
                    <div class="distribution-row">
                      <div class="distribution-copy">
                        <strong>{distributionLabel(row, 'content')}</strong>
                        <span>{formatPercent(row.kill_side_rate)} / {formatDecimal(row.sample, 0)} sample</span>
                      </div>
                      <div class="bar-track">
                        <span style={`width: ${Math.max(row.kill_side_rate * 100, 3)}%`}></span>
                      </div>
                    </div>
                  {/each}
                </div>
              </div>

              <div>
                <h4>Scale</h4>
                <div class="distribution-list">
                  {#each buildDetail.distributions.by_fight_scale as row}
                    <div class="distribution-row">
                      <div class="distribution-copy">
                        <strong>{distributionLabel(row, 'scale')}</strong>
                        <span>{formatPercent(row.kill_side_rate)} / {formatDecimal(row.sample, 0)} sample</span>
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
        {:else}
          <div class="empty-state compact">
            <h3>Select a build.</h3>
            <p>Top builds from the selected weapon will appear here.</p>
          </div>
        {/if}
      </section>
    </aside>
  </section>
</main>

<style>
  :global(*) {
    box-sizing: border-box;
  }

  :global(body) {
    margin: 0;
    background: #eff2ea;
    color: #161a17;
    font-family:
      Inter, ui-sans-serif, system-ui, -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif;
  }

  :global(button),
  :global(input),
  :global(select) {
    font: inherit;
  }

  :global(code) {
    font-family:
      'SFMono-Regular', ui-monospace, SFMono-Regular, Menlo, Consolas, 'Liberation Mono', monospace;
  }

  .page {
    margin: 0 auto;
    max-width: 1440px;
    padding: 20px;
  }

  .hero-band,
  .summary-band,
  .content-grid {
    width: 100%;
  }

  .hero-band {
    display: grid;
    gap: 18px;
    grid-template-columns: minmax(0, 1.2fr) minmax(360px, 0.9fr);
    margin-bottom: 16px;
  }

  .hero-copy,
  .filter-panel,
  .surface,
  .hero-stat,
  .component-tile,
  .build-row {
    border: 1px solid #d8ddd3;
    border-radius: 8px;
    background: #fcfdf9;
  }

  .hero-copy,
  .filter-panel,
  .surface {
    padding: 20px;
  }

  .eyebrow {
    margin: 0 0 8px;
    color: #5b675d;
    font-size: 12px;
    font-weight: 800;
    text-transform: uppercase;
  }

  h1,
  h2,
  h3,
  h4,
  p {
    margin: 0;
  }

  .hero-copy h1 {
    font-size: 38px;
    line-height: 1.05;
    max-width: 12ch;
  }

  .hero-text {
    color: #586458;
    font-size: 15px;
    line-height: 1.6;
    margin-top: 12px;
    max-width: 62ch;
  }

  .hero-stats {
    display: grid;
    gap: 12px;
    grid-template-columns: repeat(2, minmax(0, 1fr));
    margin-top: 18px;
  }

  .hero-stat {
    padding: 14px;
  }

  .hero-stat span,
  .summary-copy span,
  .summary-meta span,
  .panel-head span,
  .selection-header span,
  .distribution-copy span,
  .build-row span,
  .component-tile span,
  .empty-state p,
  .empty-copy {
    color: #5b675d;
    font-size: 13px;
    line-height: 1.5;
    overflow-wrap: anywhere;
  }

  .hero-stat strong {
    display: block;
    font-size: 18px;
    line-height: 1.3;
    margin-top: 4px;
    overflow-wrap: anywhere;
  }

  .filter-panel {
    display: grid;
    gap: 12px;
  }

  .filter-row {
    display: grid;
    gap: 12px;
    grid-template-columns: repeat(4, minmax(0, 1fr));
  }

  .secondary-row {
    grid-template-columns: minmax(0, 1fr) 120px 140px auto;
  }

  label {
    color: #4d584e;
    display: grid;
    font-size: 12px;
    font-weight: 800;
    gap: 6px;
    text-transform: uppercase;
  }

  input,
  select {
    min-height: 42px;
    padding: 0 12px;
    color: #161a17;
    background: #f6f8f3;
    border: 1px solid #d8ddd3;
    border-radius: 8px;
  }

  .filter-actions {
    align-items: end;
    display: flex;
    gap: 8px;
    justify-content: flex-end;
  }

  .primary-button,
  .secondary-button {
    min-height: 42px;
    padding: 0 14px;
    border-radius: 8px;
    border: 0;
    cursor: pointer;
    font-weight: 800;
  }

  .primary-button {
    background: #161a17;
    color: #f5f7f1;
  }

  .secondary-button {
    background: #e4e9df;
    color: #161a17;
  }

  .summary-band {
    align-items: center;
    display: flex;
    justify-content: space-between;
    gap: 12px;
    margin-bottom: 16px;
    padding: 4px 2px;
  }

  .summary-copy strong {
    display: block;
    font-size: 15px;
    margin-bottom: 4px;
  }

  .summary-meta {
    align-items: center;
    display: flex;
    gap: 10px;
    justify-content: flex-end;
  }

  .timestamp {
    white-space: nowrap;
  }

  .api-pill {
    align-items: center;
    border-radius: 999px;
    display: inline-flex;
    font-size: 12px;
    font-weight: 800;
    min-height: 32px;
    padding: 0 12px;
  }

  .api-pill.loading {
    background: #eef0e7;
    color: #536054;
  }

  .api-pill.ready {
    background: #e3f2e7;
    color: #236340;
  }

  .api-pill.error {
    background: #faece9;
    color: #a13d37;
  }

  .content-grid {
    display: grid;
    gap: 18px;
    grid-template-columns: minmax(0, 1.1fr) minmax(360px, 0.9fr);
  }

  .detail-column {
    display: grid;
    gap: 18px;
  }

  .panel-head {
    align-items: end;
    border-bottom: 1px solid #e1e6dc;
    display: flex;
    justify-content: space-between;
    gap: 12px;
    padding-bottom: 14px;
  }

  .panel-head h2 {
    font-size: 24px;
    line-height: 1.1;
  }

  .loading-table,
  .loading-block {
    display: grid;
    gap: 10px;
    margin-top: 18px;
  }

  .loading-row,
  .loading-block {
    animation: pulse 1.2s ease-in-out infinite;
    background: linear-gradient(90deg, #eef1eb, #ffffff, #eef1eb);
    border-radius: 8px;
  }

  .loading-row {
    height: 68px;
  }

  .loading-block {
    height: 220px;
  }

  .loading-block.short {
    height: 180px;
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
    gap: 10px;
    justify-items: start;
    padding: 28px 0 6px;
  }

  .empty-state.compact {
    padding-top: 18px;
  }

  .table-scroll {
    margin-top: 16px;
    overflow-x: auto;
  }

  .rank-table {
    border-collapse: collapse;
    min-width: 760px;
    width: 100%;
  }

  .rank-table th,
  .rank-table td {
    border-bottom: 1px solid #e4e9df;
    padding: 14px 10px;
    text-align: left;
    vertical-align: middle;
  }

  .rank-table th {
    color: #657166;
    font-size: 12px;
    font-weight: 800;
    position: sticky;
    top: 0;
    background: #fcfdf9;
    text-transform: uppercase;
    z-index: 1;
  }

  .rank-table tbody tr {
    cursor: pointer;
  }

  .rank-table tbody tr:hover {
    background: #f5f8f1;
  }

  .rank-table tbody tr.selected {
    background: #edf5ea;
  }

  .rank-col {
    width: 64px;
    white-space: nowrap;
  }

  .metric-col {
    width: 120px;
    white-space: nowrap;
  }

  .weapon-cell,
  .selection-header {
    align-items: center;
    display: grid;
    gap: 12px;
    grid-template-columns: 54px minmax(0, 1fr);
  }

  .weapon-cell img,
  .selection-header img,
  .component-tile img {
    height: 54px;
    width: 54px;
    border-radius: 8px;
    border: 1px solid #d8ddd3;
    background: #f4f6f0;
    object-fit: contain;
    padding: 4px;
  }

  .weapon-copy,
  .selection-header div {
    display: grid;
    gap: 4px;
    min-width: 0;
  }

  .weapon-copy strong,
  .selection-header strong,
  .component-tile strong,
  .distribution-copy strong,
  .build-row strong {
    overflow-wrap: anywhere;
  }

  .weapon-copy span,
  .selection-header span {
    font-size: 12px;
  }

  code {
    color: #718071;
    font-size: 11px;
    overflow-wrap: anywhere;
  }

  .positive {
    color: #22653f;
  }

  .confidence {
    display: inline-flex;
    align-items: center;
    border-radius: 999px;
    font-size: 11px;
    font-weight: 800;
    min-height: 28px;
    padding: 0 10px;
    text-transform: uppercase;
  }

  .confidence.low {
    background: #f3ece2;
    color: #84653b;
  }

  .confidence.medium {
    background: #edf2dd;
    color: #5c6e12;
  }

  .confidence.high {
    background: #e4f1ea;
    color: #236340;
  }

  .selection-header {
    margin-top: 16px;
  }

  .metric-strip {
    display: grid;
    gap: 0;
    grid-template-columns: repeat(3, minmax(0, 1fr));
    margin: 18px 0 0;
  }

  .metric-strip div {
    padding: 12px 0;
    border-bottom: 1px solid #e4e9df;
  }

  .metric-strip dt {
    color: #647064;
    font-size: 11px;
    font-weight: 800;
    margin-bottom: 4px;
    text-transform: uppercase;
  }

  .metric-strip dd {
    font-size: 16px;
    font-weight: 800;
    margin: 0;
  }

  .detail-block {
    border-top: 1px solid #e4e9df;
    margin-top: 18px;
    padding-top: 16px;
  }

  .block-head {
    align-items: baseline;
    display: flex;
    justify-content: space-between;
    gap: 12px;
    margin-bottom: 12px;
  }

  .block-head h3,
  .distribution-grid h4 {
    font-size: 17px;
  }

  .distribution-grid {
    display: grid;
    gap: 16px;
    grid-template-columns: repeat(2, minmax(0, 1fr));
  }

  .distribution-list,
  .build-stack {
    display: grid;
    gap: 10px;
  }

  .distribution-row {
    display: grid;
    gap: 8px;
  }

  .distribution-copy {
    align-items: baseline;
    display: flex;
    gap: 12px;
    justify-content: space-between;
  }

  .bar-track {
    height: 10px;
    overflow: hidden;
    border-radius: 999px;
    background: #e5eadf;
  }

  .bar-track span {
    display: block;
    height: 100%;
    background: linear-gradient(90deg, #1d2d23, #2d7a4d, #d5b257);
  }

  .build-row {
    display: grid;
    gap: 8px;
    padding: 12px;
    text-align: left;
    width: 100%;
  }

  .build-row.selected {
    border-color: #1d2d23;
    box-shadow: inset 0 0 0 1px #1d2d23;
  }

  .build-row-main {
    align-items: baseline;
    display: flex;
    gap: 10px;
    justify-content: space-between;
  }

  .build-row-copy {
    display: flex;
    flex-wrap: wrap;
    gap: 6px;
  }

  .build-row-copy span {
    padding: 4px 8px;
    border-radius: 999px;
    background: #eef2e9;
    font-size: 12px;
  }

  .component-grid {
    display: grid;
    gap: 10px;
    grid-template-columns: repeat(2, minmax(0, 1fr));
  }

  .component-tile {
    display: grid;
    gap: 8px;
    justify-items: start;
    min-height: 170px;
    padding: 14px;
  }

  @media (max-width: 1180px) {
    .hero-band,
    .content-grid {
      grid-template-columns: 1fr;
    }
  }

  @media (max-width: 840px) {
    .page {
      padding: 14px;
    }

    .hero-copy h1 {
      font-size: 32px;
    }

    .hero-stats,
    .metric-strip,
    .distribution-grid,
    .component-grid {
      grid-template-columns: 1fr;
    }

    .filter-row,
    .secondary-row {
      grid-template-columns: repeat(2, minmax(0, 1fr));
    }

    .filter-actions {
      grid-column: 1 / -1;
      justify-content: stretch;
    }

    .filter-actions :global(button) {
      flex: 1;
    }

    .summary-band,
    .summary-meta,
    .block-head,
    .distribution-copy,
    .build-row-main {
      align-items: start;
      display: grid;
      gap: 6px;
      justify-content: start;
    }
  }
</style>
