# FastAPI's first real endpoint reads a checked-in JSON file, not a database

The backend has been an unbuilt stub since `0001`/`0002` — no endpoints, no DB, no schema. The Business picker needs a MISC group-of-companies list (BU → legal entity, ~86 rows from an internal export) that changes over time as more BUs are added. Rather than standing up a first database/migration/schema for the whole app just to serve this one dropdown, FastAPI serves `GET /api/companies` by reading `backend/data/companies.json` (converted once from the source CSV, encoding-fixed) directly off disk. Adding a BU is a file edit + restart, not a migration.

Rejected: a real DB table now — the schema/migration choice would set precedent for how URS SA-4's backend gets built generally, which is a bigger decision than "one dropdown's data source" and shouldn't be made as a side effect of this feature.

**Status**: accepted
