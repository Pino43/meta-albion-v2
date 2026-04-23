import { error } from '@sveltejs/kit';

import { isDashboardSlot } from '$lib/slots';

export const prerender = false;

export function load({ params }: { params: { slot: string } }) {
  if (!isDashboardSlot(params.slot)) {
    throw error(404, 'Not found');
  }

  return {
    slot: params.slot
  };
}
