<script lang="ts">
  import { onMount } from 'svelte';
  import { Tween } from 'svelte/motion';
  import { cubicOut } from 'svelte/easing';
  import { Plot, BarX, Text } from 'svelteplot';
  import type { BridgeStep } from '../data/types';
  import { formatRmAuto } from '../data/format';

  let { steps = [], height = 220 }: { steps?: BridgeStep[]; height?: number } = $props();

  const axisLabel: Record<string, string> = {
    'Cost of Revenue': 'Cost of Rev.',
    'Operating Profit': 'Op. Profit',
    'Finance Costs': 'Fin. Costs',
    'Profit Before Tax': 'PBT',
    'Other Income & Expenses': 'Other Inc./Exp.',
    'Secondary Cost Elements': 'Secondary Cost',
  };

  // Waterfall shape: each bar spans [from, to] rather than [0, value] — a running
  // total carries forward from bar to bar, and resets at each "total" step.
  const bars = $derived.by(() => {
    let running = 0;
    return steps.map((step) => {
      let from: number;
      let to: number;
      if (step.kind === 'total') {
        from = 0;
        to = step.value;
        running = step.value;
      } else {
        from = running;
        to = running + step.value;
        running = to;
      }
      return {
        label: axisLabel[step.label] ?? step.label,
        x1: from,
        x2: to,
        end: Math.max(from, to),
        kind: step.kind,
        valueLabel: formatRmAuto(Math.abs(step.value)),
      };
    });
  });

  // Headroom on the right so value labels past the longest bar aren't clipped.
  const xMax = $derived(Math.max(...bars.map((b) => b.end), 1) * 1.12);

  // Reveals the plot left-to-right on mount via a shrinking clip-path.
  const reveal = new Tween(0, { duration: 900, easing: cubicOut });
  onMount(() => {
    reveal.set(1);
  });
</script>

<div class="chart-colors w-full" style="clip-path: inset(0 {(1 - reveal.current) * 100}% 0 0);">
  <Plot
    {height}
    x={{ label: false, grid: true, domain: [0, xMax] }}
    y={{ label: false, domain: bars.map((b) => b.label), reverse: true }}
    color={{ scheme: { total: 'var(--total)', increase: 'var(--increase)', decrease: 'var(--decrease)' } }}
  >
    <BarX data={bars} sort={false} y="label" x1="x1" x2="x2" fill="kind" />
    <Text data={bars} y="label" x="end" text="valueLabel" dx={6} textAnchor="start" fontSize={9} />
  </Plot>
</div>

<style>
  .chart-colors {
    --total: var(--color-green-700);
    --increase: var(--color-green-600);
    --decrease: var(--color-red-600);
  }
  :global(.dark) .chart-colors {
    --total: var(--color-green-500);
    --increase: var(--color-green-400);
    --decrease: var(--color-red-400);
  }
</style>
