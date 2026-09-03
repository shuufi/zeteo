<script lang="ts">
  import { untrack } from 'svelte';
  import { slide } from 'svelte/transition';
  import { link } from 'svelte-spa-router';
  import { indentClass } from '../data/gl-client';
  import type { DisplayRow, Direction, OperationalUnit } from '../data/types';

  /**
   * One value column of the statement (a month, a comparison period, a
   * side-by-side hierarchy, …). `isDelta` marks the one column (if any)
   * eligible for favourable/adverse coloring and the "(±X.X%)" suffix — see
   * `showDeltaColoring`/`cellDirection`/`cellDeltaPct` below.
   */
  export interface StatementColumn {
    key: string;
    label: string;
    isDelta?: boolean;
  }

  interface CellLink {
    href: string;
    title: string;
  }

  /**
   * Shared statement table behind Financial Trends (12 monthly columns) and
   * Financial Comparison (Period A / Period B / Δ columns) — see
   * docs/adr/0033's Phase 0. Owns expand/collapse state, subtotal/final-row
   * shading, driver/operational-row rendering and the resizable line-item
   * column; callers just supply already-built `DisplayRow[]` plus column
   * config. Designed to also fit a 1-column layout and a 2-column
   * side-by-side layout with delta coloring off (later VDT consumers).
   */
  let {
    rows,
    columns,
    cellValue,
    rowExists = () => true,
    cellHref,
    cellDirection,
    cellDeltaPct,
    showDeltaColoring = false,
    labelFor = (row: DisplayRow) => row.label,
    showLabelTooltip = false,
    resizable = false,
    initialLineItemWidth = 280,
    lineItemMinWidth = 160,
    lineItemMaxWidth = 640,
    columnMinWidthPx = 64,
    minTableWidthPx = 640,
    resetKey = undefined,
  }: {
    rows: DisplayRow[];
    columns: StatementColumn[];
    cellValue: (row: DisplayRow, column: StatementColumn, index: number) => number;
    rowExists?: (row: DisplayRow) => boolean;
    cellHref?: (row: DisplayRow, column: StatementColumn, index: number) => CellLink | undefined;
    cellDirection?: (row: DisplayRow) => Direction;
    cellDeltaPct?: (row: DisplayRow) => number | null;
    showDeltaColoring?: boolean;
    labelFor?: (row: DisplayRow) => string;
    showLabelTooltip?: boolean;
    resizable?: boolean;
    initialLineItemWidth?: number;
    lineItemMinWidth?: number;
    lineItemMaxWidth?: number;
    columnMinWidthPx?: number;
    minTableWidthPx?: number;
    resetKey?: unknown;
  } = $props();

  // User-resizable via the drag handle next to the header — width persists
  // for the session but isn't saved beyond it (no ask for that). Only the
  // prop's initial value seeds the state deliberately — later prop changes
  // shouldn't fight the user's own drag-resize.
  let lineItemWidth = $state(untrack(() => initialLineItemWidth));

  function startResize(event: PointerEvent): void {
    event.preventDefault();
    const startX = event.clientX;
    const startWidth = lineItemWidth;
    function onMove(e: PointerEvent): void {
      lineItemWidth = Math.min(
        lineItemMaxWidth,
        Math.max(lineItemMinWidth, startWidth + (e.clientX - startX)),
      );
    }
    function onUp(): void {
      window.removeEventListener('pointermove', onMove);
      window.removeEventListener('pointerup', onUp);
    }
    window.addEventListener('pointermove', onMove);
    window.addEventListener('pointerup', onUp);
  }

  const gridTemplateColumns = $derived(
    resizable
      ? `${lineItemWidth}px repeat(${columns.length}, minmax(${columnMinWidthPx}px,1fr))`
      : `1fr repeat(${columns.length}, minmax(${columnMinWidthPx}px,1fr))`,
  );

  const rowsByNodeId = $derived(new Map(rows.map((row) => [row.nodeId, row])));
  const collapsibleIds = $derived(
    new Set(rows.map((row) => row.group).filter((g): g is string => g !== undefined)),
  );
  // Groups whose children are purely operational drivers start collapsed — they're
  // supplementary detail, so the statement stays readable by default.
  const operationalGroupIds = $derived(
    new Set(
      rows
        .filter((row) => row.kind === 'operational')
        .map((row) => row.group)
        .filter((g): g is string => g !== undefined),
    ),
  );
  // Groups above hierarchy level 1 auto-expand; level 1 and deeper (leaf
  // nodes and whatever's nested under them) start collapsed — see
  // docs/adr/0029.
  const summaryGroupIds = $derived(
    new Set([...collapsibleIds].filter((id) => (rowsByNodeId.get(id)?.indent ?? 0) < 1)),
  );

  let expandedGroups = $state<Set<string>>(new Set());
  let expandedGroupsInitialised = false;
  $effect(() => {
    if (expandedGroupsInitialised || rows.length === 0) return;
    expandedGroupsInitialised = true;
    expandedGroups = new Set([...summaryGroupIds].filter((id) => !operationalGroupIds.has(id)));
  });
  // Re-run initial-collapse whenever the caller's resetKey changes (e.g.
  // Comparison's chosen statement node) — a no-op for callers that never
  // pass one (e.g. Trends, whose root never changes).
  $effect(() => {
    resetKey;
    expandedGroupsInitialised = false;
  });

  function toggleGroup(nodeId: string): void {
    const next = new Set(expandedGroups);
    if (next.has(nodeId)) next.delete(nodeId);
    else next.add(nodeId);
    expandedGroups = next;
  }

  function isVisible(row: DisplayRow): boolean {
    let group = row.group;
    while (group) {
      if (!expandedGroups.has(group)) return false;
      group = rowsByNodeId.get(group)?.group;
    }
    return true;
  }

  const visibleRows = $derived(rows.filter(isVisible).filter(rowExists));

  // Values already carry the right sign server-side (see docs/adr/0023) — a
  // negative number is a subtraction/loss, shown in parens.
  function statementValue(value: number): string {
    const text = Math.abs(value).toFixed(1);
    return value < 0 && value !== 0 ? `(${text})` : text;
  }

  function operationalValue(value: number, unit: OperationalUnit | 'RM_M' | undefined): string {
    switch (unit) {
      case 'RM_M':
        // A Driver Formula bound to a GL leaf produces money — same signed,
        // parens-for-negative treatment as any other statement row.
        return statementValue(value);
      case 'usd-per-day':
        // Small values (e.g. an RM_M-scaled Driver Formula term — see
        // docs/adr/0030) need more than 0 decimals or they'd all show "$0k/d".
        return value < 10 ? `$${value.toFixed(3)}k/d` : `$${value.toFixed(0)}k/d`;
      case 'usd-per-month':
        return value < 10 ? `$${value.toFixed(3)}k/mo` : `$${value.toFixed(0)}k/mo`;
      case 'percent':
        return `${value.toFixed(1)}%`;
      case 'days':
        return value.toFixed(1);
      case 'count':
        return value.toFixed(0);
      case 'ratio':
        return `${value.toFixed(2)}×`;
      default:
        return value.toFixed(1);
    }
  }

  function deltaPctLabel(deltaPct: number | null): string {
    if (deltaPct === null) return '';
    const sign = deltaPct > 0 ? '+' : '';
    return ` (${sign}${deltaPct.toFixed(1)}%)`;
  }

  // Favourable/adverse only applies to GL rows (see docs/adr/0031) — operational
  // (Driver/Formula) rows always render their delta neutral, regardless of sign.
  function deltaTextClass(row: DisplayRow, direction: Direction): string {
    if (row.kind === 'operational') return 'text-gray-500 dark:text-gray-400';
    if (direction === 'favourable') return 'text-emerald-600 dark:text-emerald-400';
    if (direction === 'adverse') return 'text-red-600 dark:text-red-400';
    return 'text-gray-500 dark:text-gray-400';
  }

  // Coloring is opt-in (`showDeltaColoring`) and only ever applies to the
  // column flagged `isDelta` — the two eventual 1-column/2-column consumers
  // never set either, so this always resolves to '' for them.
  function colorClassFor(row: DisplayRow, column: StatementColumn, suppressForFinal: boolean): string {
    if (!column.isDelta || !showDeltaColoring || !cellDirection) return '';
    if (suppressForFinal && row.isFinal) return '';
    return deltaTextClass(row, cellDirection(row));
  }

  function cellText(row: DisplayRow, column: StatementColumn, index: number): string {
    const raw = cellValue(row, column, index);
    const text = row.kind === 'operational' ? operationalValue(raw, row.unit) : statementValue(raw);
    const suffix = column.isDelta && cellDeltaPct ? deltaPctLabel(cellDeltaPct(row)) : '';
    return `${text}${suffix}`;
  }
