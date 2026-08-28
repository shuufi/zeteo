<script lang="ts">
  import type { BridgeStep } from '../data/types';
  import { formatRmAuto } from '../data/zeteo-data';

  let {
    steps = [],
    width = 100,
    height = 130,
  }: { steps?: BridgeStep[]; width?: number; height?: number } = $props();

  const chartHeight = $derived(height - 24);
  const maxValue = $derived(Math.max(...steps.filter((s) => s.kind === 'total').map((s) => s.value), 1));

  const axisLabel: Record<string, string> = {
    'Cost of Revenue': 'Cost of Rev.',
    'Operating Profit': 'Op. Profit',
    'Finance Costs': 'Fin. Costs',
    'Profit Before Tax': 'PBT',
  };

  const bars = $derived.by(() => {
    const barGap = 6;
    const barWidth = (width - barGap * (steps.length - 1)) / (steps.length || 1);
    let running = 0;
    return steps.map((step, i) => {
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
      const top = Math.max(from, to);
      const bottom = Math.min(from, to);
      const y = chartHeight - (top / maxValue) * chartHeight;
      const barHeight = Math.max(((top - bottom) / maxValue) * chartHeight, 1);
      const colorClass =
        step.kind === 'total'
          ? 'fill-gray-900 dark:fill-gray-50'
          : step.kind === 'decrease'
            ? 'fill-red-600 dark:fill-red-400'
            : 'fill-green-600 dark:fill-green-400';
      return {
        x: i * (barWidth + barGap),
        y,
        barWidth,
        barHeight,
        colorClass,
        label: axisLabel[step.label] ?? step.label,
        valueLabel: formatRmAuto(Math.abs(step.value)),
      };
    });
  });
</script>

<svg {width} {height} viewBox="0 0 {width} {height}" role="img" aria-label="Profit bridge, Revenue to NPAT">
  <line x1="0" y1={chartHeight} x2={width} y2={chartHeight} class="stroke-gray-200 dark:stroke-gray-700" />
  {#each bars as bar (bar.label)}
    <rect x={bar.x} y={bar.y} width={bar.barWidth} height={bar.barHeight} class={bar.colorClass} />
    <text x={bar.x + bar.barWidth / 2} y={bar.y - 3} font-size="7" text-anchor="middle" class="fill-gray-700 dark:fill-gray-300">
      {bar.valueLabel}
    </text>
    <text
      x={bar.x + bar.barWidth / 2}
      y={chartHeight + 11}
      font-size="7"
      text-anchor="middle"
      class="fill-gray-500 dark:fill-gray-400"
    >
      {bar.label}
    </text>
  {/each}
</svg>
