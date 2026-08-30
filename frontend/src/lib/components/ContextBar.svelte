<script lang="ts">
  import { link } from "svelte-spa-router";
  import { context } from "../data/zeteo-data";
  import BusinessPicker from "./BusinessPicker.svelte";
  import PeriodPicker from "./PeriodPicker.svelte";
  import ChipSelect from "./ChipSelect.svelte";
  import { scopeState } from "../state/scope.svelte";
  import { scopeDraft } from "../state/scope-draft.svelte";
  import { periodState } from "../state/period.svelte";
  import { periodDraft } from "../state/period-draft.svelte";
  import { loadScope } from "../data/gl-store.svelte";

  const comparisonOptions = ["vs Budget", "vs Prior Year", "vs Forecast"];

  // Business/Period only stage a draft when picked (see docs/adr/0027) —
  // this is what actually commits scopeState/periodState and refetches.
  function applyPending(): void {
    scopeState.set(scopeDraft.code, scopeDraft.label);
    periodState.set(periodDraft.code);
    loadScope(scopeDraft.code, periodDraft.code);
    scopeDraft.reset();
    periodDraft.reset();
  }

  interface Crumb {
    id: string;
    name: string;
    href: string;
  }

  let {
    ancestors = [],
    currentLabel = "",
    refreshedAt = "",
    showYtd = false,
    ytd = $bindable(false),
  }: {
    ancestors?: Crumb[];
    currentLabel?: string;
    refreshedAt?: string;
    showYtd?: boolean;
    ytd?: boolean;
  } = $props();
</script>

<div
  class="flex items-center gap-2.5 pb-4 text-xs flex-wrap border-b border-gray-200 dark:border-gray-700"
>
  <BusinessPicker />
  <PeriodPicker />
  {#if showYtd}
    <label
      class="flex items-center gap-1.5 text-xs text-gray-600 dark:text-gray-300 cursor-pointer select-none"
    >
      <input
        type="checkbox"
        bind:checked={ytd}
        class="accent-indigo-600 dark:accent-indigo-400"
      />
      YTD
    </label>
  {/if}
  <ChipSelect
    id="comparison-select"
    options={comparisonOptions}
    selected={context.comparison}
  />
  <button
    type="button"
    onclick={applyPending}
    disabled={!scopeDraft.dirty && !periodDraft.dirty}
    class="rounded-md bg-indigo-600 px-3 py-1.5 text-xs font-semibold text-white shadow-xs hover:bg-indigo-500 disabled:cursor-not-allowed disabled:bg-gray-300 disabled:text-gray-500 dark:disabled:bg-gray-700 dark:disabled:text-gray-400"
  >
    Apply
  </button>

  {#if ancestors.length || currentLabel}
    <span class="ml-2 text-gray-700 dark:text-gray-300 text-sm">
      {#each ancestors as crumb, i (crumb.id)}
        <a
          href={crumb.href}
          use:link
          class="text-gray-500 dark:text-gray-400 no-underline hover:text-indigo-600 dark:hover:text-indigo-400 hover:underline"
          >{crumb.name}</a
        >
        {#if i < ancestors.length - 1 || currentLabel}<span
            class="text-gray-500 dark:text-gray-400 mx-1">›</span
          >{/if}
      {/each}
      {#if currentLabel}<strong>{currentLabel}</strong>{/if}
    </span>
  {/if}

  {#if refreshedAt}
    <span class="ml-auto text-gray-500 dark:text-gray-400 whitespace-nowrap"
      >{refreshedAt}</span
    >
  {/if}
</div>
