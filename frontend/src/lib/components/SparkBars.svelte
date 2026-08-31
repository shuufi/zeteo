<script lang="ts">
  let {
    values = [],
    width = 100,
    height = 30,
    fillClass = 'fill-gray-900 dark:fill-gray-50',
    class: className = '',
    splitAt,
    tooltips = [],
  }: {
    values?: number[];
    width?: number;
    height?: number;
    fillClass?: string;
    class?: string;
    /** Bars before this index render at reduced opacity (e.g. the prior-year half of a trailing-24-month series). */
    splitAt?: number;
    /** Per-bar hover text, e.g. "Jan (Prior Year): RM188.9m". */
    tooltips?: string[];
  } = $props();

  let hoveredIndex = $state<number | null>(null);

  const bars = $derived.by(() => {
    if (!values.length) return [];
    const max = Math.max(...values, 0);
    const min = Math.min(...values, 0);
    const range = max - min || 1;
    const step = width / values.length;
    const barWidth = Math.max(step - 1, 0.5);
    const zeroY = height - ((0 - min) / range) * height;
    return values.map((v, i) => {
      const barHeight = (Math.abs(v) / range) * height;
      const top = v >= 0 ? zeroY - barHeight : zeroY;
      return {
        x: i * step,
        y: top,
        width: barWidth,
        height: barHeight,
        opacity: splitAt !== undefined && i < splitAt ? 0.4 : 1,
        tooltip: tooltips[i],
        leftPct: ((i * step + barWidth / 2) / width) * 100,
      };
    });
  });

  const hovered = $derived(hoveredIndex !== null ? bars[hoveredIndex] : undefined);
</script>

<div class="relative">
  <svg viewBox="0 0 {width} {height}" preserveAspectRatio="none" class={className}>
    {#each bars as bar, i (i)}
      <rect
        x={bar.x}
        y={bar.y}
        width={bar.width}
        height={bar.height}
        opacity={bar.opacity}
        class={fillClass}
        role="presentation"
        onmouseenter={() => (hoveredIndex = i)}
        onmouseleave={() => (hoveredIndex = null)}
      />
    {/each}
  </svg>
  {#if hovered?.tooltip}
    <div
      class="pointer-events-none absolute bottom-full z-30 mb-1 -translate-x-1/2 whitespace-nowrap rounded bg-gray-900 dark:bg-gray-700 px-2 py-1 text-xs font-normal text-white shadow-lg"
      style="left: {hovered.leftPct}%"
    >
      {hovered.tooltip}
    </div>
  {/if}
</div>
