<script lang="ts">
  import { onMount } from 'svelte';
  import { Tween } from 'svelte/motion';
  import { cubicOut } from 'svelte/easing';
  import { Plot, BarY, RuleY, Text } from 'svelteplot';
  import type { BridgeStep } from '../data/types';
  import { formatMoney, type MoneyScale } from '../data/format';

  let {
    steps = [],
    height = 280,
    emphasis = 0,
    currency = '',
    moneyScale = 'units',
  }: { steps?: BridgeStep[]; height?: number; emphasis?: number; currency?: string; moneyScale?: MoneyScale } = $props();

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
  const rawBars = $derived.by(() => {
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
        from,
        to,
        kind: step.kind,
        valueLabel: formatMoney(Math.abs(step.value), currency, moneyScale),
      };
    });
  });

  // The delta bars' own trajectory (every non-total step's from/to) — this is
  // the range actually worth spending chart height on. Sometimes a 'total'
  // bar's true length (e.g. RM56m) is an order of magnitude past this (e.g.
  // RM0.1-0.7m swings between it) — drawn to scale from zero, that dead space
  // would dwarf every delta bar into an invisible sliver. So a bar still
  // starts at 0 (real bar-chart semantics, not a floating marker) but the
  // 0-to-`near` stretch can compress into a smaller stub, controlled by
  // `emphasis` (0 = true scale throughout, 1 = maximally compressed) — a
  // slider, not a fixed heuristic, since whether a stretch reads as "empty
  // space" vs "several real components" is a judgment call the data alone
  // can't make (Revenue-to-NPAT's steps are all similarly-sized real
  // components with no dead space; a period-over-period delta against a
  // large total is the opposite). See docs/adr/0031.
  const deltaPoints = $derived(rawBars.filter((b) => b.kind !== 'total').flatMap((b) => [b.from, b.to]));
  const range = $derived.by(() => {
    if (deltaPoints.length === 0) return [0, 1];
    return [Math.min(...deltaPoints), Math.max(...deltaPoints)];
  });
  // Whichever end of the delta range sits closer to 0 is the far side of the
  // compressed stub; the other end is where true scale takes over.
  const near = $derived(Math.abs(range[0]) <= Math.abs(range[1]) ? range[0] : range[1]);
  const far = $derived(near === range[0] ? range[1] : range[0]);
  const trueSpan = $derived(Math.max(Math.abs(far - near), 1));
  const clampedEmphasis = $derived(Math.min(1, Math.max(0, emphasis)));
  // At emphasis=0 this equals |near| exactly, making plotValue the identity
  // function below — zero emphasis is always literally "no compression".
  const stub = $derived(Math.abs(near) * (1 - clampedEmphasis) + trueSpan * 0.25 * clampedEmphasis);
  const plotNear = $derived(near === 0 ? 0 : Math.sign(near) * stub);

  // Maps a real value to plot space: [0, near] maps to [0, plotNear]; [near,
  // far] (and beyond) always keeps true scale, offset to continue from
  // plotNear.
  function plotValue(v: number): number {
    if (near === 0) return v;
    const inStub = near > 0 ? v <= near : v >= near;
    return inStub ? (v / near) * plotNear : plotNear + (v - near);
  }

  const bars = $derived(rawBars.map((b) => ({ ...b, y1: plotValue(b.from), y2: plotValue(b.to) })));

  const allY = $derived(bars.flatMap((b) => [b.y1, b.y2]).concat(0));
  const yPad = $derived(Math.max(Math.max(...allY) - Math.min(...allY), 1) * 0.18);
  const yMin = $derived(Math.min(...allY) - yPad);
  const yMax = $derived(Math.max(...allY) + yPad);

  // Reveals the plot bottom-to-top on mount via a shrinking clip-path.
  const reveal = new Tween(0, { duration: 900, easing: cubicOut });
  onMount(() => {
    reveal.set(1);
  });
</script>

{#if bars.length}
  <div class="chart-colors w-full" style="clip-path: inset({(1 - reveal.current) * 100}% 0 0 0);">
    <Plot
      {height}
      marginBottom={50}
      x={{ label: false, domain: bars.map((b) => b.label), wordWrap: true }}
      y={{ label: false, axis: false, grid: false, domain: [yMin, yMax] }}
      color={{
        scheme: { total: 'var(--total)', increase: 'var(--increase)', decrease: 'var(--decrease)', neutral: 'var(--neutral)' },
      }}
    >
      <RuleY data={[0]} y={(d) => d} stroke="var(--axis)" />
      <BarY data={bars} sort={false} x="label" y1="y1" y2="y2" fill="kind" borderRadius={4} />
      <Text data={bars} x="label" y={(d) => Math.max(d.y1, d.y2)} text="valueLabel" dy={-12} textAnchor="middle" fontSize={11} />
    </Plot>
  </div>
{/if}

<style>
  .chart-colors {
    /* Total bars are start/end anchors, not a favourable/adverse value —
       indigo (the app's theme accent) keeps green/red reserved purely for
       the delta bars' own direction. */
    --total: var(--color-indigo-600);
    --increase: var(--color-green-600);
    --decrease: var(--color-red-600);
    --neutral: var(--color-gray-400);
    --axis: var(--color-gray-300);
  }
  :global(.dark) .chart-colors {
    --total: var(--color-indigo-400);
    --increase: var(--color-green-400);
    --decrease: var(--color-red-400);
    --neutral: var(--color-gray-500);
    --axis: var(--color-gray-600);
  }
</style>
