export const dashboardSlots = ['main_hand', 'head', 'armor', 'shoes'] as const;

export type DashboardSlot = (typeof dashboardSlots)[number];

export const slotLabels: Record<DashboardSlot, string> = {
  main_hand: 'Weapons',
  head: 'Head',
  armor: 'Chest',
  shoes: 'Shoes'
};

export const slotHeadings: Record<DashboardSlot, string> = {
  main_hand: 'Weapon rankings',
  head: 'Head armor rankings',
  armor: 'Chest armor rankings',
  shoes: 'Shoes rankings'
};

export function isDashboardSlot(value: string): value is DashboardSlot {
  return dashboardSlots.includes(value as DashboardSlot);
}
