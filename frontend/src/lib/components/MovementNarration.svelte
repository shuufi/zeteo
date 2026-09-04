<script lang="ts">
  type Status = 'idle' | 'loading' | 'ready' | 'error';

  let {
    status,
    text = '',
    error = '',
    onGenerate,
  }: {
    status: Status;
    text?: string;
    error?: string;
    onGenerate: () => void;
  } = $props();

  // Backend returns a headline sentence then "- " bullet lines (see
  // docs/adr/0034) — split for display rather than dumping raw text.
  const headline = $derived(text.split('\n').find((line) => line.trim().length > 0) ?? '');
  const bullets = $derived(
    text
      .split('\n')
      .slice(1)
      .map((line) => line.trim())
      .filter((line) => line.length > 0)
      .map((line) => line.replace(/^[-•]\s*/, '')),
  );
</script>

<div class="flex flex-col gap-2 text-sm">
  <div class="flex items-center justify-between">
    <div class="font-bold text-sm text-gray-900 dark:text-gray-50">Movement narration</div>
    <button
      type="button"
      onclick={onGenerate}
      disabled={status === 'loading'}
      class="rounded-md bg-indigo-600 px-2.5 py-1 text-xs font-semibold text-white shadow-xs hover:bg-indigo-500 disabled:cursor-not-allowed disabled:bg-gray-300 disabled:text-gray-500 dark:disabled:bg-gray-700 dark:disabled:text-gray-400"
    >
      {status === 'loading' ? 'Explaining…' : status === 'ready' ? 'Regenerate' : 'Explain movement'}
    </button>
  </div>

  {#if status === 'idle'}
    <div class="text-xs text-gray-500 dark:text-gray-400">
      Ask the analyst to explain what drove this movement.
    </div>
  {:else if status === 'loading'}
    <div class="text-xs text-gray-500 dark:text-gray-400">Generating narration…</div>
  {:else if status === 'error'}
    <div class="text-xs text-red-600 dark:text-red-400">Unable to generate narration right now ({error}).</div>
  {:else if status === 'ready'}
    <p class="text-gray-900 dark:text-gray-50">{headline}</p>
    {#if bullets.length}
      <ul class="list-disc pl-4 flex flex-col gap-1 text-gray-700 dark:text-gray-300">
        {#each bullets as bullet, i (i)}
          <li>{bullet}</li>
        {/each}
      </ul>
    {/if}
  {/if}
</div>
