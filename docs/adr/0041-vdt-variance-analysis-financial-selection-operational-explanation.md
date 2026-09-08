# VDT Variance Analysis selects financially and explains operationally

VDT Variance Analysis must not let the LLM choose which variance is worth discussing or merely restate a financial delta. The backend now ranks Posting Activity Accounts by absolute two-period delta, retains at most four contributors at or above 10% of gross leaf movement, and requires exactly one LLM bullet for each selected item. The LLM receives only those financial items and their Driver Formula terms, using native-unit A → B values to explain the movement; missing or unchanged operational evidence is named as unavailable or inconclusive rather than invented.

## Consequences

The headline calls out selected movements that offset, even when the root net variance is small. If no Posting Activity Account meets the threshold, the endpoint returns a deterministic distributed-movement result with no LLM call or bullets. Monetary impact remains structured for the client to scale, while operational evidence remains unit-native. Currency-rate terms include the selected Company's ISO currency and cadence (for example, `MYR/month`) and use thousands separators.

**Status**: accepted
