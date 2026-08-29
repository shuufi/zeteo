# Fake GL fact data covers a 9-company sample, not the full company list; Business chip stops being purely decorative

ADR-0015 made the Business chip a live BU/Company picker but explicitly kept it decorative with respect to data, because "no mock node in `zeteo-data.ts` is scoped per-company." That's no longer true: the new GL fact table is scoped per company, so picking one now changes the numbers shown. Seeding all ~86 companies (`backend/data/companies.json`) at 1011 leaf accounts × 12 months × 3 scenarios each would be ~2.9M rows for a fake dataset whose only job is proving the plumbing works, so only a sample gets fact data: 3 companies per BU (AET: 3 of 57, OBU: 3 of 26; MMS/SUPSB/ALAM have exactly 1 company each, so all three are fully covered) — 9 companies, ~327k rows total.

Selecting a company outside the sample renders the existing `NotYetModelled` state (same precedent as ADR-0004, extended to a new trigger: missing fact data for the selected scope, not missing diagnostic depth). Selecting a BU as a whole shows the sum of only that BU's sampled companies, visibly labelled as partial (e.g. "3 of 57 companies") rather than presented as if it were the true BU total.

Rejected: seeding fact data for every company — correct but disproportionate effort for a fake dataset; and silently showing a full-BU-shaped total with no partial label — that would misrepresent a 3-of-57 sample as complete.

**Status**: accepted
