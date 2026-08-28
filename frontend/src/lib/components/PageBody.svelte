<script lang="ts">
  import type { Snippet } from 'svelte';

  let { children }: { children?: Snippet } = $props();
</script>

<main class="-mt-32">
  <div class="shell pb-12">
    <div
      class="rounded-lg bg-white px-5 py-6 shadow-sm sm:px-6 dark:bg-gray-800 dark:shadow-none dark:outline-1 dark:-outline-offset-1 dark:outline-white/10"
    >
      {@render children?.()}
    </div>
  </div>
</main>
