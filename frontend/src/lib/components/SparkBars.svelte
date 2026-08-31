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
    /** Per-bar hover text (native SVG `<title>`), e.g. "Jan (Prior Year): RM188.9m". */
    tooltips?: string[];
  } = $props();

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
      };
    });
  });
</script>

<svg viewBox="0 0 {width} {height}" preserveAspectRatio="none" class={className}>
  {#each bars as bar, i (i)}
    <rect x={bar.x} y={bar.y} width={bar.width} height={bar.height} opacity={bar.opacity} class={fillClass}>
      {#if bar.tooltip}<title>{bar.tooltip}</title>{/if}
    </rect>
  {/each}
</svg>
