<script lang="ts">
  import { onMount } from 'svelte';
  import Router from 'svelte-spa-router';
  import NavBar from './lib/components/NavBar.svelte';
  import { scopeState } from './lib/state/scope.svelte';
  import { periodState } from './lib/state/period.svelte';
  import { loadScope } from './lib/data/gl-store.svelte';
  import Home from './routes/Home.svelte';
  import FinancialPerformance from './routes/FinancialPerformance.svelte';
  import FinancialComparison from './routes/FinancialComparison.svelte';
  import VdtComparison from './routes/VdtComparison.svelte';
  import VdtExplorerRedirect from './routes/VdtExplorerRedirect.svelte';
  import VdtRanked from './routes/VdtRanked.svelte';
  import VdtTree from './routes/VdtTree.svelte';
  import VdtReconciliation from './routes/VdtReconciliation.svelte';
  import DriverDiagnostic from './routes/DriverDiagnostic.svelte';
  import AskZeteo from './routes/AskZeteo.svelte';
  import Initiatives from './routes/Initiatives.svelte';
  import NotFound from './routes/NotFound.svelte';

  const routes = {
    '/': Home,
    '/financial': FinancialPerformance,
    '/financial/compare': FinancialComparison,
    '/vdt': VdtExplorerRedirect,
    '/vdt/compare': VdtComparison,
    '/vdt/reconciliation': VdtReconciliation,
    '/vdt/:id': VdtRanked,
    '/vdt-tree': VdtTree,
    '/vdt-tree/:id': VdtTree,
    '/diagnostic/:id': DriverDiagnostic,
    '/diagnostic/:id/:tab': DriverDiagnostic,
    '/ask': AskZeteo,
    '/initiatives': Initiatives,
    '*': NotFound,
  };

  // Independent of BusinessPicker's/PeriodPicker's mount — several routes hide
  // ContextBar (and so both pickers) while their own data is loading, so the
  // initial GL tree fetch can't depend on either component ever rendering.
  onMount(() => {
    loadScope(scopeState.code, periodState.code);
  });
</script>

<div class="flex min-h-screen flex-col">
  <NavBar />
  <div class="flex flex-1 flex-col min-h-0 min-w-0">
    <Router {routes} />
  </div>
</div>
