"""LLM-generated narrative for the variance diagnostic — see docs/adr/0034 and 0041.

Backend-mediated: the OpenAI key never reaches the browser, and the prompt is
built entirely from numbers the backend already computed (a comparison
subtree from vdt_tree.build_vdt_tree()/gl_tree.diff_subtree()) — the model is
asked to narrate given facts, never to compute its own deltas.
"""

import os
import json
from typing import Any, Optional

_cache: dict[tuple, dict[str, Any]] = {}

VDT_ACCOUNT = "VDT Account"
MATERIALITY_THRESHOLD = 0.10
MAX_CONTRIBUTORS = 4
_DRIVER_DISPLAY_PLACES: dict[str, int] = {
    "count": 0,
    "days": 0,
    "currency-per-day": 2,
    "currency-per-month": 2,
    "percent": 4,
    "ratio": 4,
}


class VarianceAnalysisUnavailable(Exception):
    pass


def _movement_label(value_a: float, value_b: float) -> str:
    """Whether a node's real-world magnitude grew or shrank between A and B.

    Ledger sign follows normal_balance (see docs/adr/0023): a cost account's
    value is stored negative, so a *more negative* delta means the cost went
    UP, not down. Comparing magnitudes (abs) sidesteps that entirely — it's
    the only direction signal safe to hand the LLM without it misreading the
    raw delta's sign as plain-English "increase"/"decrease".
    """
    if abs(value_b) > abs(value_a):
        return "increased"
    if abs(value_b) < abs(value_a):
        return "decreased"
    return "unchanged"


def _select_contributors(nodes: dict[str, dict]) -> list[dict]:
    """Select the financial items the LLM is allowed to explain.

    The selection deliberately happens before prompting: operational movements
    tell us *why* a VDT Account changed, while that account's
    financial delta tells us whether it deserves attention at all.
    """
    leaves = [node for node in nodes.values() if node.get("nodeType") == VDT_ACCOUNT]
    gross_movement = sum(abs(node["delta"]) for node in leaves)
    if not gross_movement:
        return []

    materiality_floor = gross_movement * MATERIALITY_THRESHOLD
    selected = [node for node in leaves if abs(node["delta"]) >= materiality_floor]
    return sorted(selected, key=lambda node: abs(node["delta"]), reverse=True)[:MAX_CONTRIBUTORS]


def _format_driver_value(value: float, unit: str, currency: Optional[str]) -> str:
    places = _DRIVER_DISPLAY_PLACES.get(unit, 3)
    if places == 0:
        return f"{int(round(value)):,}"
    formatted = f"{value:,.{places}f}"
    return f"{currency} {formatted}" if unit.startswith("currency-") and currency else formatted


def _driver_unit_label(unit: str, currency: Optional[str]) -> str:
    if unit == "currency-per-day":
        return f"{currency}/day" if currency else unit
    if unit == "currency-per-month":
        return f"{currency}/month" if currency else unit
    return unit


def _render_contributor(nodes: dict[str, dict], contributor: dict, lines: list[str], currency: Optional[str]) -> None:
    """Render one selected financial leaf and its operational evidence.

    Evidence status is computed here rather than inferred by the LLM so that
    a missing or static formula can never turn into an invented cause.
    """
    code = contributor["id"]
    lines.append(
        f"- [{code}] {contributor['name']} ({VDT_ACCOUNT}, money): "
        f"A={contributor['valueA']}, B={contributor['valueB']}, delta={contributor['delta']:+}"
        + (f" ({contributor['deltaPct']:+}%)" if contributor.get("deltaPct") is not None else "")
        + f", magnitude {_movement_label(contributor['valueA'], contributor['valueB'])}"
    )

    formulas = [
        nodes[formula_id]
        for formula_id in contributor.get("childIds", [])
        if nodes.get(formula_id, {}).get("nodeType") == "Driver Formula"
    ]
    terms: list[dict] = []
    for formula in formulas:
        lines.append(f"  Driver Formula: {formula.get('expression') or formula['name']}")
        for driver_id in formula.get("childIds", []):
            driver = nodes.get(driver_id)
            if not driver or driver.get("nodeType") != "Driver":
                continue
            unit = driver["unit"]
            value_a = _format_driver_value(driver["valueA"], unit, currency)
            value_b = _format_driver_value(driver["valueB"], unit, currency)
            changed = value_a != value_b
            terms.append(driver)
            lines.append(
                f"    - {driver['name']} ({_driver_unit_label(unit, currency)}): {value_a} -> {value_b} "
                f"({'changed' if changed else 'unchanged'})"
            )

    if not terms:
        lines.append("  Operational evidence: unavailable (no Driver Formula terms are modelled).")
    elif not any(
        _format_driver_value(term["valueA"], term["unit"], currency)
        != _format_driver_value(term["valueB"], term["unit"], currency)
        for term in terms
    ):
        lines.append("  Operational evidence: inconclusive (no Driver Formula term changed at displayed precision).")


