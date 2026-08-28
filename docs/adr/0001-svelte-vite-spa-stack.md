# Frontend stack: plain Svelte + Vite + svelte-spa-router, not SvelteKit

URS section 4.4.1 (SA-4) specifies "FastAPI for the backend service layer, and Svelte with Vite for the frontend build," with FastAPI as the backend of record and eventual hosting on Databricks Apps. We built the prototype as a plain Svelte 5 + Vite SPA with `svelte-spa-router` for client-side routing, rather than SvelteKit, so the build is static assets FastAPI can serve directly with no second server runtime to reconcile. TypeScript is used throughout (`svelte-ts` template) per explicit user requirement.

**Status**: accepted
