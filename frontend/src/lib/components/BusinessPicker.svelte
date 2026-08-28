<script lang="ts">
  import { clickOutside } from '../actions/clickOutside';
  import type { BusinessUnit } from '../data/types';

  let open = $state(false);
  let status = $state<'loading' | 'error' | 'ready'>('loading');
  let businessUnits = $state<BusinessUnit[]>([]);
  let expandedBu = $state<string | null>(null);
  let selectedLabel = $state('AET');
  let selectedBuCode = $state('AET');
  let selectedCompanyCode = $state<string | null>(null);

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

  function close() {
    open = false;
  }

  function toggleBu(code: string) {
    expandedBu = expandedBu === code ? null : code;
  }

  function selectBu(bu: BusinessUnit) {
    selectedBuCode = bu.code;
    selectedCompanyCode = null;
    selectedLabel = bu.label;
    close();
  }

  function selectCompany(bu: BusinessUnit, companyCode: string, companyName: string) {
    selectedBuCode = bu.code;
    selectedCompanyCode = companyCode;
    selectedLabel = companyName;
    close();
  }
</script>

<div class="relative inline-block" use:clickOutside={close}>
  <button
    type="button"
    class="flex items-center gap-1.5 text-xs cursor-pointer bg-white dark:bg-gray-800 text-gray-700 dark:text-gray-300 border border-gray-200 dark:border-gray-700 rounded-lg py-0.5 px-2.5 whitespace-nowrap focus-visible:outline-2 focus-visible:-outline-offset-2 focus-visible:outline-indigo-600 dark:focus-visible:outline-indigo-500 aria-expanded:border-indigo-600 dark:aria-expanded:border-indigo-500"
    onclick={() => (open = !open)}
    aria-expanded={open}
    aria-haspopup="tree"
  >
    <span>Business: {selectedLabel}</span>
    <svg viewBox="0 0 16 16" fill="currentColor" aria-hidden="true" class="w-3.5 h-3.5 text-gray-500 dark:text-gray-400 shrink-0">
      <path
        fill-rule="evenodd"
        d="M5.22 10.22a.75.75 0 0 1 1.06 0L8 11.94l1.72-1.72a.75.75 0 1 1 1.06 1.06l-2.25 2.25a.75.75 0 0 1-1.06 0l-2.25-2.25a.75.75 0 0 1 0-1.06ZM10.78 5.78a.75.75 0 0 1-1.06 0L8 4.06 6.28 5.78a.75.75 0 0 1-1.06-1.06l2.25-2.25a.75.75 0 0 1 1.06 0l2.25 2.25a.75.75 0 0 1 0 1.06Z"
        clip-rule="evenodd"
      />
    </svg>
  </button>

  {#if open}
    <div class="absolute left-0 top-full mt-2 w-80 max-h-[360px] overflow-y-auto bg-white dark:bg-gray-800 border border-gray-200 dark:border-gray-700 rounded-lg shadow-lg py-2 z-20">
      {#if status === 'loading'}
        <div class="py-2.5 px-4 text-sm text-gray-500 dark:text-gray-400">Loading…</div>
      {:else if status === 'error'}
        <div class="py-2.5 px-4 text-sm text-gray-500 dark:text-gray-400">
          Couldn't load companies.
          <button type="button" class="ml-2 bg-transparent border-0 text-indigo-600 dark:text-indigo-400 underline cursor-pointer p-0" onclick={load}>Retry</button>
        </div>
      {:else}
        <ul class="list-none m-0 p-0">
          {#each businessUnits as bu (bu.code)}
            <li>
              <div class="flex items-center">
                <button
                  type="button"
                  class="bg-transparent border-0 cursor-pointer text-gray-500 dark:text-gray-400 text-[10px] w-6 shrink-0 text-center py-2 px-0"
                  onclick={() => toggleBu(bu.code)}
                  aria-label={expandedBu === bu.code ? `Collapse ${bu.label}` : `Expand ${bu.label}`}
                >
                  {expandedBu === bu.code ? '▾' : '▸'}
                </button>
                <button
                  type="button"
                  class="group flex-1 flex items-center justify-between gap-2.5 text-left bg-transparent border-0 cursor-pointer py-2 px-2.5 text-sm text-gray-700 dark:text-gray-300 font-semibold hover:bg-indigo-600 hover:text-white"
                  onclick={() => selectBu(bu)}
                >
                  <span>{bu.label} <span class="font-normal text-gray-500 dark:text-gray-400 group-hover:text-indigo-100">({bu.companies.length})</span></span>
                  {#if selectedBuCode === bu.code && !selectedCompanyCode}
                    <svg
                      viewBox="0 0 20 20"
                      fill="currentColor"
                      aria-hidden="true"
                      class="w-4 h-4 shrink-0 text-indigo-600 dark:text-indigo-500 group-hover:text-white"
                    >
                      <path
                        fill-rule="evenodd"
                        d="M16.704 4.153a.75.75 0 0 1 .143 1.052l-8 10.5a.75.75 0 0 1-1.127.075l-4.5-4.5a.75.75 0 0 1 1.06-1.06l3.894 3.893 7.48-9.817a.75.75 0 0 1 1.05-.143Z"
                        clip-rule="evenodd"
                      />
                    </svg>
                  {/if}
                </button>
              </div>
              {#if expandedBu === bu.code}
                <ul class="list-none m-0 p-0 pl-6">
                  {#each bu.companies as company (company.code)}
                    <li>
                      <button
                        type="button"
                        class="group flex-1 flex items-center justify-between gap-2.5 text-left bg-transparent border-0 cursor-pointer py-2 px-2.5 text-sm text-gray-500 dark:text-gray-400 hover:bg-indigo-600 hover:text-white"
                        onclick={() => selectCompany(bu, company.code, company.name)}
                      >
                        <span>{company.name}</span>
                        {#if selectedCompanyCode === company.code}
                          <svg
                            viewBox="0 0 20 20"
                            fill="currentColor"
                            aria-hidden="true"
                            class="w-4 h-4 shrink-0 text-indigo-600 dark:text-indigo-500 group-hover:text-white"
                          >
                            <path
                              fill-rule="evenodd"
                              d="M16.704 4.153a.75.75 0 0 1 .143 1.052l-8 10.5a.75.75 0 0 1-1.127.075l-4.5-4.5a.75.75 0 0 1 1.06-1.06l3.894 3.893 7.48-9.817a.75.75 0 0 1 1.05-.143Z"
                              clip-rule="evenodd"
                            />
                          </svg>
                        {/if}
                      </button>
                    </li>
                  {/each}
                </ul>
              {/if}
            </li>
          {/each}
        </ul>
      {/if}
    </div>
  {/if}
</div>
