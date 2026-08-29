<script lang="ts">
  import type { BusinessUnit } from '../data/types';
  import { scopeState } from '../state/scope.svelte';
  import { loadScope } from '../data/gl-store.svelte';
  import Autocomplete from './Autocomplete.svelte';

  let status = $state<'loading' | 'error' | 'ready'>('loading');
  let businessUnits = $state<BusinessUnit[]>([]);
  let inputEl = $state<HTMLInputElement | null>(null);
  let defaulted = false;

  async function load() {
    status = 'loading';
    try {
      const res = await fetch('/api/companies');
      if (!res.ok) throw new Error(`Request failed: ${res.status}`);
      const data = await res.json();
      businessUnits = data.businessUnits ?? [];
      status = 'ready';
    } catch (err) {
      console.error('Failed to load MISC companies', err);
      status = 'error';
    }
  }

  load();

  // Only sets the input's display text to match whatever scope is already
  // selected (loaded independently — see App.svelte) — this component isn't
  // always mounted (routes hide ContextBar while their own data is loading),
  // so it must never be the sole trigger for the initial GL tree fetch.
  $effect(() => {
    if (defaulted || status !== 'ready' || !inputEl || businessUnits.length === 0) return;
    defaulted = true;
    const fallback = businessUnits.find((bu) => bu.code === scopeState.code) ?? businessUnits[0];
    inputEl.value = fallback.label;
    if (fallback.code !== scopeState.code) {
      scopeState.set(fallback.code, fallback.label);
      loadScope(fallback.code);
    }
  });

  function handleSelect(option: HTMLElement): void {
    const code = option.dataset.code;
    const label = option.textContent?.trim() ?? code;
    if (!code || !label) return;
    scopeState.set(code, label);
    loadScope(code);
  }
</script>

<div class="flex items-center gap-1.5">
  <span class="text-xs whitespace-nowrap text-gray-500 dark:text-gray-400">Business:</span>

  <Autocomplete
    id="business-autocomplete"
    ariaLabel="Business"
    placeholder="Search business or company…"
    wrapperClass="w-64"
    bind:inputEl
    onselect={handleSelect}
  >
    {#if status === 'loading'}
      <div class="px-3 py-2 text-sm text-gray-500 dark:text-gray-400">Loading…</div>
    {:else if status === 'error'}
      <div class="px-3 py-2 text-sm text-gray-500 dark:text-gray-400">
        Couldn't load companies.
        <button type="button" class="ml-2 cursor-pointer border-0 bg-transparent p-0 text-indigo-600 underline dark:text-indigo-400" onclick={load}>Retry</button>
      </div>
    {:else}
      {#each businessUnits as bu (bu.code)}
        <el-option
          value={bu.label}
          data-code={bu.code}
          class="block truncate px-3 py-2 font-semibold text-gray-900 select-none aria-selected:bg-indigo-600 aria-selected:text-white dark:text-gray-300 dark:aria-selected:bg-indigo-500"
        >
          {bu.label}
        </el-option>
        {#each bu.companies as company (company.code)}
          <el-option
            value={company.name}
            data-code={company.code}
            class="block truncate py-2 pr-3 pl-6 text-gray-900 select-none aria-selected:bg-indigo-600 aria-selected:text-white dark:text-gray-300 dark:aria-selected:bg-indigo-500"
          >
            {company.name}
          </el-option>
        {/each}
      {/each}
    {/if}
  </Autocomplete>
</div>
