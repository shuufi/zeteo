<script lang="ts">
  import { link } from 'svelte-spa-router';

  let {
    label = 'Full diagnostic not yet modelled for this node.',
    linkHref = '',
    linkLabel = '',
  }: { label?: string; linkHref?: string; linkLabel?: string } = $props();
</script>

<div
  class="rounded-2xl border-[1.5px] border-dashed border-gray-100 bg-gray-100 p-6 text-center text-sm text-gray-500 dark:border-gray-800 dark:bg-gray-900 dark:text-gray-400"
>
  <p>{label}</p>
  {#if linkHref}
    <a
      href={linkHref}
      use:link
      class="mt-2 inline-block font-semibold text-indigo-600 no-underline hover:underline dark:text-indigo-400"
      >{linkLabel} →</a
    >
  {/if}
</div>
