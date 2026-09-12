"""Variance Analysis selects financial contributors before narrating operational evidence."""

import pytest

from backend.diagnostics.variance_analysis import (
    VarianceAnalysisUnavailable,
    _parse_variance_analysis,
    _select_contributors,
    build_variance_analysis_prompt,
    generate_variance_analysis,
)


NODES = {
    "ROOT": {
        "id": "ROOT",
        "name": "Crew Cost",
        "nodeType": "VDT Hierarchy Node",
        "unit": "money",
        "valueA": -1_000.00,
        "valueB": -1_655.00,
        "delta": -655.00,
        "deltaPct": 65.5,
        "childIds": ["SENIOR", "JUNIOR", "TRAVEL", "ACCOMMODATION", "TINY"],
    },
    "SENIOR": {
        "id": "SENIOR",
        "name": "Senior crew salaries",
        "nodeType": "VDT Account",
        "unit": "money",
        "valueA": -1_000.00,
        "valueB": -1_500.00,
        "delta": -500.00,
        "deltaPct": 50.0,
        "childIds": ["SENIOR::FORMULA"],
    },
    "SENIOR::FORMULA": {
        "id": "SENIOR::FORMULA",
        "name": "Senior crew salary formula",
        "nodeType": "Driver Formula",
        "unit": "money",
        "expression": "Senior crew count × senior salary rate",
        "valueA": -1_000.00,
        "valueB": -1_500.00,
        "delta": -500.00,
        "deltaPct": 50.0,
        "childIds": ["SENIOR::COUNT", "SENIOR::RATE"],
    },
    "SENIOR::COUNT": {
        "id": "SENIOR::COUNT",
        "name": "Senior crew count",
        "nodeType": "Driver",
        "unit": "count",
        "valueA": 5.0,
        "valueB": 20.0,
        "delta": 15.0,
        "deltaPct": 300.0,
        "childIds": [],
    },
    "SENIOR::RATE": {
        "id": "SENIOR::RATE",
        "name": "Senior salary rate",
        "nodeType": "Driver",
        "unit": "currency-per-month",
        "valueA": 100.0,
        "valueB": 100.0,
        "delta": 0.0,
        "deltaPct": 0.0,
        "childIds": [],
    },
    "JUNIOR": {
        "id": "JUNIOR",
        "name": "Junior crew salaries",
        "nodeType": "VDT Account",
        "unit": "money",
        "valueA": -400.00,
        "valueB": -600.00,
        "delta": -200.00,
        "deltaPct": 50.0,
        "childIds": [],
    },
    "TRAVEL": {
        "id": "TRAVEL",
        "name": "Crew travel",
        "nodeType": "VDT Account",
        "unit": "money",
        "valueA": -900.00,
        "valueB": -750.00,
        "delta": 150.00,
        "deltaPct": -16.7,
        "childIds": [],
    },
    "ACCOMMODATION": {
        "id": "ACCOMMODATION",
        "name": "Crew accommodation",
        "nodeType": "VDT Account",
        "unit": "money",
        "valueA": -100.00,
        "valueB": -200.00,
        "delta": -100.00,
        "deltaPct": 100.0,
        "childIds": [],
    },
    "TINY": {
        "id": "TINY",
        "name": "Training",
        "nodeType": "VDT Account",
        "unit": "money",
        "valueA": -20.00,
        "valueB": -25.00,
        "delta": -5.00,
        "deltaPct": 25.0,
        "childIds": [],
    },
}


def test_selects_only_material_vdt_accounts_by_gross_movement():
    selected = _select_contributors(NODES)

    # Gross movement is 955, so the 10% floor is 95.5. The tiny line is
    # excluded; the remaining candidates are ordered by absolute delta.
    assert [node["id"] for node in selected] == ["SENIOR", "JUNIOR", "TRAVEL", "ACCOMMODATION"]


