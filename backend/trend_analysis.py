"""LLM-generated Trend Analysis narrative for VDT Trends — see docs/adr/0040.

Distinct from variance_analysis.py: a monthly-series walk over server-flagged
leaves, not a two-point diff over a full subtree. Detection is trend_flagging's
job; this module only turns flagged facts into prose. Backend-mediated the same
way variance_analysis.py is — the OpenAI key never reaches the browser, and every
number in the prompt was already computed server-side; the model narrates
given facts, it never computes its own arithmetic.
"""

import os
import json
from typing import Any, Optional

from trend_flagging import flag_trends

_cache: dict[tuple, dict[str, Any]] = {}

MONTHS = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]
MAX_BULLETS = 6


class TrendAnalysisUnavailable(Exception):
    pass


def _render_flagged(flagged: list[dict]) -> str:
    lines: list[str] = []
    for node in flagged:
        lines.append(
            f"- [{node['nodeId']}] {node['nodeName']} ({node['nodeType']}), "
            f"parent: {node.get('parentName') or 'n/a'}, "
            f"12-month series ({', '.join(MONTHS)}): {node['series']}"
        )
        for month in node["flaggedMonths"]:
            m = month["monthIndex"]
            pct_text = f"{month['momPct']}%" if month["momPct"] is not None else "from ~0"
            lines.append(
                f"    {MONTHS[m - 1]} -> {MONTHS[m]}: {month['prevValue']} -> {month['currValue']}, "
                f"MoM change {pct_text}, magnitude {month['direction']}, "
                f"{month['sharePct']}% of {node['rootName']}'s total that month"
            )
        if node["drivers"]:
            lines.append("    Driver Formula terms (own units, explain WHY this moved):")
            for driver in node["drivers"]:
                lines.append(
                    f"      - {driver['name']} ({driver['unit']}): {driver['series']}"
                    + (f", formula: {driver['expression']}" if driver.get("expression") else "")
                )
    return "\n".join(lines)


def build_trend_prompt(root_name: str, year_label: str, scenario: str, flagged: list[dict]) -> str:
    flagged_text = _render_flagged(flagged)
    return (
        "You are a financial analyst writing a short analytical-review narrative "
        f"identifying the notable month-over-month (MoM) trends in {root_name} across "
        f"fiscal year {year_label} ({scenario} scenario).\n\n"
        "Use ONLY the numbers and structure given below — never invent, recompute, or "
        "restate a figure differently than given. The backend has already flagged which "
        "nodes and months are material; your job is only to explain WHY each flagged "
        "movement happened, not to decide what's material. Each flagged node lists its "
        "full 12-month series for context, then the specific month(s) that were flagged, "
        "then — where available — its Driver Formula terms' own 12-month series (e.g. "
        "crew headcount, travel/crew-movement counts, salary or accommodation rates). "
        "Always explain a flagged movement via its driver terms (quantity vs rate) when "
        "given, not just the dollar figure — that operational cause is the point of this "
        "narrative, not the financial outcome number.\n\n"
        "Return JSON only, with this exact shape: "
        '{"headline":"...","bullets":[{"nodeId":"...","text":"..."}]}. '
        f"Write one short headline summarising the year's notable trends, then up to "
        f"{MAX_BULLETS} bullets — one per flagged node you choose to cover, fewer if "
        "fewer nodes were flagged. Do not manufacture a bullet for a node that wasn't "
        "flagged, and do not pad bullets to reach the cap. Each flagged node line below "
        "starts with a nodeId in square brackets, e.g. \"[V201000000] SOC Crew Cost ...\", "
        "where the id is V201000000. Every bullet's nodeId must exactly copy one of those "
        "ids, WITHOUT the surrounding square brackets and without the name that follows it.\n\n"
        "Do not put currency symbols or monetary amounts in headline or bullet text: the "
        "application renders those raw values separately so its display scale can change "
        "without regenerating this narrative. Percentages (MoM change, % of total) ARE "
        "scale-independent, so you may and should reference them — but always state a "
        "percentage as an unsigned number paired with the magnitude word given (e.g. "
        "'increased 23%'), never with a raw sign, since accounting sign conventions don't "
        "match plain-English direction. IMPORTANT: each flagged month already states a "
        "'magnitude' label (increased/decreased) — always use THAT word for direction, "
        "never infer direction from a raw value's sign yourself; a cost account can show "
        "a more-negative value while its magnitude increased (cost went up). Only use an "
        "intensifier like 'primarily', 'mainly', 'largest', or 'significantly' when the "
        "percentage or ranking that justifies it appears in the same sentence.\n\n"
        f"Flagged nodes:\n{flagged_text}"
    )


