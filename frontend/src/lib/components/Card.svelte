<script lang="ts">
  import type { Snippet } from 'svelte';

  let {
    title = '',
    class: className = '',
    header,
    children,
  }: {
    title?: string;
    class?: string;
    header?: Snippet;
    children?: Snippet;
  } = $props();
</script>

<div class="border border-gray-200 dark:border-gray-700 rounded-lg px-4 py-2.5 bg-white dark:bg-gray-800 {className}">
  {#if header}
    {@render header()}
  {:else if title}
    <div class="font-bold text-sm mb-2 text-gray-900 dark:text-gray-50">{title}</div>
  {/if}
  {@render children?.()}
</div>
