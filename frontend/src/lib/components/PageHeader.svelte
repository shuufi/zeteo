<script lang="ts">
  let { title = '' }: { title?: string } = $props();
</script>

<header class="border-b border-gray-200 bg-white dark:border-gray-700 dark:bg-gray-800">
  <div class="shell py-5">
    <h1 class="text-2xl font-bold text-gray-900 dark:text-gray-50">{title}</h1>
  </div>
</header>