def _parse_trend(text: str, flagged_by_id: dict[str, dict]) -> dict[str, Any]:
    cleaned = text.strip()
    if cleaned.startswith("```"):
        cleaned = cleaned.removeprefix("```json").removeprefix("```").removesuffix("```").strip()
    try:
        generated = json.loads(cleaned)
    except json.JSONDecodeError as exc:
        raise TrendAnalysisUnavailable("OpenAI returned invalid trend analysis JSON") from exc

    headline = generated.get("headline") if isinstance(generated, dict) else None
    bullets = generated.get("bullets") if isinstance(generated, dict) else None
    if not isinstance(headline, str) or not headline.strip() or not isinstance(bullets, list):
        raise TrendAnalysisUnavailable("OpenAI returned an invalid trend analysis structure")

    structured_bullets: list[dict[str, Any]] = []
    seen: set[str] = set()
    for bullet in bullets[:MAX_BULLETS]:
        if not isinstance(bullet, dict):
            continue
        node_id = bullet.get("nodeId")
        if isinstance(node_id, str):
            node_id = node_id.strip().removeprefix("[").removesuffix("]").strip()
        bullet_text = bullet.get("text")
        flagged = flagged_by_id.get(node_id) if isinstance(node_id, str) else None
        if (
            flagged is None
            or node_id in seen
            or not isinstance(bullet_text, str)
            or not bullet_text.strip()
        ):
            continue
        seen.add(node_id)
        structured_bullets.append(
            {
                "nodeId": node_id,
                "nodeName": flagged["nodeName"],
                "nodeType": flagged["nodeType"],
                "text": bullet_text.strip(),
                "series": flagged["series"],
                "rootSeries": flagged["rootSeries"],
                "flaggedMonths": flagged["flaggedMonths"],
                "peakMonthIndex": flagged["peakMonthIndex"],
                "amount": flagged["amount"],
                "drivers": flagged["drivers"],
            }
        )

    if not structured_bullets:
        raise TrendAnalysisUnavailable("OpenAI did not reference a valid flagged node")

    return {
        "headline": headline.strip(),
        "bullets": structured_bullets,
    }


def generate_trend_analysis(
    cache_key: tuple,
    tree: dict[str, dict],
    root: str,
    scenario: str,
    year_label: str,
) -> dict[str, Any]:
    if cache_key in _cache:
        return _cache[cache_key]

    flagged = flag_trends(tree, root, scenario)
    root_node = tree[root]
    root_name = root_node["name"]

    if not flagged:
        result = {
            "headline": f"No material month-over-month movements in {root_name} for {year_label}.",
            "scenario": scenario,
            "bullets": [],
        }
        _cache[cache_key] = result
        return result

    api_key = os.environ.get("OPENAI_API_KEY")
    if not api_key:
        raise TrendAnalysisUnavailable("OPENAI_API_KEY is not configured")

    try:
        from openai import OpenAI
    except ImportError as exc:
        raise TrendAnalysisUnavailable("openai package not installed") from exc

    model = os.environ.get("OPENAI_MODEL", "gpt-4o-mini")
    prompt = build_trend_prompt(root_name, year_label, scenario, flagged)

    try:
        client = OpenAI(api_key=api_key)
        response = client.chat.completions.create(
            model=model,
            messages=[{"role": "user", "content": prompt}],
            temperature=0.3,
        )
        text: Optional[str] = response.choices[0].message.content
    except Exception as exc:
        raise TrendAnalysisUnavailable(f"OpenAI request failed: {exc}") from exc

    if not text:
        raise TrendAnalysisUnavailable("OpenAI returned an empty response")

    result = _parse_trend(text, {f["nodeId"]: f for f in flagged})
    result["scenario"] = scenario
    _cache[cache_key] = result
    return result
