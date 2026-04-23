<script lang="ts">
  import { page } from '$app/stores';

  import { dashboardSlots, slotLabels } from '$lib/slots';

  const navItems = dashboardSlots.map((slot) => ({
    slot,
    label: slotLabels[slot],
    href: slot === 'main_hand' ? '/' : `/items/${slot}`
  }));

  function isActive(href: string): boolean {
    const pathname = $page.url.pathname;
    return href === '/' ? pathname === '/' : pathname.startsWith(href);
  }
</script>

<div class="app-shell">
  <header class="site-header">
    <a class="brand" href="/">
      <span class="brand-mark">AA</span>
      <span class="brand-copy">
        <strong>Albion Analytics</strong>
        <small>Meta dashboard</small>
      </span>
    </a>

    <nav class="site-nav" aria-label="Primary">
      {#each navItems as item}
        <a class:active={isActive(item.href)} href={item.href}>{item.label}</a>
      {/each}
    </nav>
  </header>

  <div class="page-frame">
    <slot />
  </div>
</div>

<style>
  :global(:root) {
    --page-width: 1240px;
    --bg: #ece9e2;
    --surface: #f8f6f1;
    --surface-muted: #f0ede6;
    --surface-strong: #101010;
    --line: #d7d0c4;
    --line-strong: #242321;
    --text: #111111;
    --text-soft: #696258;
    --accent: #c7942f;
  }

  :global(*) {
    box-sizing: border-box;
  }

  :global(body) {
    margin: 0;
    background:
      linear-gradient(180deg, #0f0f10 0 88px, transparent 88px),
      var(--bg);
    color: var(--text);
    font-family: 'IBM Plex Sans', 'Segoe UI Variable Text', 'Segoe UI', sans-serif;
  }

  :global(button),
  :global(input),
  :global(select) {
    font: inherit;
  }

  :global(a) {
    color: inherit;
  }

  .app-shell {
    min-height: 100vh;
  }

  .site-header {
    align-items: center;
    display: flex;
    gap: 24px;
    justify-content: space-between;
    margin: 0 auto;
    max-width: var(--page-width);
    padding: 18px 14px;
  }

  .brand {
    align-items: center;
    color: #f6f2e9;
    display: flex;
    gap: 12px;
    min-width: 0;
    text-decoration: none;
  }

  .brand-mark {
    align-items: center;
    background: var(--accent);
    color: #1a1205;
    display: inline-flex;
    font-size: 13px;
    font-weight: 800;
    height: 38px;
    justify-content: center;
    width: 38px;
  }

  .brand-copy {
    display: grid;
    gap: 2px;
  }

  .brand-copy strong {
    font-size: 15px;
    line-height: 1.1;
  }

  .brand-copy small {
    color: #c2b9aa;
    font-size: 11px;
    letter-spacing: 0.08em;
    text-transform: uppercase;
  }

  .site-nav {
    display: flex;
    flex-wrap: wrap;
    gap: 8px;
  }

  .site-nav a {
    border: 1px solid #36322c;
    color: #d8d0c3;
    font-size: 12px;
    font-weight: 700;
    min-height: 38px;
    padding: 0 14px;
    display: inline-flex;
    align-items: center;
    text-decoration: none;
    text-transform: uppercase;
    letter-spacing: 0.04em;
  }

  .site-nav a.active {
    background: var(--accent);
    border-color: var(--accent);
    color: #201708;
  }

  .page-frame {
    margin: 0 auto;
    max-width: var(--page-width);
    padding: 12px 14px 28px;
  }

  @media (max-width: 860px) {
    .site-header {
      align-items: start;
      flex-direction: column;
    }

    .site-nav {
      width: 100%;
    }

    .site-nav a {
      flex: 1 1 calc(50% - 8px);
      justify-content: center;
    }
  }
</style>
