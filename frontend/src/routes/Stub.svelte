<script lang="ts">
  import PageHeader from '../lib/components/PageHeader.svelte';

  let { title = '' }: { title?: string } = $props();
</script>

<PageHeader {title} />

<div class="shell pt-12 pb-12">
  <p class="text-gray-500 dark:text-gray-400">Not built in this round of the wireframe. See docs/adr for scope.</p>
</div>
