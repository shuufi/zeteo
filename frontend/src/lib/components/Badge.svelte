<script lang="ts">
  let {
    variant = 'neutral',
    text,
  }: { variant?: 'fact' | 'ai' | 'neutral'; text: string } = $props();
</script>

<span
  class="inline-flex items-center whitespace-nowrap rounded-full px-2 py-0.5 text-xs font-semibold {variant ===
  'neutral'
    ? 'bg-indigo-100 text-indigo-600 dark:bg-indigo-900 dark:text-indigo-500'
    : variant === 'fact'
      ? 'border-[1.5px] border-gray-900 bg-white text-gray-900 dark:border-gray-50 dark:bg-gray-800 dark:text-gray-50'
      : 'border-[1.5px] border-dashed border-blue-600 bg-blue-50 text-blue-600 dark:border-blue-400 dark:bg-blue-950 dark:text-blue-400'}"
>{text}</span>
