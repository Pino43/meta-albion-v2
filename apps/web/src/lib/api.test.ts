import { describe, expect, it } from 'vitest';

import { buildDetailQuery, buildLeaderboardQuery } from './api';

describe('buildLeaderboardQuery', () => {
  it('includes only active leaderboard filters', () => {
    const query = buildLeaderboardQuery({
      days: 14,
      region: 'asia',
      patchId: 3,
      contentType: 'mists',
      fightScale: 'duo',
      killArea: 'Mist Prime',
      limit: 20,
      minSample: 25
    });

    expect(query.toString()).toBe(
      'days=14&region=asia&patch_id=3&content_type=mists&fight_scale=duo&kill_area=Mist+Prime&limit=20&min_sample=25'
    );
  });

  it('drops optional all/empty filters', () => {
    const query = buildLeaderboardQuery({
      days: 7,
      region: 'all',
      patchId: null,
      contentType: 'all',
      fightScale: 'all',
      killArea: '   ',
      limit: 10,
      minSample: 0
    });

    expect(query.toString()).toBe('days=7&limit=10&min_sample=0');
  });
});

describe('buildDetailQuery', () => {
  it('matches shared detail filter shape', () => {
    const query = buildDetailQuery({
      days: 30,
      region: 'europe',
      patchId: null,
      contentType: 'roads',
      fightScale: 'small_party',
      killArea: 'Avalon Path'
    });

    expect(query.toString()).toBe(
      'days=30&region=europe&content_type=roads&fight_scale=small_party&kill_area=Avalon+Path'
    );
  });
});
