<script lang="ts">
  let {
    label = '',
    chips = [],
    selected = '',
  }: { label?: string; chips?: string[]; selected?: string } = $props();
</script>

<div class="flex flex-wrap items-center gap-2 text-xs">
  {#if label}<span class="text-gray-500 dark:text-gray-400">{label}</span>{/if}
  {#each chips as chip (chip)}
    <span
      class="rounded-full border px-2.5 py-px {chip === selected
        ? 'border-gray-900 font-semibold text-gray-900 dark:border-gray-50 dark:text-gray-50'
        : 'border-gray-200 text-gray-500 dark:border-gray-700 dark:text-gray-400'}"
    >{chip}</span>
  {/each}
</div>
