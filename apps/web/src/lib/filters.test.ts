import { describe, expect, it } from 'vitest';

import {
  applyDraft,
  defaultFilters,
  draftFromFilters,
  filtersFromParams,
  filtersToParams,
  summarizeFilters
} from '$lib/filters';

describe('filters', () => {
  it('round-trips the main filter state through draft and query params', () => {
    const filters = {
      days: 14,
      region: 'asia' as const,
      patchId: null,
      contentType: 'all' as const,
      fightScale: 'duo' as const,
      limit: 50,
      minSample: 100
    };

    const draft = draftFromFilters(filters);
    expect(applyDraft(draft)).toEqual(filters);

    const params = filtersToParams(filters);
    expect(filtersFromParams(params)).toEqual(filters);
  });

  it('falls back to defaults for invalid search params', () => {
    const params = new URLSearchParams('days=999&region=moon&limit=999&min_sample=999');

    expect(filtersFromParams(params)).toEqual(defaultFilters());
  });

  it('builds a compact summary string', () => {
    const filters = {
      ...defaultFilters(),
      region: 'europe' as const,
      fightScale: 'small_party' as const
    };

    expect(summarizeFilters(filters)).toContain('7d window');
    expect(summarizeFilters(filters)).toContain('Europe');
    expect(summarizeFilters(filters)).toContain('small party');
  });
});
