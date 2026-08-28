# Monorepo layout: docs / backend / frontend at repo root

The repo started as a single `wireframe\` folder holding only requirements docs and a claude.ai/design-linked wireframe. We restructured to a monorepo at `C:\Shuf\Dev\zeteo\` with `docs\` (requirements, design brief), `backend\` (stub, unbuilt — FastAPI per ADR 0001), and `frontend\` (the Svelte prototype). `wireframe\` was dissolved; the source `.dc.html` wireframe continues to live in the claude.ai design project and is pulled via DesignSync when needed rather than mirrored on disk.

**Status**: accepted
