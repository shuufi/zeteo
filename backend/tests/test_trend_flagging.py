"""Trend Analysis flagging is deterministic dollar-impact + root-share threshold logic —
see docs/adr/0040. Pure function over a hand-built tree dict, no DB needed."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from trend_flagging import MAX_FLAGGED_NODES, flag_trends  # noqa: E402


def _leaf(name: str, actual: list[float], budget: list[float] | None = None, parent: str = "ROOT") -> dict:
    return {
        "name": name,
        "nodeType": "Posting GL Account",
        "monthlyActual": actual,
        "monthlyBudget": budget if budget is not None else [0.0] * 12,
        "childIds": [],
        "parentId": parent,
    }


def _tree(**leaves: dict) -> dict[str, dict]:
    root_series = [1000.0] * 12
    tree = {
        "ROOT": {
            "name": "Root",
            "nodeType": "Activity Node",
            "monthlyActual": root_series,
            "monthlyBudget": root_series,
            "childIds": list(leaves.keys()),
            "parentId": None,
        }
    }
    tree.update(leaves)
    return tree


def test_flags_only_when_both_thresholds_hold():
    tree = _tree(
        # Big enough (> 5% of 1000 = 50) and moves > 15% MoM.
        BIG=_leaf("Big Line", [100] * 5 + [200] * 7),
        # Moves 200% MoM but stays under the 5%-of-root share threshold.
        SMALL=_leaf("Small Line", [1] * 5 + [3] * 7),
        # Above the root-share threshold but MoM change stays under 15%.
        STEADY=_leaf("Steady Line", [100] * 12),
    )

    flags = flag_trends(tree, "ROOT", "actual")
    flagged_ids = {f["nodeId"] for f in flags}

    assert flagged_ids == {"BIG"}


def test_january_index_zero_is_never_flagged():
    # A huge drop from Jan (index 0) to Feb (index 1) legitimately flags Feb,
    # but Jan itself must never appear as a flagged month.
    tree = _tree(JANSPIKE=_leaf("Jan Spike", [900] + [100] * 11))

    flags = flag_trends(tree, "ROOT", "actual")

    assert len(flags) == 1
    month_indices = {m["monthIndex"] for m in flags[0]["flaggedMonths"]}
    assert 0 not in month_indices
    assert 1 in month_indices


def test_from_zero_movement_flags_without_a_mom_percentage():
    tree = _tree(ZEROSTART=_leaf("Zero Start", [0] * 6 + [60] * 6))

    flags = flag_trends(tree, "ROOT", "actual")

    assert len(flags) == 1
    flagged_month = next(m for m in flags[0]["flaggedMonths"] if m["monthIndex"] == 6)
    assert flagged_month["momPct"] is None
    assert flagged_month["direction"] == "increased"


def test_ranking_is_by_dollar_impact_of_movement_not_percentage():
    tree = _tree(
        # 100% move but small dollar impact (500 -> 1000... wait keep simple)
        BIGIMPACT=_leaf("Big Impact", [100] * 5 + [900] * 7),  # impact 800, > root share
        SMALLIMPACT=_leaf("Small Impact", [60] * 5 + [120] * 7),  # impact 60, > root share
    )

    flags = flag_trends(tree, "ROOT", "actual")

    assert [f["nodeId"] for f in flags] == ["BIGIMPACT", "SMALLIMPACT"]


def test_cap_at_max_flagged_nodes():
    leaves = {
        f"LEAF{i}": _leaf(f"Leaf {i}", [100] * 5 + [100 + i * 20] * 7) for i in range(1, MAX_FLAGGED_NODES + 5)
    }
    tree = _tree(**leaves)

    flags = flag_trends(tree, "ROOT", "actual")

    assert len(flags) == MAX_FLAGGED_NODES


def test_budget_scenario_reads_monthly_budget_series():
    tree = _tree(BUDGETMOVE=_leaf("Budget Mover", actual=[100] * 12, budget=[100] * 5 + [200] * 7))

    actual_flags = flag_trends(tree, "ROOT", "actual")
    budget_flags = flag_trends(tree, "ROOT", "budget")

    assert actual_flags == []
    assert len(budget_flags) == 1
    assert budget_flags[0]["nodeId"] == "BUDGETMOVE"


def test_leaves_outside_roots_subtree_are_never_flagged():
    # build_vdt_tree() returns every Reporting Root's full reach, not just
    # the requested anchor's own branch — a big mover elsewhere in the tree
    # must never be flagged against a root it doesn't roll up to.
    tree = _tree(INSCOPE=_leaf("In Scope", [100] * 5 + [200] * 7))
    tree["OUTSIDE"] = _leaf("Outside Root's Subtree", [100] * 5 + [900] * 7, parent="OTHER_ROOT")
    tree["OTHER_ROOT"] = {
        "name": "Other Root",
        "nodeType": "Reporting Root",
        "monthlyActual": [1000.0] * 12,
        "monthlyBudget": [1000.0] * 12,
        "childIds": ["OUTSIDE"],
        "parentId": None,
    }

    flags = flag_trends(tree, "ROOT", "actual")

    assert {f["nodeId"] for f in flags} == {"INSCOPE"}


def test_quiet_year_returns_empty_list():
    tree = _tree(STEADY=_leaf("Steady", [500] * 12))

    assert flag_trends(tree, "ROOT", "actual") == []


def test_drivers_are_collected_from_driver_formula_children():
    tree = _tree(LEAFWITHDRIVER=_leaf("Leaf With Driver", [100] * 5 + [200] * 7))
    tree["LEAFWITHDRIVER"]["childIds"] = ["FORMULA1"]
    tree["FORMULA1"] = {
        "name": "Formula",
        "nodeType": "Driver Formula",
        "expression": "DRIVER1",
        "childIds": ["DRIVER1"],
        "parentId": "LEAFWITHDRIVER",
    }
    tree["DRIVER1"] = {
        "name": "Headcount",
        "nodeType": "Driver",
        "unit": "count",
        "monthlyActual": [10] * 5 + [20] * 7,
        "monthlyBudget": [10] * 12,
        "childIds": [],
        "parentId": "FORMULA1",
    }

    flags = flag_trends(tree, "ROOT", "actual")

    assert len(flags) == 1
    drivers = flags[0]["drivers"]
    assert len(drivers) == 1
    assert drivers[0]["name"] == "Headcount"
    assert drivers[0]["unit"] == "count"
    assert drivers[0]["series"] == [10] * 5 + [20] * 7
