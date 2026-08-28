<script lang="ts">
  let {
    points = [],
    width = 100,
    height = 30,
    strokeClass = 'stroke-gray-900 dark:stroke-gray-50',
  }: { points?: number[]; width?: number; height?: number; strokeClass?: string } = $props();

  const path = $derived.by(() => {
    if (!points.length) return '';
    const max = Math.max(...points);
    const min = Math.min(...points);
    const range = max - min || 1;
    const stepX = width / (points.length - 1 || 1);
    return points
      .map((p, i) => {
        const x = i * stepX;
        const y = height - ((p - min) / range) * height;
        return `${x.toFixed(1)},${y.toFixed(1)}`;
      })
      .join(' ');
  });
</script>

<svg {width} {height} viewBox="0 0 {width} {height}" preserveAspectRatio="none">
  <polyline points={path} fill="none" class={strokeClass} stroke-width="2" />
</svg>
