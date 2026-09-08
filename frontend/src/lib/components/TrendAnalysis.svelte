<script lang="ts">
  import { formatMoney, formatVar, type MoneyScale } from '../data/format';
  import type { TrendAnalysisData } from '../data/trend-analysis-store.svelte';
  import LottieLoader from './LottieLoader.svelte';
  import Sparkline from './Sparkline.svelte';
  import thinkingSrc from '../assets/thinking.lottie?url';

  type Status = 'idle' | 'loading' | 'ready' | 'error';

  let {
    status,
    analysis = null,
    error = '',
    onGenerate,
    currency,
    moneyScale,
    months,
  }: {
    status: Status;
    analysis?: TrendAnalysisData | null;
    error?: string;
    onGenerate: () => void;
    currency: string;
    moneyScale: MoneyScale;
    months: string[];
  } = $props();

  function directionAt(bullet: TrendAnalysisData['bullets'][number]): string {
    return bullet.flaggedMonths.find((m) => m.monthIndex === bullet.peakMonthIndex)?.direction ?? 'unchanged';
  }
</script>

<div class="flex flex-col gap-2 text-sm">
  <div class="flex items-center justify-between">
    <div class="font-bold text-sm text-gray-900 dark:text-gray-50">Trend Analysis</div>
    <button
      type="button"
      onclick={onGenerate}
      disabled={status === 'loading'}
      class="rounded-md bg-indigo-600 px-2.5 py-1 text-xs font-semibold text-white shadow-xs hover:bg-indigo-500 disabled:cursor-not-allowed disabled:bg-gray-300 disabled:text-gray-500 dark:disabled:bg-gray-700 dark:disabled:text-gray-400"
    >
      {status === 'loading' ? 'Analysing…' : status === 'ready' ? 'Regenerate' : 'Analyse trends'}
    </button>
  </div>

  {#if status === 'idle'}
    <div class="text-xs text-gray-500 dark:text-gray-400">
      Scan the full fiscal year for month-over-month movements worth flagging.
    </div>
  {:else if status === 'loading'}
    <div class="flex flex-col items-center justify-center gap-2 py-2">
      <div class="w-1/2">
        <LottieLoader src={thinkingSrc} size={400} aspectRatio={1} responsive />
      </div>
      <div class="text-xs text-gray-500 dark:text-gray-400">Thinking...</div>
    </div>
  {:else if status === 'error'}
    <div class="text-xs text-red-600 dark:text-red-400">Unable to generate trend analysis right now ({error}).</div>
  {:else if status === 'ready' && analysis}
    <p class="text-gray-900 dark:text-gray-50">{analysis.headline}</p>
    {#if analysis.bullets.length === 0}
      <div class="text-xs text-gray-500 dark:text-gray-400">Quiet year — nothing crossed the threshold.</div>
    {:else}
      <ul class="flex flex-col gap-3">
        {#each analysis.bullets as bullet (bullet.nodeId)}
          <li class="flex flex-col gap-1 border-t border-gray-100 pt-2 first:border-t-0 first:pt-0 dark:border-gray-800">
            <div class="flex items-start gap-2">
              <span class="shrink-0 rounded bg-gray-100 px-1.5 py-0.5 text-xs font-semibold tabular-nums text-gray-700 dark:bg-gray-700 dark:text-gray-200">
                {formatMoney(Math.abs(bullet.amount), currency, moneyScale)}
              </span>
              <span class="font-semibold text-gray-900 dark:text-gray-100">
                {bullet.nodeName}
                <span class="font-normal text-gray-500 dark:text-gray-400">{directionAt(bullet)}</span>
              </span>
            </div>
            <p class="text-gray-700 dark:text-gray-300">{bullet.text}</p>
            <div class="flex flex-wrap items-center gap-2 text-xs text-gray-500 dark:text-gray-400">
              {#each bullet.flaggedMonths as month (month.monthIndex)}
                <span class="rounded bg-gray-50 px-1.5 py-0.5 dark:bg-gray-800">
                  {months[month.monthIndex]}: {month.momPct !== null ? formatVar(month.momPct) : 'from ~0'}
                  ({month.sharePct}% of total)
                </span>
              {/each}
            </div>
            <div class="flex items-center gap-2">
              <Sparkline points={bullet.series} width={100} height={24} strokeClass="stroke-indigo-500 dark:stroke-indigo-400" />
            </div>
            {#if bullet.drivers.length}
              <div class="flex flex-col gap-0.5 text-xs text-gray-500 dark:text-gray-400">
                {#each bullet.drivers as driver (driver.name)}
                  <span>
                    {driver.name}: {driver.series[bullet.peakMonthIndex - 1] ?? '—'} → {driver.series[bullet.peakMonthIndex]} {driver.unit}
                  </span>
                {/each}
              </div>
            {/if}
          </li>
        {/each}
      </ul>
    {/if}
  {/if}
</div>
