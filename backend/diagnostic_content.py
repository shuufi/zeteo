"""Illustrative Driver Diagnostic depth for the one fully-modelled node.

Ported from the old mock's `repairs-maintenance` node onto its real GL/FSI
equivalent, PNL-0024 ("Repairs And Maintenance", under Cost of Revenue — see
docs/adr/0022). Every other node has none of this and renders NotYetModelled.
"""

FULLY_MODELLED_NODE = "PNL-0024"

DIAGNOSTIC_CONTENT = {
    FULLY_MODELLED_NODE: {
        "trend": [40, 35, 38, 20, 25, 10, 5, 8],
        "drivers": [
            {"id": "dry-dock", "label": "Unplanned dry-dock, Vessel A", "varAbs": 2_800_000.00, "varPct": 52, "direction": "adverse", "rank": 1},
            {"id": "spares-inflation", "label": "Spare parts price inflation", "varAbs": 1_400_000.00, "varPct": 26, "direction": "adverse", "rank": 2},
            {"id": "preventive-deferred", "label": "Preventive maint. deferred", "varAbs": 700_000.00, "varPct": 13, "direction": "adverse", "rank": 3},
        ],
        "sensitivity": {
            "mostSensitive": ["Dry-dock incidence", "Spares unit price"],
            "mostVariable": ["Spares unit price"],
        },
        "benchmark": {
            "metricLabel": "Repairs & Maintenance / Vessel Operating Day",
            "basis": "normalised per VOD, same vessel class (LNGC), FY26 YTD",
            "bars": [
                {"id": "vessel-a", "label": "Vessel A", "valuePerVod": 4120, "kind": "subject"},
                {"id": "fleet-median", "label": "Fleet Median", "valuePerVod": 2980, "kind": "internal"},
                {"id": "similar-class", "label": "Similar Class", "valuePerVod": 3110, "kind": "internal"},
                {"id": "external", "label": "External Bench.", "valuePerVod": 2750, "kind": "external"},
            ],
            "rows": [
                {"basis": "MISC Vessel A", "valuePerVod": 4120.00, "gap": "+38%"},
                {"basis": "Fleet median", "valuePerVod": 2980.00, "gap": "—"},
                {"basis": "Similar vessel class", "valuePerVod": 3110.00, "gap": "baseline"},
                {"basis": "External benchmark (industry, LNGC)", "valuePerVod": 2750.00, "gap": "data available FY25 only"},
            ],
        },
        "reviewSummary": "Cross-functional review: Finance × Petroleum Ops · 3 validated, 2 under review",
        "rootCause": [
            {
                "id": "dry-dock",
                "driverLabel": "Unplanned dry-dock, Vessel A",
                "amount": 2_800_000.00,
                "sharePct": 52,
                "type": "FACT",
                "evidenceOrRationale": "Evidence: work order #WO-4471, class survey report, invoice batch Q3",
                "mitigation": "Mitigation: schedule remaining dry-docks in off-peak charter windows",
                "status": "Validated",
                "analystNotes": "confirmed with Ops SME, 12 Aug",
            },
            {
                "id": "spares-inflation",
                "driverLabel": "Spare parts price inflation",
                "amount": 1_400_000.00,
                "sharePct": 26,
                "type": "AI_HYPOTHESIS",
                "confidence": "Medium",
                "evidenceOrRationale": "AI confidence: Medium — rationale: vendor invoice trend +14% QoQ, matched against 2 prior incident reports",
                "mitigation": "Proposed mitigation: renegotiate framework agreement with top-2 suppliers",
                "status": "AI proposed",
            },
            {
                "id": "preventive-deferred",
                "driverLabel": "Preventive maintenance deferred",
                "amount": 700_000.00,
                "sharePct": 13,
                "type": "AI_HYPOTHESIS",
                "confidence": "Low",
                "evidenceOrRationale": "AI confidence: Low — rationale: work-order pattern shift, no confirming SOP match found",
                "status": "Under review",
            },
        ],
    }
}
