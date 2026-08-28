<script lang="ts">
  import type { BarChartCategory } from '../data/types';
  import { formatRmAuto } from '../data/zeteo-data';

  let {
    categories = [],
    width = 100,
  }: { categories?: BarChartCategory[]; width?: number } = $props();

  const rowHeight = 26;
  const labelWidth = 84;
  const barAreaWidth = $derived(width - labelWidth - 60);
  const height = $derived(categories.length * rowHeight * 2 + 8);

  const maxValue = $derived(
    Math.max(...categories.flatMap((c) => [c.actual, c.priorYear]), 1)
  );

  function barWidth(value: number): number {
    return (value / maxValue) * barAreaWidth;
  }
</script>

<svg {width} {height} viewBox="0 0 {width} {height}" role="img" aria-label="Revenue, Cost of Revenue and OPEX, actual vs prior year">
  {#each categories as cat, i (cat.label)}
    <g transform="translate(0,{i * rowHeight * 2})">
      <text x="0" y="10" font-size="9" class="fill-gray-500 dark:fill-gray-400">{cat.label}</text>
      <rect x={labelWidth} y="2" width={barWidth(cat.actual)} height="10" class="fill-gray-900 dark:fill-gray-50" />
      <text x={labelWidth + barWidth(cat.actual) + 4} y="10" font-size="9" class="fill-gray-900 dark:fill-gray-50">
        {formatRmAuto(cat.actual)}
      </text>
      <rect x={labelWidth} y="14" width={barWidth(cat.priorYear)} height="10" class="fill-gray-200 dark:fill-gray-700" />
      <text x={labelWidth + barWidth(cat.priorYear) + 4} y="22" font-size="9" class="fill-gray-500 dark:fill-gray-400">
        {formatRmAuto(cat.priorYear)}
      </text>
    </g>
  {/each}
  <text x={labelWidth} y={height - 4} font-size="8" class="fill-gray-500 dark:fill-gray-400">
    ■ Actual&#160;&#160;&#160;□ Prior Year
  </text>
</svg>
