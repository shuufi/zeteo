"""Server-side MoM anomaly flagging for VDT Trend Analysis — see docs/adr/0040.

Detection is deterministic here (the LLM never judges materiality): a leaf is
flagged in a month when its magnitude MoM change > MOM_THRESHOLD AND its own
magnitude that month > ROOT_SHARE_THRESHOLD of the root's total. Ranks flagged
leaves by dollar-impact of the movement (a big % on a trivial line isn't
big-ticket) and caps the payload so the prompt stays bounded.
"""

MOM_THRESHOLD = 0.15          # 15% month-over-month magnitude change
ROOT_SHARE_THRESHOLD = 0.05   # node magnitude must be >5% of root total that month
MAX_FLAGGED_NODES = 12        # payload bound; LLM still caps bullets at 6

LEAF_MONEY_NODE_TYPES = {"Posting GL Account", "Posting Activity Account"}
EPSILON = 1e-9


def _series_for(node: dict, scenario: str) -> list[float]:
    return node["monthlyBudget"] if scenario == "budget" else node["monthlyActual"]


def _movement_label(prev: float, cur: float) -> str:
    if abs(cur) > abs(prev):
        return "increased"
    if abs(cur) < abs(prev):
        return "decreased"
    return "unchanged"


def _descendant_codes(tree: dict[str, dict], root: str) -> set[str]:
    """Every code reachable from `root` via childIds, root included.

    `tree` (a build_vdt_tree() output) spans every Reporting Root's full
    reach, not just `root`'s own branch — flagging must stay inside `root`'s
    subtree (the same anchor the VDT Trends table renders), or an unrelated
    leaf elsewhere in the tree could get flagged and have its "share of
    root" computed against a root total it has nothing to do with.
    """
    seen: set[str] = set()

    def walk(code: str) -> None:
        if code in seen:
            return
        seen.add(code)
        node = tree.get(code)
        if node is None:
            return
        for child_id in node.get("childIds", []):
            walk(child_id)

    walk(root)
    return seen


#: Display precision per Driver unit — the underlying series is a smooth,
#: 3-decimal-quantized curve (see seed_vdt.py's growth model), but a count
#: like headcount is never fractional in the real world; rounding here is
#: purely for what's shown/narrated, not the flagging math (which never reads
#: Driver series, only the leaf's own money series).
_DRIVER_DISPLAY_PLACES: dict[str, int] = {
    "count": 0,
    "days": 0,
    "currency-per-day": 2,
    "currency-per-month": 2,
    "percent": 4,
    "ratio": 4,
}


def _round_driver_series(unit: str, series: list[float]) -> list[float]:
    places = _DRIVER_DISPLAY_PLACES.get(unit, 2)
    if places == 0:
        return [int(round(v)) for v in series]
    return [round(v, places) for v in series]


def _collect_drivers(tree: dict[str, dict], leaf_id: str, scenario: str) -> list[dict]:
    """Walk the leaf's Driver Formula / Driver descendants, returning each
    Driver term's 12-month series in the selected scenario (its own unit, not
    money). Explains WHY the leaf moved — quantity vs rate."""
    out: list[dict] = []
    leaf = tree.get(leaf_id)
    for f_id in (leaf or {}).get("childIds", []):
        formula = tree.get(f_id)
        if not formula or formula.get("nodeType") != "Driver Formula":
            continue
        for d_id in formula.get("childIds", []):
            driver = tree.get(d_id)
            if not driver or driver.get("nodeType") != "Driver":
                continue
            out.append(
                {
                    "name": driver["name"],
                    "unit": driver["unit"],
                    "series": _round_driver_series(driver["unit"], _series_for(driver, scenario)),
                    "expression": formula.get("expression"),
                }
            )
    return out


