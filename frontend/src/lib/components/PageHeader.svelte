<script lang="ts">
  let { title = '' }: { title?: string } = $props();
</script>

<header class="bg-indigo-600 pb-32 dark:bg-indigo-800">
  <div class="shell py-10">
    <h1 class="text-3xl font-bold text-white">{title}</h1>
  </div>
</header>
