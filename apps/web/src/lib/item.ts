import { EXACT_LABELS, TOKEN_LABELS, WORD_LABELS } from '$lib/item-labels';

export type ParsedItem = {
  itemType: string;
  tier: string;
  enchantment: string;
  label: string;
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

export function familyKeyFromItemType(itemType: string): string {
  const [base] = itemType.split('@');
  const normalized = base.replace(/^T\d+_?/, '');
  return normalized || itemType;
}

export function labelForFamilyKey(familyKey: string): string {
  return EXACT_LABELS[familyKey] ?? (fallbackLabel(familyKey) || familyKey);
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
