<script lang="ts">
  import type { PeriodNode } from '../data/types';

  let {
    label,
    periods,
    value = $bindable<string | undefined>(undefined),
  }: { label: string; periods: PeriodNode[]; value?: string } = $props();

  let open = $state(false);
  let rootEl = $state<HTMLDivElement | null>(null);

  const selectedLabel = $derived(periods.find((p) => p.id === value)?.label ?? 'Select…');

  function select(period: PeriodNode): void {
    value = period.id;
    open = false;
  }

  $effect(() => {
    if (!open) return;
    function handlePointerDown(e: PointerEvent): void {
      if (rootEl && !rootEl.contains(e.target as Node)) open = false;
    }
    function handleKeydown(e: KeyboardEvent): void {
      if (e.key === 'Escape') open = false;
    }
    document.addEventListener('pointerdown', handlePointerDown);
    document.addEventListener('keydown', handleKeydown);
    return () => {
      document.removeEventListener('pointerdown', handlePointerDown);
      document.removeEventListener('keydown', handleKeydown);
    };
  });
</script>

<div class="flex items-center gap-1.5" bind:this={rootEl}>
  <span class="text-xs whitespace-nowrap text-gray-500 dark:text-gray-400">{label}:</span>

  <div class="relative">
    <button
      type="button"
      onclick={() => (open = !open)}
      disabled={periods.length === 0}
      class="grid min-w-28 cursor-default grid-cols-1 rounded-md bg-white py-1.5 pr-2 pl-3 text-left text-gray-900 outline-1 -outline-offset-1 outline-gray-300 focus-visible:outline-2 focus-visible:-outline-offset-2 focus-visible:outline-indigo-600 disabled:cursor-not-allowed disabled:opacity-50 sm:text-sm/6 dark:bg-white/5 dark:text-white dark:outline-white/10 dark:focus-visible:outline-indigo-500"
    >
      <span class="col-start-1 row-start-1 truncate pr-6">{selectedLabel}</span>
      <svg
        viewBox="0 0 16 16"
        fill="currentColor"
        aria-hidden="true"
        class="col-start-1 row-start-1 size-5 self-center justify-self-end text-gray-500 sm:size-4 dark:text-gray-400"
      >
        <path
          fill-rule="evenodd"
          d="M5.22 10.22a.75.75 0 0 1 1.06 0L8 11.94l1.72-1.72a.75.75 0 1 1 1.06 1.06l-2.25 2.25a.75.75 0 0 1-1.06 0l-2.25-2.25a.75.75 0 0 1 0-1.06ZM10.78 5.78a.75.75 0 0 1-1.06 0L8 4.06 6.28 5.78a.75.75 0 0 1-1.06-1.06l2.25-2.25a.75.75 0 0 1 1.06 0l2.25 2.25a.75.75 0 0 1 0 1.06Z"
          clip-rule="evenodd"
        />
      </svg>
    </button>

    {#if open}
      <div
        class="absolute z-10 mt-1 max-h-72 w-40 overflow-auto rounded-md bg-white py-1 shadow-lg outline-1 outline-black/5 dark:bg-gray-800 dark:shadow-none dark:-outline-offset-1 dark:outline-white/10"
      >
        {#each periods as period (period.id)}
          <button
            type="button"
            onclick={() => select(period)}
            class="block w-full px-3 py-1.5 text-left text-sm {period.id === value
              ? 'bg-indigo-600 text-white'
              : 'text-gray-900 hover:bg-gray-100 dark:text-gray-300 dark:hover:bg-gray-700'}"
          >
            {period.label}
          </button>
        {/each}
      </div>
    {/if}
  </div>
</div>
