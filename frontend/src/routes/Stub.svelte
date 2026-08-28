<script lang="ts">
  import PageHeader from '../lib/components/PageHeader.svelte';
  import PageBody from '../lib/components/PageBody.svelte';

  let { title = '' }: { title?: string } = $props();
</script>

<PageHeader {title} />
<PageBody>
  <p class="text-gray-500 dark:text-gray-400">Not built in this round of the wireframe. See docs/adr for scope.</p>
</PageBody>
