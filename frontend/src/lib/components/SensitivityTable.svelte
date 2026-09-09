<script lang="ts">
  import { formatMoney } from '../data/format';
  import type { MoneyScale } from '../data/format';
  import type { SensitivityCandidate, SensitivityNaReason } from '../data/types';

  // Coordinator always passes result.ranked (top-10) — the same list backing
  // the tornado chart, never the full result.candidates set (see
  // docs/adr/0043 RESOLVED DECISIONS #3).
  let {
    candidates = [],
    currency = '',
    moneyScale = 'units' as MoneyScale,
    bumpPct = 0,
  }: { candidates?: SensitivityCandidate[]; currency?: string; moneyScale?: MoneyScale; bumpPct?: number } = $props();

  const sorted = $derived(
    [...candidates].sort((a, b) => (b.rankMagnitude ?? -1) - (a.rankMagnitude ?? -1)),
  );

  const naReasonLabel: Record<SensitivityNaReason, string> = {
    'baseline-driver-zero': 'baseline driver value zero',
    'divide-by-zero': 'divide-by-zero at baseline',
    'baseline-npat-zero': 'NPAT near zero for window',
  };

  function polarityClass(polarity: SensitivityCandidate['up']['polarity']): string {
    return polarity === 'favourable'
      ? 'text-green-600 dark:text-green-400'
      : polarity === 'adverse'
        ? 'text-red-600 dark:text-red-400'
        : 'text-gray-500 dark:text-gray-400';
  }
</script>

<div class="overflow-x-auto">
  <table class="w-full text-xs">
    <thead>
      <tr class="border-b border-gray-200 text-left text-gray-500 dark:border-gray-700 dark:text-gray-400">
        <th class="py-1.5 pr-3 font-medium">Driver</th>
        <th class="py-1.5 pr-3 font-medium">Unit</th>
        <th class="py-1.5 pr-3 text-right font-medium">Elasticity +{bumpPct}%</th>
        <th class="py-1.5 pr-3 text-right font-medium">Elasticity -{bumpPct}%</th>
        <th class="py-1.5 pr-3 text-right font-medium">$ Impact +{bumpPct}%</th>
        <th class="py-1.5 text-right font-medium">$ Impact -{bumpPct}%</th>
      </tr>
    </thead>
    <tbody>
      {#each sorted as candidate (candidate.driverCode)}
        <tr class="border-b border-gray-100 last:border-0 dark:border-gray-800">
          <td class="py-1.5 pr-3 text-gray-900 dark:text-gray-100">{candidate.description}</td>
          <td class="py-1.5 pr-3 text-gray-500 dark:text-gray-400">{candidate.unit}</td>
          {#if candidate.na}
            <td class="py-1.5 pr-3 text-right text-gray-400 dark:text-gray-500" colspan="4">
              <span title={candidate.naReason ? naReasonLabel[candidate.naReason] : undefined}>N/A</span>
            </td>
          {:else}
            <td class="py-1.5 pr-3 text-right tabular-nums {polarityClass(candidate.up.polarity)}">
              {candidate.up.elasticityPct?.toFixed(1)}%
            </td>
            <td class="py-1.5 pr-3 text-right tabular-nums {polarityClass(candidate.down.polarity)}">
              {candidate.down.elasticityPct?.toFixed(1)}%
            </td>
            <td class="py-1.5 pr-3 text-right tabular-nums text-gray-900 dark:text-gray-100">
              {formatMoney(candidate.up.npatImpact, currency, moneyScale)}
            </td>
            <td class="py-1.5 text-right tabular-nums text-gray-900 dark:text-gray-100">
              {formatMoney(candidate.down.npatImpact, currency, moneyScale)}
            </td>
          {/if}
        </tr>
      {/each}
    </tbody>
  </table>
</div>