def flag_trends(tree: dict[str, dict], root: str, scenario: str) -> list[dict]:
    """Returns flagged leaf nodes, ranked by peak dollar-impact, capped at
    MAX_FLAGGED_NODES. Empty list == a quiet year (caller must NOT manufacture
    bullets)."""
    root_node = tree.get(root)
    if root_node is None:
        return []
    root_series = _series_for(root_node, scenario)
    in_scope = _descendant_codes(tree, root)

    flagged: list[dict] = []
    for node_id in in_scope:
        node = tree[node_id]
        if node.get("nodeType") not in LEAF_MONEY_NODE_TYPES:
            continue
        series = _series_for(node, scenario)
        months: list[dict] = []
        for m in range(1, 12):  # Jan (0) has no in-year prior month
            prev, cur = series[m - 1], series[m]
            root_total = abs(root_series[m])
            if root_total < EPSILON or abs(cur) <= ROOT_SHARE_THRESHOLD * root_total:
                continue
            if abs(prev) < EPSILON:
                mom_pct = None
                passes = abs(cur) > EPSILON
            else:
                mom_pct = abs(cur - prev) / abs(prev)
                passes = mom_pct > MOM_THRESHOLD
            if not passes:
                continue
            months.append(
                {
                    "monthIndex": m,
                    "prevValue": prev,
                    "currValue": cur,
                    "momPct": None if mom_pct is None else round(mom_pct * 100, 1),
                    "direction": _movement_label(prev, cur),
                    "sharePct": round(abs(cur) / root_total * 100, 1),
                    "impact": abs(cur - prev),
                }
            )
        if not months:
            continue
        peak = max(months, key=lambda x: x["impact"])
        flagged.append(
            {
                "nodeId": node_id,
                "nodeName": node["name"],
                "nodeType": node["nodeType"],
                "series": series,
                "parentId": node.get("parentId"),
                "parentName": tree.get(node.get("parentId"), {}).get("name"),
                "rootId": root,
                "rootName": root_node["name"],
                "rootSeries": root_series,
                "flaggedMonths": months,
                "peakMonthIndex": peak["monthIndex"],
                "peakImpact": peak["impact"],
                "amount": peak["currValue"] - peak["prevValue"],
                "drivers": _collect_drivers(tree, node_id, scenario),
            }
        )

    flagged.sort(key=lambda f: f["peakImpact"], reverse=True)
    return flagged[:MAX_FLAGGED_NODES]


if __name__ == "__main__":
    # Quick standalone sanity check with a hand-built tree — no pytest needed
    # to validate the core threshold/ranking logic.
    def _leaf(name: str, node_type: str, actual: list[float], parent="ROOT") -> dict:
        return {
            "name": name,
            "nodeType": node_type,
            "monthlyActual": actual,
            "monthlyBudget": [0.0] * 12,
            "childIds": [],
            "parentId": parent,
        }

    root_series = [1000.0] * 12
    tree = {
        "ROOT": {
            "name": "Root",
            "nodeType": "Activity Node",
            "monthlyActual": root_series,
            "monthlyBudget": root_series,
            "childIds": ["BIG", "SMALL", "JANSPIKE", "ZEROSTART"],
            "parentId": None,
        },
        # Big line, crosses both thresholds mid-year.
        "BIG": _leaf("Big Line", "Posting GL Account", [100, 100, 100, 100, 100, 200, 200, 200, 200, 200, 200, 200]),
        # Trivial line — moves 200% but stays under 5% of root, should never flag.
        "SMALL": _leaf("Small Line", "Posting GL Account", [1, 1, 1, 1, 1, 3, 3, 3, 3, 3, 3, 3]),
        # Jan (index 0) has no prior month — must never flag regardless of value.
        "JANSPIKE": _leaf("Jan Spike", "Posting GL Account", [900, 100, 100, 100, 100, 100, 100, 100, 100, 100, 100, 100]),
        # Starts at zero then appears — from-zero case.
        "ZEROSTART": _leaf("Zero Start", "Posting GL Account", [0, 0, 0, 0, 0, 0, 60, 60, 60, 60, 60, 60]),
    }

    flags = flag_trends(tree, "ROOT", "actual")
    flagged_ids = {f["nodeId"] for f in flags}
    assert "BIG" in flagged_ids, "expected BIG to be flagged"
    assert "SMALL" not in flagged_ids, "expected SMALL to stay unflagged (below root-share threshold)"
    assert "ZEROSTART" in flagged_ids, "expected ZEROSTART to be flagged (from-zero case)"
    for f in flags:
        assert all(m["monthIndex"] != 0 for m in f["flaggedMonths"]), "Jan (index 0) must never be flagged"
    assert flags == sorted(flags, key=lambda f: f["peakImpact"], reverse=True), "must rank by peak dollar impact"
    assert len(flags) <= MAX_FLAGGED_NODES
    print("trend_flagging sanity checks passed:", flagged_ids)
