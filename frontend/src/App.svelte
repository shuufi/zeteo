<script lang="ts">
  import { onMount } from 'svelte';
  import Router from 'svelte-spa-router';
  import NavBar from './lib/components/NavBar.svelte';
  import { scopeState } from './lib/state/scope.svelte';
  import { loadScope } from './lib/data/gl-store.svelte';
  import Home from './routes/Home.svelte';
  import FinancialPerformance from './routes/FinancialPerformance.svelte';
  import VdtRanked from './routes/VdtRanked.svelte';
  import DriverDiagnostic from './routes/DriverDiagnostic.svelte';
  import AskZeteo from './routes/AskZeteo.svelte';
  import Initiatives from './routes/Initiatives.svelte';
  import NotFound from './routes/NotFound.svelte';

  const routes = {
    '/': Home,
    '/financial': FinancialPerformance,
    '/vdt/:id': VdtRanked,
    '/diagnostic/:id': DriverDiagnostic,
    '/diagnostic/:id/:tab': DriverDiagnostic,
    '/ask': AskZeteo,
    '/initiatives': Initiatives,
    '*': NotFound,
  };

  // Independent of BusinessPicker's mount — several routes hide ContextBar
  // (and so BusinessPicker) while their own data is loading, so the initial
  // GL tree fetch can't depend on that component ever rendering.
  onMount(() => {
    loadScope(scopeState.code);
  });
</script>

<NavBar />
<Router {routes} />
