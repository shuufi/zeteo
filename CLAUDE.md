# Zeteo documentation contract

Zeteo's root `README.md` is the documentation entry point. It
links to focused, present-tense guides under `docs/`; it is not a replacement
for them.

The current-state guides describe what Zeteo does now. ADRs in `docs/adr/`
remain historical decision records and rationale, not the primary current-state
reference. Link to an ADR when the rationale helps, but do not require readers
to reconstruct current behavior from ADR history.

Keep these distinctions explicit:

- ERP-owned imported reference data versus Zeteo-owned master data.
- The present POC SQLite serving model as a provisional logical Gold
  candidate, versus any future governed medallion implementation.
- Working POC capabilities versus demonstration/prototype, planned, and
  proposed behavior.

When created, Zeteo's focused guides must cover the current business
capabilities/reports, the technical architecture and runtime/data flows, and
the field-level data catalogue. The catalogue covers every persisted table
and field, including facts and `app_settings`, with its meaning, type,
relationship, ownership/source, and usage.

Update the relevant guide in the same change whenever a capability, report
contract, persisted schema, ownership boundary, API, or runtime flow changes.
Use Mermaid only when it makes a relationship or flow clearer; diagrams show
the current POC unless explicitly labelled proposed.
