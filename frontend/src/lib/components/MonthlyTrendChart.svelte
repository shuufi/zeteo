<script lang="ts">
  import { onMount } from 'svelte';
  import { Tween } from 'svelte/motion';
  import { cubicOut } from 'svelte/easing';
  import { Plot, Line, Text } from 'svelteplot';
  import type { MonthlySeries } from '../data/types';

  let {
    series = [],
    months = [],
    height = 300,
  }: { series?: MonthlySeries[]; months?: string[]; height?: number } = $props();

  const data = $derived(
    series.flatMap((s) =>
      s.values.map((value, i) => ({ month: months[i], label: s.label, value, valueLabel: value.toFixed(0) }))
    )
  );

  // Headroom above the highest point so its data label isn't clipped by the plot edge.
  const yMax = $derived(Math.max(...series.flatMap((s) => s.values), 1) * 1.15);

  // No legend — instead, name each line right at its last point, where a
  // reader's eye naturally lands after following the line across the months.
  // When two series end close together, nudge the lower name's label down
  // so the two don't print on top of each other.
  const seriesNameLabels = $derived.by(() => {
    const items = series
      .filter((s) => s.values.length > 0)
      .map((s) => ({
        month: months[s.values.length - 1],
        label: s.label,
        value: s.values[s.values.length - 1],
        labelY: s.values[s.values.length - 1],
      }))
      .sort((a, b) => a.value - b.value);

    const pxPerUnit = yMax > 0 ? height / yMax : 1;
    const minGapPx = 14;
    for (let i = 1; i < items.length; i++) {
      const gapPx = (items[i].labelY - items[i - 1].labelY) * pxPerUnit;
      if (gapPx < minGapPx) {
        items[i].labelY = items[i - 1].labelY + minGapPx / pxPerUnit;
      }
    }
    return items;
  });

  // Reveals the plot left-to-right on mount via a shrinking clip-path — works
  // uniformly across all series regardless of each line's individual path length.
  const reveal = new Tween(0, { duration: 900, easing: cubicOut });
  onMount(() => {
    reveal.set(1);
  });
</script>

<div class="chart-colors w-full" style="clip-path: inset(0 {(1 - reveal.current) * 100}% 0 0);">
  <Plot
    {height}
    marginRight={54}
    x={{ label: false, domain: months }}
    y={{ label: false, grid: false, axis: false, domain: [0, yMax] }}
    color={{
      legend: false,
      domain: ['Revenue', 'COR', 'GP', 'NPAT'],
      scheme: {
        Revenue: 'var(--revenue)',
        COR: 'var(--cor)',
        GP: 'var(--gp)',
        NPAT: 'var(--npat)',
      },
    }}
  >
    <Line {data} x="month" y="value" stroke="label" strokeWidth={2} curve="linear" />
    <Text {data} x="month" y="value" text="valueLabel" fill="label" dy={-9} textAnchor="middle" fontSize={11} fontWeight="bold" />
    <Text
      data={seriesNameLabels}
      x="month"
      y="labelY"
      text="label"
      fill="label"
      dx={8}
      textAnchor="start"
      fontSize={11}
      fontWeight="bold"
    />
  </Plot>
</div>

<style>
  .chart-colors {
    --revenue: var(--color-gray-900);
    --cor: var(--color-red-600);
    --gp: var(--color-emerald-600);
    --npat: var(--color-blue-600);
  }
  :global(.dark) .chart-colors {
    --revenue: var(--color-gray-50);
    --cor: var(--color-red-400);
    --gp: var(--color-emerald-400);
    --npat: var(--color-blue-400);
  }
</style>
