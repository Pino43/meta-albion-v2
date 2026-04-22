export type ParsedItem = {
  itemType: string;
  tier: string;
  enchantment: string;
  label: string;
};

const EXACT_LABELS: Record<string, string> = {
  MAIN_SWORD: 'Broadsword',
  MAIN_AXE: 'Battleaxe',
  MAIN_MACE: 'Mace',
  MAIN_HAMMER: 'Hammer',
  MAIN_SPEAR: 'Spear',
  MAIN_BOW: 'Bow',
  MAIN_CROSSBOW: 'Crossbow',
  MAIN_DAGGER: 'Dagger',
  MAIN_FIRESTAFF: 'Fire Staff',
  MAIN_FROSTSTAFF: 'Frost Staff',
  MAIN_ARCANESTAFF: 'Arcane Staff',
  MAIN_CURSEDSTAFF: 'Cursed Staff',
  MAIN_HOLYSTAFF: 'Holy Staff',
  MAIN_NATURESTAFF: 'Nature Staff',
  '2H_CLAYMORE': 'Claymore',
  '2H_DUALSWORD': 'Dual Swords',
  '2H_AXE': 'Greataxe',
  '2H_MACE': 'Heavy Mace',
  '2H_HAMMER': 'Great Hammer',
  '2H_SPEAR': 'Pike',
  '2H_BOW': 'Warbow',
  '2H_CROSSBOW': 'Heavy Crossbow',
  '2H_DAGGERPAIR': 'Dagger Pair',
  '2H_FIRESTAFF': 'Great Fire Staff',
  '2H_FROSTSTAFF': 'Great Frost Staff',
  '2H_ARCANESTAFF': 'Great Arcane Staff',
  '2H_CURSEDSTAFF': 'Great Cursed Staff',
  '2H_HOLYSTAFF': 'Great Holy Staff',
  '2H_NATURESTAFF': 'Great Nature Staff'
};

const TOKEN_LABELS: Array<[string, string]> = [
  ['DOUBLEBLADEDSTAFF', 'Double-Bladed Staff'],
  ['QUARTERSTAFF', 'Quarterstaff'],
  ['CROSSBOW', 'Crossbow'],
  ['ARCANESTAFF', 'Arcane Staff'],
  ['CURSEDSTAFF', 'Cursed Staff'],
  ['FROSTSTAFF', 'Frost Staff'],
  ['FIRESTAFF', 'Fire Staff'],
  ['HOLYSTAFF', 'Holy Staff'],
  ['NATURESTAFF', 'Nature Staff'],
  ['DAGGERPAIR', 'Dagger Pair'],
  ['SHAPESHIFTER', 'Shapeshifter'],
  ['CLAYMORE', 'Claymore'],
  ['DUALSWORD', 'Dual Swords'],
  ['SCIMITAR', 'Scimitar'],
  ['CLEAVER', 'Cleaver'],
  ['INFERNOSTAFF', 'Inferno Staff'],
  ['BATTLEBRACERS', 'Battle Bracers'],
  ['SPIKEDGAUNTLETS', 'Spiked Gauntlets'],
  ['POTION', 'Potion'],
  ['MEAL', 'Meal']
];

const WORD_LABELS: Record<string, string> = {
  MAIN: '1H',
  OFF: 'Off',
  HAND: 'Hand',
  TWO: 'Two',
  ONE: 'One',
  AXE: 'Axe',
  SWORD: 'Sword',
  HAMMER: 'Hammer',
  MACE: 'Mace',
  SPEAR: 'Spear',
  BOW: 'Bow',
  DAGGER: 'Dagger',
  STAFF: 'Staff',
  SHIELD: 'Shield',
  TORCH: 'Torch',
  BOOK: 'Book',
  ORB: 'Orb',
  CAPE: 'Cape',
  BAG: 'Bag',
  ARMOR: 'Armor',
  SHOES: 'Shoes',
  HEAD: 'Head',
  PLATE: 'Plate',
  LEATHER: 'Leather',
  CLOTH: 'Cloth',
  AVALON: 'Avalonian',
  MORGANA: 'Morgana',
  UNDEAD: 'Undead',
  ROYAL: 'Royal',
  KEEPER: 'Keeper',
  HELL: 'Hell',
  CRYSTAL: 'Crystal',
  DEMONIC: 'Demonic',
  DRUIDIC: 'Druidic',
  MALEFACTION: 'Malefaction',
  GREATAXE: 'Greataxe'
};

function titleizeWord(value: string): string {
  return value.toLowerCase().replace(/\b\w/g, (char) => char.toUpperCase());
}

function fallbackLabel(base: string): string {
  let normalized = base;
  for (const [token, replacement] of TOKEN_LABELS) {
    normalized = normalized.replaceAll(token, replacement);
  }

  return normalized
    .split('_')
    .filter(Boolean)
    .map((part) => WORD_LABELS[part] ?? titleizeWord(part))
    .join(' ')
    .replace(/\b1h\b/gi, '1H')
    .replace(/\b2h\b/gi, '2H')
    .trim();
}

export function parseItemType(itemType: string): ParsedItem {
  const [base, enchantmentRaw] = itemType.split('@');
  const tierMatch = /^T(\d+)/.exec(base);
  const tier = tierMatch ? `T${tierMatch[1]}` : 'Unknown';
  const enchantment = enchantmentRaw ? `.${enchantmentRaw}` : '.0';
  const normalizedBase = base.replace(/^T\d+_?/, '');
  const label = EXACT_LABELS[normalizedBase] ?? fallbackLabel(normalizedBase);

  return {
    itemType,
    tier,
    enchantment,
    label: label || itemType
  };
}

export function itemImageUrl(itemType: string): string {
  return `https://render.albiononline.com/v1/item/${encodeURIComponent(itemType)}.png`;
}

export function mainItemFromBuildKey(buildKey: string): string | null {
  const parts = buildKey.split('|').filter(Boolean);
  return parts[3] || parts[0] || null;
}
