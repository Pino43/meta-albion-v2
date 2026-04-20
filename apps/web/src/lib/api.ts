import { apiBaseUrl } from '$lib/config';

export const regions = ['all', 'europe', 'americas', 'asia'] as const;
export const perspectives = ['killer', 'victim', 'participant'] as const;
export const slots = [
  'main_hand',
  'off_hand',
  'head',
  'armor',
  'shoes',
  'bag',
  'cape',
  'mount',
  'potion',
  'food'
] as const;

export type Region = (typeof regions)[number];
export type Perspective = (typeof perspectives)[number];
export type Slot = (typeof slots)[number];
export type RankingMode = 'items' | 'builds';

export type ItemRanking = {
  item_type: string;
  uses: number;
  events: number;
  avg_item_power: number | null;
  avg_participants: number | null;
  total_kill_fame: number;
};

export type BuildRanking = {
  build_key: string;
  uses: number;
  events: number;
  avg_item_power: number | null;
  avg_participants: number | null;
  total_kill_fame: number;
};

export type RankingMeta = {
  days: number;
  region: string | null;
  perspective: string;
  limit: number;
  slot?: string;
  generated_at?: string;
  cache_ttl_sec?: number;
};

export type RankingResponse<T> = {
  data: T[];
  meta: RankingMeta;
};

export type RankingFilters = {
  mode: RankingMode;
  slot: Slot;
  days: number;
  region: Region;
  perspective: Perspective;
  limit: number;
};

function paramsFor(filters: RankingFilters): URLSearchParams {
  const params = new URLSearchParams({
    days: String(filters.days),
    perspective: filters.perspective,
    limit: String(filters.limit)
  });
  if (filters.region !== 'all') {
    params.set('region', filters.region);
  }
  if (filters.mode === 'items') {
    params.set('slot', filters.slot);
  }
  return params;
}

export async function fetchRankings(
  filters: RankingFilters,
  fetcher: typeof fetch = fetch
): Promise<RankingResponse<ItemRanking | BuildRanking>> {
  if (!apiBaseUrl) {
    throw new Error('PUBLIC_API_BASE_URL is not configured');
  }
  const path = filters.mode === 'items' ? '/v1/rankings/items' : '/v1/rankings/builds';
  const response = await fetcher(`${apiBaseUrl}${path}?${paramsFor(filters).toString()}`);
  if (!response.ok) {
    throw new Error(`API request failed with ${response.status}`);
  }
  return response.json();
}
