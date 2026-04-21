import { getApiBaseUrl } from '$lib/config';

export const regions = ['all', 'europe', 'americas', 'asia'] as const;
export const contentTypes = [
  'all',
  'corrupted_dungeon',
  'mists',
  'hellgate',
  'roads',
  'abyssal',
  'unknown'
] as const;
export const fightScales = [
  'all',
  'solo',
  'duo',
  'small_party',
  'party',
  'large_party',
  'zvz',
  'unknown'
] as const;

export type Region = (typeof regions)[number];
export type ContentTypeFilter = (typeof contentTypes)[number];
export type FightScaleFilter = (typeof fightScales)[number];
export type Confidence = 'low' | 'medium' | 'high';

export type ApiMeta = {
  generated_at?: string;
  cache_ttl_sec?: number;
  days?: number;
  region?: string | null;
  patch_id?: number | null;
  content_type?: string | null;
  fight_scale?: string | null;
  kill_area?: string | null;
  limit?: number;
  min_sample?: number;
  slot?: string;
  item_type?: string;
  build_key?: string;
};

export type ApiResponse<T> = {
  data: T;
  meta: ApiMeta;
};

export type OutcomeMetrics = {
  kill_credit: number;
  death_count: number;
  appearance_count: number;
  event_count: number;
  avg_item_power: number | null;
  total_kill_fame: number;
  kill_side_rate: number;
  kd_ratio: number | null;
  sample: number;
  pick_rate?: number;
  baseline_rate?: number;
  adjusted_score: number;
  confidence: Confidence;
};

export type BuildComponents = {
  head_type: string | null;
  armor_type: string | null;
  shoes_type: string | null;
  main_hand_type: string | null;
  off_hand_type: string | null;
  cape_type: string | null;
};

export type MainHandLeaderboardRow = OutcomeMetrics & {
  item_type: string;
  top_build_key: string | null;
};

export type BuildSummary = OutcomeMetrics & {
  build_key: string;
  components?: BuildComponents;
};

export type DistributionRow = OutcomeMetrics & {
  content_type?: string;
  fight_scale?: string;
  patch_id?: number | null;
};

export type ItemDetail = {
  slot: string;
  item_type: string;
  summary: OutcomeMetrics;
  distributions: {
    by_content_type: DistributionRow[];
    by_fight_scale: DistributionRow[];
    by_patch: DistributionRow[];
  };
  builds: {
    representative_build: BuildSummary | null;
    top_builds: BuildSummary[];
  };
};

export type BuildDetail = {
  build_key: string;
  components: BuildComponents;
  summary: OutcomeMetrics;
  distributions: {
    by_content_type: DistributionRow[];
    by_fight_scale: DistributionRow[];
    by_patch: DistributionRow[];
  };
};

export type LeaderboardFilters = {
  days: number;
  region: Region;
  patchId: number | null;
  contentType: ContentTypeFilter;
  fightScale: FightScaleFilter;
  killArea: string;
  limit: number;
  minSample: number;
};

export type DetailFilters = Omit<LeaderboardFilters, 'limit' | 'minSample'>;

function appendOptional(params: URLSearchParams, key: string, value: string | number | null) {
  if (value === null) return;
  const normalized = String(value).trim();
  if (normalized) {
    params.set(key, normalized);
  }
}

function appendSharedFilters(params: URLSearchParams, filters: DetailFilters) {
  params.set('days', String(filters.days));
  if (filters.region !== 'all') {
    params.set('region', filters.region);
  }
  appendOptional(params, 'patch_id', filters.patchId);
  if (filters.contentType !== 'all') {
    params.set('content_type', filters.contentType);
  }
  if (filters.fightScale !== 'all') {
    params.set('fight_scale', filters.fightScale);
  }
  if (filters.killArea.trim()) {
    params.set('kill_area', filters.killArea.trim());
  }
}

export function buildLeaderboardQuery(filters: LeaderboardFilters): URLSearchParams {
  const params = new URLSearchParams();
  appendSharedFilters(params, filters);
  params.set('limit', String(filters.limit));
  params.set('min_sample', String(filters.minSample));
  return params;
}

export function buildDetailQuery(filters: DetailFilters): URLSearchParams {
  const params = new URLSearchParams();
  appendSharedFilters(params, filters);
  return params;
}

async function fetchJson<T>(
  path: string,
  params: URLSearchParams,
  fetcher: typeof fetch = fetch
): Promise<ApiResponse<T>> {
  const apiBaseUrl = getApiBaseUrl();
  if (!apiBaseUrl) {
    throw new Error('PUBLIC_API_BASE_URL is not configured');
  }
  const response = await fetcher(`${apiBaseUrl}${path}?${params.toString()}`);
  if (!response.ok) {
    throw new Error(`API request failed with ${response.status}`);
  }
  return response.json();
}

export function fetchLeaderboard(
  filters: LeaderboardFilters,
  fetcher: typeof fetch = fetch
): Promise<ApiResponse<MainHandLeaderboardRow[]>> {
  return fetchJson('/v1/leaderboards/main-hands', buildLeaderboardQuery(filters), fetcher);
}

export function fetchItemDetail(
  slot: string,
  itemType: string,
  filters: DetailFilters,
  fetcher: typeof fetch = fetch
): Promise<ApiResponse<ItemDetail>> {
  return fetchJson(
    `/v1/items/${encodeURIComponent(slot)}/${encodeURIComponent(itemType)}`,
    buildDetailQuery(filters),
    fetcher
  );
}

export function fetchBuildDetail(
  buildKey: string,
  filters: DetailFilters,
  fetcher: typeof fetch = fetch
): Promise<ApiResponse<BuildDetail>> {
  return fetchJson(
    `/v1/builds/${encodeURIComponent(buildKey)}`,
    buildDetailQuery(filters),
    fetcher
  );
}