def test_prompt_requires_complete_operational_evidence_for_selected_financial_items():
    prompt = build_variance_analysis_prompt("ROOT", NODES, "FY26-M01", "FY26-M02", "MYR")

    assert "exactly 4 bullets" in prompt
    assert "Senior crew count (count): 5 -> 20 (changed)" in prompt
    assert "Senior salary rate (MYR/month): MYR 100.00 -> MYR 100.00 (unchanged)" in prompt
    assert "operational decomposition is unavailable" in prompt
    assert "TINY" not in prompt
    assert "they offset each other" in prompt
    assert "including an ISO currency code and per-day/month unit" in prompt


def test_prompt_marks_static_formula_terms_as_inconclusive():
    nodes = {
        **NODES,
        "SENIOR::COUNT": {**NODES["SENIOR::COUNT"], "valueB": 5.0},
    }

    prompt = build_variance_analysis_prompt("ROOT", nodes, "FY26-M01", "FY26-M02")

    assert "Operational evidence: inconclusive" in prompt
    assert "operational evidence is inconclusive" in prompt


def test_prompt_formats_currency_rate_terms_with_company_currency_and_thousands_separators():
    nodes = {
        **NODES,
        "SENIOR::RATE": {**NODES["SENIOR::RATE"], "valueA": 10_421.07, "valueB": 10_825.39},
    }

    prompt = build_variance_analysis_prompt("ROOT", nodes, "FY26-M01", "FY26-M02", "MYR")

    assert "Senior salary rate (MYR/month): MYR 10,421.07 -> MYR 10,825.39 (changed)" in prompt


def test_parser_requires_exact_coverage_and_returns_financial_selection_order():
    result = _parse_variance_analysis(
        """{
          "headline": "Cost movements offset each other.",
          "bullets": [
            {"nodeId":"ACCOMMODATION","text":"Operational decomposition is unavailable."},
            {"nodeId":"TRAVEL","text":"Operational decomposition is unavailable."},
            {"nodeId":"JUNIOR","text":"Operational decomposition is unavailable."},
            {"nodeId":"SENIOR","text":"Senior crew count increased from 5 to 20; Senior salary rate was unchanged at 100.00."}
          ]
        }""",
        "ROOT",
        NODES,
    )

    assert [bullet["nodeId"] for bullet in result["bullets"]] == ["SENIOR", "JUNIOR", "TRAVEL", "ACCOMMODATION"]
    assert result["bullets"][0]["amount"] == -500.00
    assert result["bullets"][0]["contributionPct"] == 76.3


def test_parser_rejects_an_omitted_selected_financial_item():
    with pytest.raises(VarianceAnalysisUnavailable, match="exactly one bullet"):
        _parse_variance_analysis(
            '{"headline":"Crew cost increased.","bullets":[{"nodeId":"SENIOR","text":"Senior crew count increased from 5 to 20."}]}',
            "ROOT",
            NODES,
        )


def test_no_material_contributor_returns_deterministic_diffuse_result_without_llm():
    child_ids = [f"LEAF-{index}" for index in range(11)]
    nodes = {
        "ROOT": {
            "id": "ROOT",
            "name": "Crew Cost",
            "nodeType": "VDT Hierarchy Node",
            "unit": "money",
            "valueA": -100.0,
            "valueB": -100.0,
            "delta": 0.0,
            "deltaPct": 0.0,
            "childIds": child_ids,
        },
        **{
            child_id: {
                "id": child_id,
                "name": f"Small item {index}",
                "nodeType": "VDT Account",
                "unit": "money",
                "valueA": -10.0,
                "valueB": -11.0,
                "delta": -1.0,
                "deltaPct": 10.0,
                "childIds": [],
            }
            for index, child_id in enumerate(child_ids)
        },
    }

    # Each of 11 leaves accounts for 9.1% of gross movement, so none reaches
    # the 10% materiality floor and this succeeds without an API key.
    result = generate_variance_analysis(("diffuse-test",), "ROOT", nodes, "FY26-M01", "FY26-M02")

    assert result["bullets"] == []
    assert "distributed across smaller" in result["headline"]
