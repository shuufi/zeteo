<script lang="ts">
  import { formatMoney, type MoneyScale } from '../data/format';
  import type { MovementNarrationData } from '../data/narration-store.svelte';

  type Status = 'idle' | 'loading' | 'ready' | 'error';

  let {
    status,
    narration = null,
    error = '',
    onGenerate,
    currency,
    moneyScale,
  }: {
    status: Status;
    narration?: MovementNarrationData | null;
    error?: string;
    onGenerate: () => void;
    currency: string;
    moneyScale: MoneyScale;
  } = $props();
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
  {:else if status === 'ready' && narration}
    <div class="flex items-start gap-2">
      <span class="shrink-0 rounded bg-gray-100 px-1.5 py-0.5 text-xs font-semibold tabular-nums text-gray-700 dark:bg-gray-700 dark:text-gray-200">
        {formatMoney(Math.abs(narration.netAmount), currency, moneyScale)}
      </span>
      <p class="text-gray-900 dark:text-gray-50">{narration.headline}</p>
    </div>
    {#if narration.bullets.length}
      <ul class="list-disc pl-4 flex flex-col gap-1 text-gray-700 dark:text-gray-300">
        {#each narration.bullets as bullet (bullet.nodeId)}
          <li>
            <span class="font-semibold tabular-nums text-gray-900 dark:text-gray-100">
              {formatMoney(Math.abs(bullet.amount), currency, moneyScale)} — {bullet.nodeName}:
            </span>
            {bullet.text}
          </li>
        {/each}
      </ul>
    {/if}
  {/if}
</div>
