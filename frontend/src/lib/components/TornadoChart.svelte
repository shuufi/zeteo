<script lang="ts">
  import { formatMoney, type MoneyScale } from '../data/format';
  import type { SensitivityCandidate } from '../data/types';

  // Horizontal diverging bar chart — no existing chart shape fits (GroupedBarChart
  // is same-direction rows, ProfitBridge is a vertical waterfall) — hand-rolled
  // SVG, same approach GroupedBarChart already uses for a simple chart like this.
  let {
    candidates = [],
    currency = '',
    moneyScale = 'units',
  }: { candidates?: SensitivityCandidate[]; currency?: string; moneyScale?: MoneyScale } = $props();

  const rowHeight = 40;
  const labelWidth = 160;
  const chartWidth = 520;
  const axisWidth = $derived(chartWidth - labelWidth);
  const centerX = $derived(labelWidth + axisWidth / 2);

  // Largest at top = classic tornado — sort defensively even though the
  // backend already ranks `ranked` descending by rankMagnitude.
  const sorted = $derived(
    [...candidates].sort((a, b) => (b.rankMagnitude ?? -1) - (a.rankMagnitude ?? -1)),
  );

  const height = $derived(sorted.length * rowHeight + 8);

  // Symmetric domain from the max |elasticity| across the shown candidates.
  const maxAbsElasticity = $derived(
    Math.max(
      1,
      ...sorted.flatMap((c) => [c.up.elasticityPct, c.down.elasticityPct].filter((v): v is number => v !== null).map(Math.abs)),
    ),
  );

  // Position is driven by polarity (the bump's actual NPAT outcome), not by
  // elasticityPct's own sign — those two disagree for a down-bump (e.g.
  // decreasing a cost driver is favourable, but %ΔNPAT / %Δdriver is negative
  // since %Δdriver itself is negative), which previously put favourable bars
  // on the left. Favourable always renders right, adverse always left.
  function barX(elasticityPct: number, polarity: SensitivityCandidate['up']['polarity']): { x: number; width: number } {
    const half = axisWidth / 2;
    const width = (Math.abs(elasticityPct) / maxAbsElasticity) * half;
    return polarity === 'adverse' ? { x: centerX - width, width } : { x: centerX, width };
  }

  function colorVar(polarity: SensitivityCandidate['up']['polarity']): string {
    return polarity === 'favourable' ? 'var(--increase)' : polarity === 'adverse' ? 'var(--decrease)' : 'var(--neutral)';
  }

  // Driver descriptions can run long (e.g. "Senior officer nationality mix
  // adjustment factor") — wrap into at most 2 lines within labelWidth rather
  // than letting SVG text overflow uncontained; ellipsis if still too long.
  const MAX_LABEL_CHARS_PER_LINE = 20;
  const MAX_LABEL_LINES = 2;

  function wrapLabel(text: string): string[] {
    const words = text.split(' ');
    const lines: string[] = [];
    let current = '';
    for (const word of words) {
      const candidate = current ? `${current} ${word}` : word;
      if (candidate.length > MAX_LABEL_CHARS_PER_LINE && current) {
        lines.push(current);
        current = word;
        if (lines.length >= MAX_LABEL_LINES) break;
      } else {
        current = candidate;
      }
    }
    if (lines.length < MAX_LABEL_LINES) {
      if (current) lines.push(current);
    } else if (current) {
      const maxLen = MAX_LABEL_CHARS_PER_LINE - 1;
      const last = (lines[MAX_LABEL_LINES - 1] ?? '').slice(0, maxLen).trimEnd();
      lines[MAX_LABEL_LINES - 1] = `${last}…`;
    }
    return lines;
  }
</script>

{#if sorted.length}
  <div class="chart-colors w-full overflow-x-auto">
    <svg width={chartWidth} {height} viewBox="0 0 {chartWidth} {height}" role="img" aria-label="Tornado chart of Driver elasticity to NPAT">
      <line x1={centerX} y1="0" x2={centerX} y2={height} class="stroke-gray-300 dark:stroke-gray-600" stroke-width="1" />
      {#each sorted as candidate, i (candidate.driverCode)}
        {@const labelLines = wrapLabel(candidate.description)}
        <g transform="translate(0,{i * rowHeight})">
          <text
            x={labelWidth - 8}
            y={rowHeight / 2 + 4 - (labelLines.length - 1) * 6}
            font-size="11"
            text-anchor="end"
            class="fill-gray-700 dark:fill-gray-300"
          >
            <title>{candidate.description}</title>
            {#each labelLines as line, li}
              <tspan x={labelWidth - 8} dy={li === 0 ? 0 : 12}>{line}</tspan>
            {/each}
          </text>
          {#if candidate.na || candidate.rankMagnitude === null}
            <text x={centerX} y={rowHeight / 2 + 4} font-size="11" text-anchor="middle" class="fill-gray-400 dark:fill-gray-500">N/A</text>
          {:else}
            {#if candidate.up.elasticityPct !== null}
              {@const bar = barX(candidate.up.elasticityPct, candidate.up.polarity)}
              <rect x={bar.x} y={8} width={bar.width} height={rowHeight - 16} fill={colorVar(candidate.up.polarity)} rx="2" />
              <title>+bump: {candidate.up.elasticityPct.toFixed(1)}% elasticity, {formatMoney(candidate.up.npatImpact, currency, moneyScale)}</title>
            {/if}
            {#if candidate.down.elasticityPct !== null}
              {@const bar = barX(candidate.down.elasticityPct, candidate.down.polarity)}
              <rect x={bar.x} y={8} width={bar.width} height={rowHeight - 16} fill={colorVar(candidate.down.polarity)} rx="2" opacity="0.7" />
              <title>-bump: {candidate.down.elasticityPct.toFixed(1)}% elasticity, {formatMoney(candidate.down.npatImpact, currency, moneyScale)}</title>
            {/if}
          {/if}
        </g>
      {/each}
    </svg>
  </div>
{/if}

<style>
  .chart-colors {
    --increase: var(--color-green-600);
    --decrease: var(--color-red-600);
    --neutral: var(--color-gray-400);
  }
  :global(.dark) .chart-colors {
    --increase: var(--color-green-400);
    --decrease: var(--color-red-400);
    --neutral: var(--color-gray-500);
  }
</style>
