export type ParsedItem = {
  itemType: string;
  tier: string;
  enchantment: string;
  label: string;
};

export function parseItemType(itemType: string): ParsedItem {
  const [base, enchantmentRaw] = itemType.split('@');
  const tierMatch = /^T(\d+)/.exec(base);
  const tier = tierMatch ? `T${tierMatch[1]}` : 'Unknown';
  const enchantment = enchantmentRaw ? `.${enchantmentRaw}` : '.0';
  const label = base
    .replace(/^T\d+_?/, '')
    .replaceAll('_', ' ')
    .toLowerCase()
    .replace(/\b\w/g, (char) => char.toUpperCase());

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
