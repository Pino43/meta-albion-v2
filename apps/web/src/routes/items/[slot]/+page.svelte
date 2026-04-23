<svelte:options runes={false} />

<script lang="ts">
  import SlotLeaderboardPage from '$lib/components/SlotLeaderboardPage.svelte';
  import type { DashboardSlot } from '$lib/slots';

  export let data: { slot: DashboardSlot };
</script>

<SlotLeaderboardPage slot={data.slot} />