def build_variance_analysis_prompt(
    root: str, nodes: dict[str, dict], period_a: str, period_b: str, currency: Optional[str] = None
) -> str:
    lines: list[str] = []
    root_name = nodes.get(root, {}).get("name", root)
    selected = _select_contributors(nodes)
    root_node = nodes.get(root, {})
    root_direction = _movement_label(root_node["valueA"], root_node["valueB"])
    root_pct = root_node.get("deltaPct")
    selected_directions = {
        _movement_label(node["valueA"], node["valueB"])
        for node in selected
    }
    offsets = "increased" in selected_directions and "decreased" in selected_directions
    for contributor in selected:
        _render_contributor(nodes, contributor, lines, currency)
    contributor_text = "\n".join(lines)
    return (
        "You are a financial analyst writing a short analytical-review variance "
        f"analysis explaining the movement in {root_name} between period {period_a} (A) and "
        f"period {period_b} (B).\n\n"
        "Use ONLY the facts given below — never invent, recompute, or restate a figure "
        "differently than given. The backend has already selected the material financial "
        "contributors by delta; do not add, omit, merge, or replace them. Explain each "
        "selected financial outcome through its Driver Formula terms, whose native-unit "
        "Period A -> Period B values are shown below. The root financial outcome is "
        f"'{root_name}' magnitude {root_direction}"
        + (f" by {abs(root_pct)}%" if root_pct is not None else "")
        + ".\n\n"
        "Return JSON only, with this exact shape: "
        '{"headline":"...","bullets":[{"nodeId":"...","text":"..."}]}. '
        f"Write one short headline summarising {root_name}'s financial movement, then exactly "
        f"{len(selected)} bullets: one for every selected contributor below. Each line starts "
        "with a nodeId in square brackets; every bullet's nodeId must exactly copy one of "
        "those ids, without brackets or the name. "
        + (
            "The selected contributors moved in opposing directions, so the headline must say that "
            "they offset each other. "
            if offsets
            else ""
        )
        + "For a contributor with changed Driver Formula terms, cite every changed term and its "
        "exact native-unit A -> B values; you may also cite an unchanged quantity or rate when "
        "that contrast isolates the cause. Use 'because' or 'driven by' only for these formula "
        "terms. If its operational evidence is marked unavailable, say operational decomposition "
        "is unavailable. If marked inconclusive, say operational evidence is inconclusive and do "
        "not assert a cause. Do not put financial-contributor amounts in headline or bullet "
        "text: the application renders those raw values separately so its display scale can "
        "change without regenerating this analysis. Driver-term values are the exception: "
        "cite them exactly as supplied, including an ISO currency code and per-day/month unit "
        "where shown. Percentages (deltaPct) ARE scale-"
        "independent, so you may and should reference them — but always state deltaPct "
        "as an unsigned number paired with the magnitude word (e.g. 'increased 12%'), "
        "never with its raw +/- sign, since that sign follows accounting convention "
        "rather than plain-English direction. Only "
        "use an intensifier like 'primarily', 'mainly', 'largest', or 'significantly' "
        "when the percentage or ranking that justifies it appears in the same sentence — "
        "never assert emphasis without the figure behind it. "
        "IMPORTANT: each line ends with a 'magnitude' label (increased/decreased/"
        "unchanged) — always use THAT word for direction, never infer direction from "
        "the sign of delta or deltaPct yourself. Accounting sign conventions mean a "
        "cost/expense account can show a NEGATIVE delta while its magnitude increased "
        "(cost went up); the magnitude label already accounts for this and is always "
        "correct as given.\n\n"
        f"Selected contributors (A = {period_a}, B = {period_b}):\n{contributor_text}"
    )


