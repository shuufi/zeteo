# Store absolute Company-local money and scale only for presentation

Monetary facts and rates are exact two-decimal amounts in each Company's required ISO 4217 local currency, stored and returned unscaled; Driver Formulas retain full decimal precision and round each final Company × Month × Scenario monetary target once using round-half-up. `docs/misc_companies.csv` replaces the generated `companies.json` as Company master data, `RM_M` is replaced by generic money plus separate currency metadata, and Business Unit/MISC Group monetary scopes are rejected until explicit FX conversion exists—superseding the partial-rollup behavior in ADR-0028 and the million-scaled assumptions in ADR-0023/0030/0033. Units/thousands/millions/billions are presentation-only, selected automatically per live Company-scoped screen with an immediate screen-local override; Home's independent static prototype content remains a follow-up.

**Status**: accepted
