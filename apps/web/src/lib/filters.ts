import {
  contentTypes,
  fightScales,
  regions,
  type ContentTypeFilter,
  type DetailFilters,
  type FightScaleFilter,
  type LeaderboardFilters,
  type Region
} from '$lib/api';

export type FilterDraft = {
  days: number;
  region: Region;
  patchIdInput: string;
  contentType: ContentTypeFilter;
  fightScale: FightScaleFilter;
  limit: number;
  minSample: number;
};

export const dayOptions = [1, 7, 14, 30] as const;
export const limitOptions = [10, 20, 50, 100] as const;
export const minSampleOptions = [0, 25, 100, 250] as const;

export function defaultFilters(): LeaderboardFilters {
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

export function draftFromFilters(value: LeaderboardFilters): FilterDraft {
  return {
    days: value.days,
    region: value.region,
    patchIdInput: '',
    contentType: 'all',
    fightScale: value.fightScale,
    limit: value.limit,
    minSample: value.minSample
  };
}

export function filtersFromParams(params: URLSearchParams): LeaderboardFilters {
  const fallback = defaultFilters();
  return {
    days: parseNumberChoice(params.get('days'), dayOptions, fallback.days),
    region: parseChoice(params.get('region'), regions, fallback.region),
    patchId: null,
    contentType: 'all',
    fightScale: parseChoice(params.get('fight_scale'), fightScales, fallback.fightScale),
    limit: parseNumberChoice(params.get('limit'), limitOptions, fallback.limit),
    minSample: parseNumberChoice(params.get('min_sample'), minSampleOptions, fallback.minSample)
  };
}

export function applyDraft(value: FilterDraft): LeaderboardFilters {
  return {
    days: value.days,
    region: value.region,
    patchId: null,
    contentType: 'all',
    fightScale: value.fightScale,
    limit: value.limit,
    minSample: value.minSample
  };
}

export function detailFiltersFrom(value: LeaderboardFilters): DetailFilters {
  return {
    days: value.days,
    region: value.region,
    patchId: value.patchId,
    contentType: value.contentType,
    fightScale: value.fightScale
  };
}

export function filtersToParams(value: LeaderboardFilters): URLSearchParams {
  const fallback = defaultFilters();
  const params = new URLSearchParams();
  params.set('days', String(value.days));
  if (value.region !== 'all') params.set('region', value.region);
  if (value.fightScale !== 'all') params.set('fight_scale', value.fightScale);
  if (value.limit !== fallback.limit) params.set('limit', String(value.limit));
  if (value.minSample !== fallback.minSample) params.set('min_sample', String(value.minSample));
  return params;
}

export function summarizeFilters(value: LeaderboardFilters): string {
  return [`${value.days}d window`, regionLabel(value.region), fightScaleLabel(value.fightScale)].join(
    ' / '
  );
}

export function regionLabel(value: Region): string {
  if (value === 'all') return 'All regions';
  return value.charAt(0).toUpperCase() + value.slice(1);
}

export function contentTypeLabel(value: ContentTypeFilter): string {
  if (value === 'all') return 'All content';
  if (value === 'open_world') return 'Open world';
  return value.replaceAll('_', ' ');
}

export function fightScaleLabel(value: FightScaleFilter): string {
  if (value === 'all') return 'All scales';
  return value.replaceAll('_', ' ');
}

export function sanitizeText(value: string | null): string | null {
  const normalized = value?.trim();
  return normalized ? normalized : null;
}

export function parsePatchId(value: string): number | null {
  const parsed = Number.parseInt(value, 10);
  return Number.isFinite(parsed) && parsed >= 0 ? parsed : null;
}

function parseChoice<T extends string>(value: string | null, allowed: readonly T[], fallback: T): T {
  return value && allowed.includes(value as T) ? (value as T) : fallback;
}

function parseNumberChoice(value: string | null, allowed: readonly number[], fallback: number): number {
  const parsed = Number(value);
  return allowed.includes(parsed) ? parsed : fallback;
}