def _parse_variance_analysis(text: str, root: str, nodes: dict[str, dict]) -> dict[str, Any]:
    cleaned = text.strip()
    if cleaned.startswith("```"):
        cleaned = cleaned.removeprefix("```json").removeprefix("```").removesuffix("```").strip()
    try:
        generated = json.loads(cleaned)
    except json.JSONDecodeError as exc:
        raise VarianceAnalysisUnavailable("OpenAI returned invalid variance analysis JSON") from exc

    headline = generated.get("headline") if isinstance(generated, dict) else None
    bullets = generated.get("bullets") if isinstance(generated, dict) else None
    if not isinstance(headline, str) or not headline.strip() or not isinstance(bullets, list):
        raise VarianceAnalysisUnavailable("OpenAI returned an invalid variance analysis structure")

    root_node = nodes.get(root)
    if root_node is None:
        raise VarianceAnalysisUnavailable("Variance analysis root is missing from the comparison")
    root_delta = root_node["delta"]
    selected = _select_contributors(nodes)
    selected_by_id = {node["id"]: node for node in selected}
    if len(bullets) != len(selected):
        raise VarianceAnalysisUnavailable("OpenAI did not return exactly one bullet per selected financial contributor")

    structured_bullets: list[dict[str, Any]] = []
    seen: set[str] = set()
    for bullet in bullets:
        if not isinstance(bullet, dict):
            continue
        node_id = bullet.get("nodeId")
        # Defensive: the model is asked to copy an id shown in "[id]" form and
        # occasionally echoes the brackets back too — strip them rather than
        # silently dropping an otherwise-valid bullet over a formatting slip.
        if isinstance(node_id, str):
            node_id = node_id.strip().removeprefix("[").removesuffix("]").strip()
        bullet_text = bullet.get("text")
        node = selected_by_id.get(node_id) if isinstance(node_id, str) else None
        if node is None or node_id in seen or node.get("unit") != "money" or not isinstance(bullet_text, str) or not bullet_text.strip():
            raise VarianceAnalysisUnavailable("OpenAI returned an invalid selected financial contributor")
        seen.add(node_id)
        structured_bullets.append(
            {
                "nodeId": node_id,
                "nodeName": node["name"],
                "text": bullet_text.strip(),
                "amount": node["delta"],
                "deltaPct": node.get("deltaPct"),
                # Share of the overall root movement this contributor accounts
                # for — computed here (not by the LLM) so it's always exact.
                "contributionPct": round(node["delta"] / root_delta * 100, 1) if root_delta else None,
            }
        )

    if {bullet["nodeId"] for bullet in structured_bullets} != set(selected_by_id):
        raise VarianceAnalysisUnavailable("OpenAI did not cover every selected financial contributor")

    structured_by_id = {bullet["nodeId"]: bullet for bullet in structured_bullets}

    return {
        "headline": headline.strip(),
        "netAmount": root_delta,
        "bullets": [structured_by_id[node["id"]] for node in selected],
    }


def generate_variance_analysis(
    cache_key: tuple,
    root: str,
    nodes: dict[str, dict],
    period_a: str,
    period_b: str,
    currency: Optional[str] = None,
) -> dict[str, Any]:
    if cache_key in _cache:
        return _cache[cache_key]

    selected = _select_contributors(nodes)
    if not selected:
        result = {
            "headline": (
                "Movement was distributed across smaller VDT Accounts; "
                "no individual contributor met the materiality threshold."
            ),
            "netAmount": nodes[root]["delta"],
            "bullets": [],
        }
        _cache[cache_key] = result
        return result

    api_key = os.environ.get("OPENAI_API_KEY")
    if not api_key:
        raise VarianceAnalysisUnavailable("OPENAI_API_KEY is not configured")

    try:
        from openai import OpenAI
    except ImportError as exc:
        raise VarianceAnalysisUnavailable("openai package not installed") from exc

    model = os.environ.get("OPENAI_MODEL", "gpt-4o-mini")
    prompt = build_variance_analysis_prompt(root, nodes, period_a, period_b, currency)

    try:
        client = OpenAI(api_key=api_key)
        response = client.chat.completions.create(
            model=model,
            messages=[{"role": "user", "content": prompt}],
            temperature=0.3,
        )
        text: Optional[str] = response.choices[0].message.content
    except Exception as exc:
        raise VarianceAnalysisUnavailable(f"OpenAI request failed: {exc}") from exc

    if not text:
        raise VarianceAnalysisUnavailable("OpenAI returned an empty response")

    variance_analysis = _parse_variance_analysis(text, root, nodes)
    _cache[cache_key] = variance_analysis
    return variance_analysis
