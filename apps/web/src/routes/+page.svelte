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
    killArea: string;
    limit: number;
    minSample: number;
  };

  type ComponentView = {
    slot: string;
    itemType: string;
    label: string;
  };

  const dayOptions = [7, 14, 30, 60];
  const limitOptions = [10, 20, 50, 100];
  const minSampleOptions = [0, 25, 100, 250];
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
  let leaderboardError = '';
  let itemError = '';
  let buildError = '';
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
  $: representativeBuild = itemDetail?.builds.representative_build ?? null;

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
      days: 14,
      region: 'all',
      patchId: null,
      contentType: 'all',
      fightScale: 'all',
      killArea: '',
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
      killArea: value.killArea,
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
      killArea: params.get('kill_area')?.trim() ?? '',
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
      fightScale: value.fightScale,
      killArea: value.killArea
    };
  }

  function applyFilters() {
    filters = {
      days: draft.days,
      region: draft.region,
      patchId: parsePatchId(draft.patchIdInput),
      contentType: draft.contentType,
      fightScale: draft.fightScale,
      killArea: draft.killArea.trim(),
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
    if (filters.killArea) params.set('kill_area', filters.killArea);
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
    leaderboardError = '';

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
    } catch (error) {
      if (requestId !== leaderboardRequestId) return;

      leaderboardRows = [];
      selectedItemType = null;
      selectedBuildKey = null;
      itemDetail = null;
      buildDetail = null;
      leaderboardState = 'error';
      apiStatus = 'error';
      leaderboardError = error instanceof Error ? error.message : 'Leaderboard could not be loaded.';
    }
  }

  async function loadItemDetail() {
    if (!selectedItemType) return;

    const requestId = ++itemRequestId;
    itemState = 'loading';
    itemError = '';

    try {
      const result = await fetchItemDetail('main_hand', selectedItemType, detailFiltersFrom(filters));
      if (requestId !== itemRequestId) return;

      itemDetail = result.data;
      itemState = 'ready';

      const candidateKeys = itemDetail.builds.top_builds.map((build) => build.build_key);
      if (!selectedBuildKey || !candidateKeys.includes(selectedBuildKey)) {
        selectedBuildKey = itemDetail.builds.representative_build?.build_key ?? null;
      }
    } catch (error) {
      if (requestId !== itemRequestId) return;

      itemDetail = null;
      selectedBuildKey = null;
      itemState = 'error';
      itemError = error instanceof Error ? error.message : 'Item detail could not be loaded.';
    }
  }

  async function loadBuildDetail() {
    if (!selectedBuildKey) return;

    const requestId = ++buildRequestId;
    buildState = 'loading';
    buildError = '';

    try {
      const result = await fetchBuildDetail(selectedBuildKey, detailFiltersFrom(filters));
      if (requestId !== buildRequestId) return;

      buildDetail = result.data;
      buildState = 'ready';
    } catch (error) {
      if (requestId !== buildRequestId) return;

      buildDetail = null;
      buildState = 'error';
      buildError = error instanceof Error ? error.message : 'Build detail could not be loaded.';
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

  function summarizeFilters(value: LeaderboardFilters): string {
    const labels = [
      `${value.days}d`,
      humanize(value.region, 'All regions'),
      humanize(value.contentType, 'All content'),
      humanize(value.fightScale, 'All scales')
    ];
    if (value.patchId !== null) labels.push(`Patch ${value.patchId}`);
    if (value.killArea) labels.push(value.killArea);
    return labels.join(' / ');
  }

  function humanize(value: string, fallback: string): string {
    if (value === 'all') return fallback;
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
    return new Intl.NumberFormat('en-US', { notation: 'compact', maximumFractionDigits: 1 }).format(
      value
    );
  }

  function confidenceTone(value: Confidence): string {
    return value;
  }

  function metricsFor(summary: MainHandLeaderboardRow | ItemDetail['summary'] | BuildDetail['summary']) {
    return [
      { label: 'Adjusted', value: formatSignedPercent(summary.adjusted_score) },
      { label: 'Kill-side', value: formatPercent(summary.kill_side_rate) },
      { label: 'K/D', value: formatDecimal(summary.kd_ratio) },
      { label: 'Sample', value: formatDecimal(summary.sample, 0) },
      { label: 'Pick rate', value: formatPercent(summary.pick_rate) },
      { label: 'Avg IP', value: formatDecimal(summary.avg_item_power, 0) }
    ];
  }

  function distributionLabel(row: DistributionRow, kind: 'content' | 'scale' | 'patch'): string {
    if (kind === 'content') {
      return humanize(row.content_type ?? 'unknown', 'Unknown');
    }
    if (kind === 'scale') {
      return humanize(row.fight_scale ?? 'unknown', 'Unknown');
    }
    if (row.patch_id === null || row.patch_id === undefined) {
      return 'Unpatched';
    }
    return `Patch ${row.patch_id}`;
  }

  function itemLabel(itemType: string): string {
    return parseItemType(itemType).label;
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
    content="Test the Albion Analytics main-hand leaderboard with item and build detail lookups."
  />
</svelte:head>

<main class="app-shell">
  <section class="control-band">
    <div class="brand-block">
      <div class="brand-mark">AA</div>
      <div class="brand-copy">
        <p>Albion Analytics</p>
        <h1>Meta Lab</h1>
        <span>{filterSummary}</span>
      </div>
    </div>

    <form class="filter-grid" on:submit|preventDefault={applyFilters}>
      <label>
        Days
        <select bind:value={draft.days}>
          {#each dayOptions as option}
            <option value={option}>{option}</option>
          {/each}
        </select>
      </label>

      <label>
        Region
        <select bind:value={draft.region}>
          {#each regions as region}
            <option value={region}>{humanize(region, 'All regions')}</option>
          {/each}
        </select>
      </label>

      <label>
        Patch
        <input bind:value={draft.patchIdInput} inputmode="numeric" placeholder="Any" />
      </label>

      <label>
        Content
        <select bind:value={draft.contentType}>
          {#each contentTypes as option}
            <option value={option}>{humanize(option, 'All content')}</option>
          {/each}
        </select>
      </label>

      <label>
        Scale
        <select bind:value={draft.fightScale}>
          {#each fightScales as option}
            <option value={option}>{humanize(option, 'All scales')}</option>
          {/each}
        </select>
      </label>

      <label class="wide">
        Kill area
        <input bind:value={draft.killArea} placeholder="Exact slug or raw area name" />
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

      <div class="actions">
        <button class="primary" type="submit">Apply</button>
        <button class="secondary" type="button" on:click={resetFilters}>Reset</button>
      </div>
    </form>
  </section>

  <section class="status-band">
    <div>
      <strong>Main-hand leaderboard</strong>
      <span>
        {leaderboardRows.length} rows
        {#if lastUpdated}
          · updated {new Date(lastUpdated).toLocaleString()}
        {/if}
      </span>
    </div>
    <span class={`api-pill ${apiStatus}`}>
      {apiStatus === 'ready' ? 'API connected' : apiStatus === 'error' ? 'API issue' : 'Loading API'}
    </span>
  </section>

  <section class="workspace">
    <section class="leaderboard-shell" aria-label="Main-hand leaderboard">
      <header class="section-head">
        <h2>Leaderboard</h2>
        <span>Adjusted score first, then sample and appearances.</span>
      </header>

      {#if leaderboardState === 'loading'}
        <div class="loading-list" aria-label="Loading leaderboard">
          {#each Array(7) as _}
            <div class="loading-row"></div>
          {/each}
        </div>
      {:else if leaderboardState === 'error'}
        <div class="empty-panel">
          <h3>Leaderboard unavailable</h3>
          <p>{leaderboardError}</p>
        </div>
      {:else if leaderboardRows.length === 0}
        <div class="empty-panel">
          <h3>No rows for this slice</h3>
          <p>Try a broader region, content filter, or lower minimum sample.</p>
        </div>
      {:else}
        <ol class="leaderboard-list">
          {#each leaderboardRows as row, index}
            {@const parsed = parseItemType(row.item_type)}
            <li>
              <button
                class:selected={row.item_type === selectedItemType}
                class="leaderboard-row"
                type="button"
                on:click={() => selectItem(row.item_type)}
              >
                <span class="rank">#{index + 1}</span>
                <img alt={parsed.label} src={itemImageUrl(row.item_type)} loading="lazy" />
                <div class="entity-copy">
                  <strong>{parsed.label}</strong>
                  <span>
                    {parsed.tier}{parsed.enchantment} · {row.item_type}
                  </span>
                  {#if row.top_build_key}
                    <em>{row.top_build_key}</em>
                  {/if}
                </div>
                <dl class="row-metrics">
                  <div>
                    <dt>Adjusted</dt>
                    <dd class:positive={row.adjusted_score >= 0}>{formatSignedPercent(row.adjusted_score)}</dd>
                  </div>
                  <div>
                    <dt>Kill-side</dt>
                    <dd>{formatPercent(row.kill_side_rate)}</dd>
                  </div>
                  <div>
                    <dt>K/D</dt>
                    <dd>{formatDecimal(row.kd_ratio)}</dd>
                  </div>
                  <div>
                    <dt>Sample</dt>
                    <dd>{formatDecimal(row.sample, 0)}</dd>
                  </div>
                  <div>
                    <dt>Pick</dt>
                    <dd>{formatPercent(row.pick_rate)}</dd>
                  </div>
                </dl>
                <span class={`confidence ${confidenceTone(row.confidence)}`}>{row.confidence}</span>
              </button>
            </li>
          {/each}
        </ol>
      {/if}
    </section>

    <aside class="detail-shell">
      <section class="detail-section">
        <header class="section-head">
          <h2>Item detail</h2>
          <span>Main hand focus with representative builds.</span>
        </header>

        {#if itemState === 'loading'}
          <div class="loading-block"></div>
        {:else if itemState === 'error'}
          <div class="empty-panel">
            <h3>Item detail unavailable</h3>
            <p>{itemError}</p>
          </div>
        {:else if itemDetail}
          {@const selectedItem = parseItemType(itemDetail.item_type)}
          <div class="detail-header">
            <img alt={selectedItem.label} src={itemImageUrl(itemDetail.item_type)} loading="lazy" />
            <div>
              <p>{selectedItem.tier}{selectedItem.enchantment}</p>
              <h3>{selectedItem.label}</h3>
              <span>{itemDetail.item_type}</span>
            </div>
          </div>

          <dl class="summary-grid">
            {#each metricsFor(itemDetail.summary) as metric}
              <div>
                <dt>{metric.label}</dt>
                <dd>{metric.value}</dd>
              </div>
            {/each}
          </dl>

          <section class="subsection">
            <header class="subhead">
              <h4>Top builds</h4>
              <span>Appearance first, adjusted score second.</span>
            </header>
            {#if itemDetail.builds.top_builds.length === 0}
              <p class="empty-copy">No build rows for this slice.</p>
            {:else}
              <div class="build-list">
                {#each itemDetail.builds.top_builds as build}
                  <button
                    class:selected={build.build_key === selectedBuildKey}
                    class="build-row"
                    type="button"
                    on:click={() => selectBuild(build.build_key)}
                  >
                    <div class="build-main">
                      <strong>{build.build_key}</strong>
                      <span>{formatSignedPercent(build.adjusted_score)} · {formatDecimal(build.sample, 0)} sample</span>
                    </div>
                    <div class="component-strip">
                      {#if build.components}
                        {#each buildComponents(build.components) as component}
                          <span>{component.slot}: {component.label}</span>
                        {/each}
                      {/if}
                    </div>
                  </button>
                {/each}
              </div>
            {/if}
          </section>

          <section class="subsection">
            <header class="subhead">
              <h4>Content split</h4>
              <span>Grouped by derived content type.</span>
            </header>
            <div class="distribution-list">
              {#each itemDetail.distributions.by_content_type as row}
                <div class="distribution-row">
                  <div class="distribution-copy">
                    <strong>{distributionLabel(row, 'content')}</strong>
                    <span>{formatPercent(row.kill_side_rate)} kill-side · {formatDecimal(row.sample, 0)} sample</span>
                  </div>
                  <div class="bar-track">
                    <span style={`width: ${Math.max(row.kill_side_rate * 100, 3)}%`}></span>
                  </div>
                </div>
              {/each}
            </div>
          </section>

          <section class="subsection two-column">
            <div>
              <header class="subhead">
                <h4>Scale split</h4>
              </header>
              <div class="distribution-list compact">
                {#each itemDetail.distributions.by_fight_scale as row}
                  <div class="distribution-row">
                    <div class="distribution-copy">
                      <strong>{distributionLabel(row, 'scale')}</strong>
                      <span>{formatDecimal(row.sample, 0)} sample</span>
                    </div>
                    <div class="bar-track">
                      <span style={`width: ${Math.max(row.kill_side_rate * 100, 3)}%`}></span>
                    </div>
                  </div>
                {/each}
              </div>
            </div>
            <div>
              <header class="subhead">
                <h4>Patch split</h4>
              </header>
              <div class="distribution-list compact">
                {#each itemDetail.distributions.by_patch as row}
                  <div class="distribution-row">
                    <div class="distribution-copy">
                      <strong>{distributionLabel(row, 'patch')}</strong>
                      <span>{formatDecimal(row.sample, 0)} sample</span>
                    </div>
                    <div class="bar-track">
                      <span style={`width: ${Math.max(row.kill_side_rate * 100, 3)}%`}></span>
                    </div>
                  </div>
                {/each}
              </div>
            </div>
          </section>
        {:else}
          <div class="empty-panel">
            <h3>Select a main hand</h3>
            <p>The first leaderboard row will open automatically when data is available.</p>
          </div>
        {/if}
      </section>

      <section class="detail-section build-detail">
        <header class="section-head">
          <h2>Build detail</h2>
          <span>Selected from the build list above.</span>
        </header>

        {#if buildState === 'loading'}
          <div class="loading-block"></div>
        {:else if buildState === 'error'}
          <div class="empty-panel">
            <h3>Build detail unavailable</h3>
            <p>{buildError}</p>
          </div>
        {:else if buildDetail}
          <div class="detail-header compact-header">
            <div>
              <p>Build key</p>
              <h3>{buildDetail.build_key}</h3>
            </div>
          </div>

          <dl class="summary-grid">
            {#each metricsFor(buildDetail.summary) as metric}
              <div>
                <dt>{metric.label}</dt>
                <dd>{metric.value}</dd>
              </div>
            {/each}
          </dl>

          <section class="subsection">
            <header class="subhead">
              <h4>Loadout</h4>
            </header>
            <div class="component-gallery">
              {#each buildComponents(buildDetail.components) as component}
                <div class="component-card">
                  <img alt={component.label} src={itemImageUrl(component.itemType)} loading="lazy" />
                  <strong>{component.slot}</strong>
                  <span>{component.label}</span>
                </div>
              {/each}
            </div>
          </section>

          <section class="subsection two-column">
            <div>
              <header class="subhead">
                <h4>Content split</h4>
              </header>
              <div class="distribution-list compact">
                {#each buildDetail.distributions.by_content_type as row}
                  <div class="distribution-row">
                    <div class="distribution-copy">
                      <strong>{distributionLabel(row, 'content')}</strong>
                      <span>{formatDecimal(row.sample, 0)} sample</span>
                    </div>
                    <div class="bar-track">
                      <span style={`width: ${Math.max(row.kill_side_rate * 100, 3)}%`}></span>
                    </div>
                  </div>
                {/each}
              </div>
            </div>
            <div>
              <header class="subhead">
                <h4>Scale split</h4>
              </header>
              <div class="distribution-list compact">
                {#each buildDetail.distributions.by_fight_scale as row}
                  <div class="distribution-row">
                    <div class="distribution-copy">
                      <strong>{distributionLabel(row, 'scale')}</strong>
                      <span>{formatDecimal(row.sample, 0)} sample</span>
                    </div>
                    <div class="bar-track">
                      <span style={`width: ${Math.max(row.kill_side_rate * 100, 3)}%`}></span>
                    </div>
                  </div>
                {/each}
              </div>
            </div>
          </section>
        {:else}
          <div class="empty-panel">
            <h3>Select a build</h3>
            <p>Representative and top builds will appear after item detail loads.</p>
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
    background: #f3f1eb;
    color: #131313;
    font-family:
      Inter, ui-sans-serif, system-ui, -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif;
  }

  :global(button),
  :global(input),
  :global(select) {
    font: inherit;
  }

  .app-shell {
    min-height: 100vh;
    padding: 20px;
  }

  .control-band,
  .status-band,
  .leaderboard-shell,
  .detail-section {
    margin: 0 auto;
    max-width: 1500px;
  }

  .control-band {
    align-items: start;
    display: grid;
    gap: 20px;
    grid-template-columns: minmax(280px, 360px) minmax(0, 1fr);
    margin-bottom: 14px;
  }

  .brand-block {
    align-items: center;
    display: flex;
    gap: 16px;
  }

  .brand-mark {
    align-items: center;
    background: #171717;
    border-radius: 8px;
    color: #f5cf5a;
    display: inline-flex;
    font-size: 20px;
    font-weight: 800;
    height: 64px;
    justify-content: center;
    width: 64px;
  }

  .brand-copy p,
  .detail-header p {
    color: #875d3c;
    font-size: 13px;
    font-weight: 700;
    margin: 0 0 4px;
    text-transform: uppercase;
  }

  .brand-copy h1,
  .section-head h2,
  .detail-header h3 {
    line-height: 1.1;
    margin: 0;
  }

  .brand-copy h1 {
    font-size: 34px;
  }

  .brand-copy span,
  .section-head span,
  .status-band span,
  .detail-header span {
    color: #5f655f;
    display: block;
    font-size: 14px;
    margin-top: 6px;
    overflow-wrap: anywhere;
  }

  .filter-grid {
    display: grid;
    gap: 12px;
    grid-template-columns: repeat(6, minmax(0, 1fr));
  }

  label {
    color: #464d46;
    display: grid;
    font-size: 12px;
    font-weight: 700;
    gap: 6px;
    text-transform: uppercase;
  }

  label.wide {
    grid-column: span 2;
  }

  input,
  select,
  .api-pill,
  .leaderboard-row,
  .build-row,
  .component-card {
    background: #fffdf8;
    border: 1px solid #ddd4c9;
    border-radius: 8px;
  }

  input,
  select {
    color: #131313;
    min-height: 42px;
    padding: 0 12px;
  }

  .actions {
    align-items: end;
    display: flex;
    gap: 8px;
  }

  .actions button {
    border: 0;
    border-radius: 8px;
    cursor: pointer;
    font-weight: 800;
    min-height: 42px;
    padding: 0 16px;
  }

  .actions .primary {
    background: #171717;
    color: #f5cf5a;
  }

  .actions .secondary {
    background: #e6ded3;
    color: #171717;
  }

  .status-band {
    align-items: center;
    border-bottom: 1px solid #ddd4c9;
    display: flex;
    justify-content: space-between;
    margin-bottom: 16px;
    padding-bottom: 12px;
  }

  .status-band strong {
    display: block;
    font-size: 18px;
    margin-bottom: 4px;
  }

  .api-pill {
    align-items: center;
    color: #5f655f;
    display: inline-flex;
    font-size: 13px;
    font-weight: 800;
    min-height: 34px;
    padding: 0 12px;
  }

  .api-pill.ready {
    background: #eef6dd;
    border-color: #c8d56c;
    color: #405018;
  }

  .api-pill.error {
    background: #fff0ef;
    border-color: #ebb4ad;
    color: #a2372f;
  }

  .workspace {
    display: grid;
    gap: 20px;
    grid-template-columns: minmax(0, 1.05fr) minmax(360px, 0.95fr);
    margin: 0 auto;
    max-width: 1500px;
  }

  .section-head {
    border-bottom: 1px solid #ddd4c9;
    padding-bottom: 12px;
  }

  .section-head h2 {
    font-size: 24px;
  }

  .leaderboard-list,
  .distribution-list,
  .build-list {
    display: grid;
    gap: 10px;
    list-style: none;
    margin: 0;
    padding: 0;
  }

  .leaderboard-row,
  .build-row {
    align-items: center;
    color: inherit;
    cursor: pointer;
    display: grid;
    gap: 12px;
    padding: 14px;
    text-align: left;
    width: 100%;
  }

  .leaderboard-row {
    grid-template-columns: 56px 56px minmax(200px, 1.2fr) minmax(260px, 1fr) auto;
  }

  .leaderboard-row.selected,
  .build-row.selected {
    border-color: #171717;
    box-shadow: inset 0 0 0 1px #171717;
  }

  .rank {
    color: #c0532d;
    font-size: 18px;
    font-weight: 900;
  }

  .leaderboard-row img,
  .detail-header img,
  .component-card img {
    background: #f5f1e8;
    border: 1px solid #ddd4c9;
    border-radius: 8px;
    object-fit: contain;
  }

  .leaderboard-row img {
    height: 56px;
    padding: 4px;
    width: 56px;
  }

  .entity-copy {
    display: grid;
    gap: 4px;
    min-width: 0;
  }

  .entity-copy strong,
  .build-main strong {
    overflow-wrap: anywhere;
  }

  .entity-copy span,
  .entity-copy em,
  .build-main span,
  .distribution-copy span,
  .component-card span,
  .empty-panel p {
    color: #5f655f;
    font-size: 13px;
    margin: 0;
    overflow-wrap: anywhere;
  }

  .entity-copy em {
    font-style: normal;
  }

  .row-metrics,
  .summary-grid {
    display: grid;
    gap: 12px;
  }

  .row-metrics {
    grid-template-columns: repeat(5, minmax(0, 1fr));
  }

  .row-metrics div,
  .summary-grid div {
    display: grid;
    gap: 4px;
  }

  dt {
    color: #7b6654;
    font-size: 11px;
    font-weight: 700;
    margin: 0;
    text-transform: uppercase;
  }

  dd {
    font-size: 14px;
    font-weight: 800;
    margin: 0;
  }

  dd.positive {
    color: #2f6c44;
  }

  .confidence {
    align-self: start;
    border-radius: 999px;
    font-size: 12px;
    font-weight: 800;
    padding: 6px 10px;
    text-transform: uppercase;
  }

  .confidence.low {
    background: #f3ebe3;
    color: #825c2e;
  }

  .confidence.medium {
    background: #edf2dd;
    color: #536500;
  }

  .confidence.high {
    background: #e4f1ea;
    color: #2f6c44;
  }

  .detail-shell {
    display: grid;
    gap: 20px;
  }

  .detail-section {
    border-top: 1px solid #ddd4c9;
    padding-top: 4px;
  }

  .detail-header {
    align-items: center;
    display: grid;
    gap: 14px;
    grid-template-columns: auto minmax(0, 1fr);
    margin-top: 16px;
  }

  .detail-header img {
    height: 72px;
    padding: 6px;
    width: 72px;
  }

  .compact-header {
    grid-template-columns: minmax(0, 1fr);
  }

  .summary-grid {
    grid-template-columns: repeat(3, minmax(0, 1fr));
    margin: 18px 0 0;
  }

  .subsection {
    border-top: 1px solid #ddd4c9;
    margin-top: 18px;
    padding-top: 16px;
  }

  .subhead {
    align-items: baseline;
    display: flex;
    justify-content: space-between;
    margin-bottom: 10px;
  }

  .subhead h4 {
    font-size: 17px;
    margin: 0;
  }

  .build-row {
    gap: 10px;
  }

  .build-main {
    display: grid;
    gap: 4px;
  }

  .component-strip,
  .component-gallery {
    display: flex;
    flex-wrap: wrap;
    gap: 8px;
  }

  .component-strip span,
  .component-card {
    min-width: 0;
  }

  .component-strip span {
    background: #f3eee5;
    border-radius: 8px;
    font-size: 12px;
    padding: 6px 8px;
  }

  .distribution-row {
    display: grid;
    gap: 8px;
  }

  .distribution-copy {
    align-items: baseline;
    display: flex;
    justify-content: space-between;
    gap: 12px;
  }

  .bar-track {
    background: #e7dfd2;
    border-radius: 999px;
    height: 10px;
    overflow: hidden;
  }

  .bar-track span {
    background: linear-gradient(90deg, #171717, #d56f3a, #f1b64e);
    display: block;
    height: 100%;
  }

  .two-column {
    display: grid;
    gap: 16px;
    grid-template-columns: repeat(2, minmax(0, 1fr));
  }

  .component-gallery {
    display: grid;
    gap: 10px;
    grid-template-columns: repeat(3, minmax(0, 1fr));
  }

  .component-card {
    display: grid;
    gap: 8px;
    justify-items: start;
    min-height: 176px;
    padding: 12px;
  }

  .component-card img {
    height: 56px;
    padding: 4px;
    width: 56px;
  }

  .empty-panel {
    padding: 28px 0 8px;
  }

  .empty-panel h3 {
    margin: 0 0 8px;
  }

  .empty-copy {
    color: #5f655f;
    margin: 0;
  }

  .loading-list,
  .loading-block {
    margin-top: 18px;
  }

  .loading-row,
  .loading-block {
    animation: pulse 1.15s ease-in-out infinite;
    background: linear-gradient(90deg, #ece5d9, #fffdf8, #ece5d9);
    border-radius: 8px;
  }

  .loading-row {
    height: 92px;
  }

  .loading-block {
    height: 220px;
  }

  @keyframes pulse {
    0%,
    100% {
      opacity: 0.62;
    }
    50% {
      opacity: 1;
    }
  }

  @media (max-width: 1220px) {
    .workspace {
      grid-template-columns: 1fr;
    }

    .summary-grid,
    .two-column,
    .component-gallery {
      grid-template-columns: repeat(2, minmax(0, 1fr));
    }
  }

  @media (max-width: 920px) {
    .app-shell {
      padding: 14px;
    }

    .control-band {
      grid-template-columns: 1fr;
    }

    .filter-grid {
      grid-template-columns: repeat(2, minmax(0, 1fr));
    }

    label.wide {
      grid-column: span 2;
    }

    .leaderboard-row {
      grid-template-columns: 40px 48px minmax(0, 1fr);
    }

    .row-metrics {
      grid-column: 1 / -1;
      grid-template-columns: repeat(3, minmax(0, 1fr));
    }

    .confidence {
      justify-self: start;
    }

    .summary-grid,
    .two-column,
    .component-gallery {
      grid-template-columns: 1fr;
    }

    .status-band,
    .distribution-copy,
    .subhead {
      align-items: start;
      display: grid;
      gap: 6px;
      justify-content: start;
    }
  }
</style>
