<script lang="ts">
  import Router from 'svelte-spa-router';
  import NavBar from './lib/components/NavBar.svelte';
  import Home from './routes/Home.svelte';
  import FinancialPerformance from './routes/FinancialPerformance.svelte';
  import VdtRanked from './routes/VdtRanked.svelte';
  import VdtTree from './routes/VdtTree.svelte';
  import DriverDiagnostic from './routes/DriverDiagnostic.svelte';
  import AskZeteo from './routes/AskZeteo.svelte';
  import Initiatives from './routes/Initiatives.svelte';
  import NotFound from './routes/NotFound.svelte';

  const routes = {
    '/': Home,
    '/financial': FinancialPerformance,
    '/vdt/:id': VdtRanked,
    '/vdt-tree/:id': VdtTree,
    '/diagnostic/:id': DriverDiagnostic,
    '/diagnostic/:id/:tab': DriverDiagnostic,
    '/ask': AskZeteo,
    '/initiatives': Initiatives,
    '*': NotFound,
  };
</script>

<NavBar />
<Router {routes} />
