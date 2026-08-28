<script lang="ts">
  import { onMount } from 'svelte';
  import { link } from 'svelte-spa-router';
  import active from 'svelte-spa-router/active';
  import { initTheme, toggleTheme, watchSystemTheme, type Theme } from '../theme';

  const navLinks: { href: string; label: string; activePath: string | RegExp }[] = [
    { href: '/', label: 'Home', activePath: '/' },
    { href: '/financial', label: 'Financial Performance', activePath: '/financial' },
    { href: '/vdt/expenses', label: 'Value Driver', activePath: /^\/(vdt|vdt-tree|diagnostic)(\/.*)?$/ },
    { href: '/ask', label: 'Ask Zeteo', activePath: '/ask' },
    { href: '/initiatives', label: 'Initiatives', activePath: '/initiatives' },
  ];

  const profileLinks: { label: string }[] = [
    { label: 'Your profile' },
    { label: 'Settings' },
    { label: 'Sign out' },
  ];

  let theme = $state<Theme>('light');

  onMount(() => {
    theme = initTheme();
    return watchSystemTheme((t) => (theme = t));
  });

  function handleToggleTheme() {
    theme = toggleTheme(theme);
  }

  function closeMobilePanel() {
    const el = document.getElementById('mobile-menu') as (HTMLElement & { hide?: () => void }) | null;
    el?.hide?.();
  }
</script>

<nav class="bg-indigo-600 dark:bg-indigo-800">
  <div class="shell">
    <div class="relative flex h-16 items-center justify-between">
      <div class="flex items-center px-2 lg:px-0">
        <a href="/" use:link class="shrink-0 text-xl font-black text-white no-underline">Zeteo</a>

        <div class="hidden lg:ml-10 lg:block">
          <div class="flex space-x-4">
            {#each navLinks as l (l.href)}
              <a
                href={l.href}
                use:link
                use:active={{ path: l.activePath, className: 'is-active' }}
                class="rounded-md px-3 py-2 text-sm font-medium text-white no-underline hover:bg-indigo-500/75 dark:hover:bg-indigo-700/75 [&.is-active]:bg-indigo-700 dark:[&.is-active]:bg-indigo-950/40"
              >
                {l.label}
              </a>
            {/each}
          </div>
        </div>
      </div>

      <div class="flex lg:hidden">
        <button
          type="button"
          command="--toggle"
          commandfor="mobile-menu"
          class="relative inline-flex items-center justify-center rounded-md bg-indigo-600 p-2 text-indigo-200 hover:bg-indigo-500/75 hover:text-white focus:outline-2 focus:outline-offset-2 focus:outline-white dark:bg-indigo-800 dark:hover:bg-indigo-700/75"
          aria-label="Open main menu"
        >
          <span aria-hidden="true" class="text-xl in-aria-expanded:hidden">☰</span>
          <span aria-hidden="true" class="text-xl not-in-aria-expanded:hidden">✕</span>
        </button>
      </div>

      <div class="hidden lg:ml-4 lg:block">
        <div class="flex items-center gap-4">
          <button
            type="button"
            class="relative rounded-full p-1 text-lg text-indigo-200 hover:text-white focus:outline-2 focus:outline-offset-2 focus:outline-white"
            onclick={handleToggleTheme}
            aria-label="Toggle dark mode"
          >
            {#if theme === 'dark'}☀{:else}☾{/if}
          </button>

          <el-dropdown class="relative">
            <button
              type="button"
              class="relative flex max-w-xs items-center rounded-full focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-white"
              aria-label="Open user menu"
            >
              <span class="flex size-8 items-center justify-center rounded-full bg-white/20 text-xs font-bold text-white outline -outline-offset-1 outline-white/10">ZU</span>
            </button>

            <el-menu
              anchor="bottom end"
              popover
              class="w-48 origin-top-right rounded-md bg-white py-1 shadow-lg outline-1 outline-black/5 transition transition-discrete [--anchor-gap:--spacing(2)] data-closed:scale-95 data-closed:transform data-closed:opacity-0 data-enter:duration-100 data-enter:ease-out data-leave:duration-75 data-leave:ease-in dark:bg-gray-800 dark:shadow-none dark:-outline-offset-1 dark:outline-white/10"
            >
              {#each profileLinks as p (p.label)}
                <button
                  type="button"
                  class="block w-full px-4 py-2 text-left text-sm text-gray-700 focus:bg-gray-100 focus:outline-hidden dark:text-gray-200 dark:focus:bg-white/5"
                >
                  {p.label}
                </button>
              {/each}
            </el-menu>
          </el-dropdown>
        </div>
      </div>
    </div>
  </div>

  <el-disclosure id="mobile-menu" hidden class="block lg:hidden">
    <div class="space-y-1 px-2 pt-2 pb-3 sm:px-3">
      {#each navLinks as l (l.href)}
        <a
          href={l.href}
          use:link
          use:active={{ path: l.activePath, className: 'is-active' }}
          onclick={closeMobilePanel}
          class="block rounded-md px-3 py-2 text-base font-medium text-white no-underline hover:bg-indigo-500/75 dark:hover:bg-indigo-700/75 [&.is-active]:bg-indigo-700 dark:[&.is-active]:bg-indigo-950/40"
        >
          {l.label}
        </a>
      {/each}
    </div>
    <div class="border-t border-indigo-700 pt-4 pb-3 dark:border-indigo-800">
      <div class="space-y-1 px-2">
        <button
          type="button"
          class="block w-full rounded-md px-3 py-2 text-left text-base font-medium text-white hover:bg-indigo-500/75 dark:hover:bg-indigo-700/75"
          onclick={handleToggleTheme}
        >
          {theme === 'dark' ? '☀ Switch to light mode' : '☾ Switch to dark mode'}
        </button>
        {#each profileLinks as p (p.label)}
          <button
            type="button"
            class="block w-full rounded-md px-3 py-2 text-left text-base font-medium text-white hover:bg-indigo-500/75 dark:hover:bg-indigo-700/75"
            onclick={closeMobilePanel}
          >
            {p.label}
          </button>
        {/each}
      </div>
    </div>
  </el-disclosure>
</nav>