</script>

{#snippet truncatedLabel(row: DisplayRow)}
  {#if showLabelTooltip}
    <span class="group/label relative min-w-0">
      <span class="truncate block">{labelFor(row)}</span>
      <span
        class="pointer-events-none absolute left-0 top-full z-30 mt-1 hidden whitespace-nowrap rounded bg-gray-900 dark:bg-gray-700 px-2 py-1 text-xs font-normal text-white shadow-lg group-hover/label:block"
      >
        {labelFor(row)}
      </span>
    </span>
  {:else}
    <span class="truncate">{labelFor(row)}</span>
  {/if}
{/snippet}

{#snippet valueCell(row: DisplayRow, column: StatementColumn, index: number, colorClass: string)}
  {@const link_ = row.kind !== 'operational' && cellHref ? cellHref(row, column, index) : undefined}
  {#if link_}
    <a
      class="group/cell flex items-center justify-end gap-1 no-underline text-inherit tabular-nums {colorClass}"
      href={link_.href}
      use:link
      onclick={(e) => e.stopPropagation()}
      title={link_.title}
    >
      <span>{cellText(row, column, index)}</span>
      <svg
        class="w-3 h-3 shrink-0 text-indigo-500 dark:text-indigo-400 opacity-0 group-hover/cell:opacity-100 transition-opacity"
        viewBox="0 0 24 24"
        fill="none"
        stroke="currentColor"
        stroke-width="2.5"
      >
        <circle cx="10.5" cy="10.5" r="6.5" />
        <line x1="16" y1="16" x2="21" y2="21" />
      </svg>
    </a>
  {:else}
    <span class="text-right tabular-nums {colorClass}">{cellText(row, column, index)}</span>
  {/if}
{/snippet}

{#snippet operationalCells(row: DisplayRow, isCollapsible: boolean)}
  <span class="{indentClass(row.indent)} flex flex-col min-w-0">
    <span class="flex items-center gap-1.5 min-w-0">
      {#if isCollapsible}
        <span
          class="inline-block w-4 shrink-0 text-base leading-none text-amber-600 dark:text-amber-400 transition-transform duration-150 {expandedGroups.has(
            row.nodeId,
          )
            ? 'rotate-90'
            : ''}"
        >
          ▸
        </span>
      {/if}
      <span
        class="text-[9px] uppercase tracking-wide font-semibold text-amber-600 dark:text-amber-400 border border-amber-300 dark:border-amber-400/40 rounded px-1 shrink-0"
        >{row.driverNodeType === 'formula' ? 'Formula' : 'Ops'}</span
      >
      {@render truncatedLabel(row)}
    </span>
    {#if row.driverNodeType === 'formula' && row.expression}
      <span
        class="truncate text-[10px] font-normal normal-case tracking-normal text-amber-600/70 dark:text-amber-400/60 {isCollapsible
          ? 'pl-6'
          : ''}"
        title={row.expression}
      >
        {row.expression}
      </span>
    {/if}
  </span>
  {#each columns as column, i (column.key)}
    {@render valueCell(row, column, i, colorClassFor(row, column, false))}
  {/each}
{/snippet}

<div class="overflow-x-auto">
  <div class="relative flex flex-col" style="min-width: {minTableWidthPx}px">
    {#if resizable}
      <div
        role="separator"
        aria-orientation="vertical"
        onpointerdown={startResize}
        class="absolute top-0 bottom-0 w-2.5 -translate-x-1/2 cursor-col-resize touch-none z-10 group/resize"
        style="left: {lineItemWidth}px"
      >
        <div
          class="mx-auto h-full w-px bg-transparent group-hover/resize:bg-indigo-400 dark:group-hover/resize:bg-indigo-500"
        ></div>
      </div>
    {/if}
    <div
      class="grid items-center py-1 text-xs text-indigo-700 dark:text-indigo-300 border-b border-indigo-200 dark:border-indigo-900"
      style="grid-template-columns: {gridTemplateColumns}"
    >
      <span>Line item</span>
      {#each columns as column (column.key)}
        <span class="flex items-center justify-end gap-1">
          {column.label}
          {#if cellHref}
            <svg class="w-3 h-3 shrink-0 invisible" viewBox="0 0 24 24"
              ><circle cx="10.5" cy="10.5" r="6.5" /></svg
            >
          {/if}
        </span>
      {/each}
    </div>
    {#each visibleRows as row (row.nodeId)}
      {#if row.kind === 'operational'}
        {#if collapsibleIds.has(row.nodeId)}
          <div
            role="button"
            tabindex="0"
            onclick={() => toggleGroup(row.nodeId)}
            onkeydown={(e) => {
              if (e.key === 'Enter' || e.key === ' ') {
                e.preventDefault();
                toggleGroup(row.nodeId);
              }
            }}
            transition:slide={{ duration: 150 }}
            class="grid items-center py-1.5 text-sm cursor-pointer text-amber-700 dark:text-amber-400 bg-amber-50/60 dark:bg-amber-400/10"
            style="grid-template-columns: {gridTemplateColumns}"
          >
            {@render operationalCells(row, true)}
          </div>
        {:else}
          <div
            transition:slide={{ duration: 150 }}
            class="grid items-center py-1.5 text-sm text-amber-700 dark:text-amber-400 bg-amber-50/60 dark:bg-amber-400/10"
            style="grid-template-columns: {gridTemplateColumns}"
          >
            {@render operationalCells(row, false)}
          </div>
        {/if}
      {:else if collapsibleIds.has(row.nodeId)}
        <div
          role="button"
          tabindex="0"
          onclick={() => toggleGroup(row.nodeId)}
          onkeydown={(e) => {
            if (e.key === 'Enter' || e.key === ' ') {
              e.preventDefault();
              toggleGroup(row.nodeId);
            }
          }}
          transition:slide={{ duration: 150 }}
          class="grid items-center py-1.5 text-sm cursor-pointer text-gray-700 dark:text-gray-300 hover:bg-indigo-50 dark:hover:bg-indigo-950/40 {row.isSubtotal
            ? 'font-bold bg-indigo-50 dark:bg-indigo-900/30 rounded'
            : ''}"
          style="grid-template-columns: {gridTemplateColumns}"
        >
          <span
            class="flex items-center gap-1.5 min-w-0 {indentClass(
              row.indent,
            )} {row.indent > 0
              ? 'text-gray-500 dark:text-gray-400'
              : ''}"
          >
            <span
              class="inline-block w-4 shrink-0 text-base leading-none text-indigo-600 dark:text-indigo-400 transition-transform duration-150 {expandedGroups.has(
                row.nodeId,
              )
                ? 'rotate-90'
                : ''}"
            >
              ▸
            </span>
            {@render truncatedLabel(row)}
          </span>
          {#each columns as column, i (column.key)}
            {@render valueCell(row, column, i, colorClassFor(row, column, false))}
          {/each}
        </div>
      {:else}
        <div
          transition:slide={{ duration: 150 }}
          class="grid items-center py-1.5 text-sm text-gray-700 dark:text-gray-300 hover:bg-indigo-50 dark:hover:bg-indigo-950/40 {row.isSubtotal
            ? 'font-bold bg-indigo-50 dark:bg-indigo-900/30 rounded'
            : ''} {row.isFinal
            ? 'bg-indigo-600 dark:bg-indigo-500 text-white rounded pl-1.5'
            : ''}"
          style="grid-template-columns: {gridTemplateColumns}"
        >
          <span
            class="flex min-w-0 {row.indent > 0
              ? `${indentClass(row.indent)} text-gray-500 dark:text-gray-400`
              : ''}"
          >
            {@render truncatedLabel(row)}
          </span>
          {#each columns as column, i (column.key)}
            {@render valueCell(row, column, i, colorClassFor(row, column, true))}
          {/each}
        </div>
      {/if}
    {/each}
  </div>
</div>
