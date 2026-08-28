<script lang="ts">
  import type { BusinessUnit } from '../data/types';
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

  $effect(() => {
    if (defaulted || status !== 'ready' || !inputEl || businessUnits.length === 0) return;
    defaulted = true;
    const fallback = businessUnits.find((bu) => bu.code === 'AET') ?? businessUnits[0];
    inputEl.value = fallback.label;
  });
</script>

<div class="flex items-center gap-1.5">
  <span class="text-xs whitespace-nowrap text-gray-500 dark:text-gray-400">Business:</span>

  <Autocomplete
    id="business-autocomplete"
    ariaLabel="Business"
    placeholder="Search business or company…"
    wrapperClass="w-64"
    bind:inputEl
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
          class="block truncate px-3 py-2 font-semibold text-gray-900 select-none aria-selected:bg-indigo-600 aria-selected:text-white dark:text-gray-300 dark:aria-selected:bg-indigo-500"
        >
          {bu.label}
        </el-option>
        {#each bu.companies as company (company.code)}
          <el-option
            value={company.name}
            class="block truncate py-2 pr-3 pl-6 text-gray-900 select-none aria-selected:bg-indigo-600 aria-selected:text-white dark:text-gray-300 dark:aria-selected:bg-indigo-500"
          >
            {company.name}
          </el-option>
        {/each}
      {/each}
    {/if}
  </Autocomplete>
</div>
