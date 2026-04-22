import { describe, expect, it } from 'vitest';

import { mainItemFromBuildKey, parseItemType } from './item';

describe('parseItemType', () => {
  it('extracts tier and enchantment from Albion item ids', () => {
    expect(parseItemType('T7_2H_AXE_AVALON@3')).toEqual({
      itemType: 'T7_2H_AXE_AVALON@3',
      tier: 'T7',
      enchantment: '.3',
      label: '2H Axe Avalonian'
    });
  });

  it('uses .0 enchantment when the id has no enchantment suffix', () => {
    expect(parseItemType('T6_BAG').enchantment).toBe('.0');
  });

  it('uses curated labels for common main-hand weapons', () => {
    expect(parseItemType('T4_MAIN_SWORD').label).toBe('Broadsword');
    expect(parseItemType('T4_2H_FIRESTAFF').label).toBe('Great Fire Staff');
  });
});

describe('mainItemFromBuildKey', () => {
  it('uses the main hand position from normalized build keys', () => {
    expect(mainItemFromBuildKey('head|armor|shoes|T4_MAIN_SWORD|offhand|cape')).toBe(
      'T4_MAIN_SWORD'
    );
  });
});
