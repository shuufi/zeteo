<script lang="ts">
  import { onMount } from 'svelte';
  import { replace } from 'svelte-spa-router';

  // Explorer's own landing page doesn't exist yet — VDT Comparison used to
  // live at bare /vdt, so redirect there until Explorer gets a real landing.
  onMount(() => {
    replace('/vdt/compare');
  });
</script>
