<script lang="ts">
  import type { Snippet } from 'svelte';

  let { children }: { children?: Snippet } = $props();
</script>

<main class="-mt-32 flex flex-1 flex-col min-h-0 min-w-0">
  <div class="shell pb-12 w-full flex flex-1 flex-col min-h-0 min-w-0">
    <div
      class="rounded-lg bg-white px-5 py-6 shadow-sm sm:px-6 dark:bg-gray-800 dark:shadow-none dark:outline-1 dark:-outline-offset-1 dark:outline-white/10 flex flex-1 flex-col min-h-0 min-w-0"
    >
      {@render children?.()}
    </div>
  </div>
</main>
