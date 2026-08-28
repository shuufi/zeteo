<script lang="ts">
  import type { MonthlySeries } from '../data/types';

  let {
    series = [],
    months = [],
    width = 100,
    height = 170,
  }: { series?: MonthlySeries[]; months?: string[]; width?: number; height?: number } = $props();

  const padTop = 10;
  const padBottom = 32;
  const padLeft = 4;
  const padRight = 4;
  const chartWidth = $derived(width - padLeft - padRight);
  const chartHeight = $derived(height - padTop - padBottom);

  const maxValue = $derived(Math.max(...series.flatMap((s) => s.values), 1));

  function pointsFor(values: number[]): string {
    const stepX = chartWidth / Math.max(values.length - 1, 1);
    return values
      .map((v, i) => {
        const x = padLeft + i * stepX;
        const y = padTop + chartHeight - (v / maxValue) * chartHeight;
        return `${x.toFixed(1)},${y.toFixed(1)}`;
      })
      .join(' ');
  }

  function tickX(i: number): number {
    const stepX = chartWidth / Math.max(months.length - 1, 1);
    return padLeft + i * stepX;
  }

  function fillClass(strokeClass: string): string {
    return strokeClass.replace(/stroke-/g, 'fill-');
  }
</script>

<svg {width} {height} viewBox="0 0 {width} {height}" role="img" aria-label="Monthly performance trend, January to December">
  <line
    x1={padLeft}
    y1={padTop + chartHeight}
    x2={width - padRight}
    y2={padTop + chartHeight}
    class="stroke-gray-200 dark:stroke-gray-700"
  />
  {#each series as s (s.label)}
    <polyline points={pointsFor(s.values)} fill="none" class={s.colorClass} stroke-width="1.5" />
  {/each}
  {#each months as m, i (m)}
    <text x={tickX(i)} y={padTop + chartHeight + 11} font-size="7" text-anchor="middle" class="fill-gray-500 dark:fill-gray-400">
      {m}
    </text>
  {/each}
  {#each series as s, i (s.label)}
    <rect x={padLeft + i * 100} y={height - 10} width="6" height="6" class={fillClass(s.colorClass)} />
    <text x={padLeft + i * 100 + 9} y={height - 5} font-size="8" class="fill-gray-500 dark:fill-gray-400">{s.label}</text>
  {/each}
</svg>
