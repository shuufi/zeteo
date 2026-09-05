"""LLM-generated movement narration for VDT Comparison — see docs/adr/0034.

Backend-mediated: the OpenAI key never reaches the browser, and the prompt is
built entirely from numbers the backend already computed (a comparison
subtree from vdt_tree.build_vdt_tree()/gl_tree.diff_subtree()) — the model is
asked to narrate given facts, never to compute its own deltas.
"""

import os
import json
from typing import Any, Optional

_cache: dict[tuple, dict[str, Any]] = {}


class NarrationUnavailable(Exception):
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


def _render_node(nodes: dict[str, dict], code: str, depth: int, lines: list[str]) -> None:
    node = nodes.get(code)
    if node is None:
        return
    indent = "  " * depth
    unit = node["unit"]
    lines.append(
        f"{indent}- [{code}] {node['name']} ({node['nodeType']}, {unit}): "
        f"A={node['valueA']}, B={node['valueB']}, delta={node['delta']:+}"
        + (f" ({node['deltaPct']:+}%)" if node.get("deltaPct") is not None else "")
        + f", magnitude {_movement_label(node['valueA'], node['valueB'])}"
    )
    expression = node.get("expression")
    if expression:
        lines.append(f"{indent}  formula: {expression}")
    for child_id in node.get("childIds", []):
        _render_node(nodes, child_id, depth + 1, lines)


def build_prompt(root: str, nodes: dict[str, dict], period_a: str, period_b: str) -> str:
    lines: list[str] = []
    _render_node(nodes, root, 0, lines)
    tree_text = "\n".join(lines)
    root_name = nodes.get(root, {}).get("name", root)
    return (
        "You are a financial analyst writing a short analytical-review narration "
        f"explaining the movement in {root_name} between period {period_a} (A) and "
        f"period {period_b} (B).\n\n"
        "Use ONLY the numbers and structure given below — never invent, recompute, "
        "or restate a figure differently than given. The hierarchy below shows how "
        "each contributor rolls up, and for contributors whose value is computed by "
        "a formula, the formula's own driver terms with their own A/B/delta — use "
        "those to explain WHY a contributor moved (e.g. a quantity driver moved but "
        "a rate driver didn't), not just THAT it moved.\n\n"
        "Return JSON only, with this exact shape: "
        '{"headline":"...","bullets":[{"nodeId":"...","text":"..."}]}. '
        "Write one short headline summarising the movement, then 2-4 bullets naming "
        "the key contributors and, where a driver breakdown is given, their underlying "
        "cause. Each hierarchy line below starts with a nodeId in square brackets, e.g. "
        '"[V201000000] SOC Crew Cost ...", where the id is V201000000. Every bullet\'s '
        "nodeId must exactly copy one of those ids, WITHOUT the surrounding square "
        "brackets and without the name that follows it. "
        "Do not put currency symbols or monetary amounts in headline or bullet text: "
        "the application renders those raw values separately so its display scale can "
        "change without regenerating this narration. Percentages (deltaPct) ARE scale-"
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
        f"Hierarchy (A = {period_a}, B = {period_b}):\n{tree_text}"
    )


def _parse_narration(text: str, root: str, nodes: dict[str, dict]) -> dict[str, Any]:
    cleaned = text.strip()
    if cleaned.startswith("```"):
        cleaned = cleaned.removeprefix("```json").removeprefix("```").removesuffix("```").strip()
    try:
        generated = json.loads(cleaned)
    except json.JSONDecodeError as exc:
        raise NarrationUnavailable("OpenAI returned invalid narration JSON") from exc

    headline = generated.get("headline") if isinstance(generated, dict) else None
    bullets = generated.get("bullets") if isinstance(generated, dict) else None
    if not isinstance(headline, str) or not headline.strip() or not isinstance(bullets, list):
        raise NarrationUnavailable("OpenAI returned an invalid narration structure")

    root_node = nodes.get(root)
    if root_node is None:
        raise NarrationUnavailable("Narration root is missing from the comparison")
    root_delta = root_node["delta"]

    structured_bullets: list[dict[str, Any]] = []
    seen: set[str] = set()
    for bullet in bullets[:4]:
        if not isinstance(bullet, dict):
            continue
        node_id = bullet.get("nodeId")
        # Defensive: the model is asked to copy an id shown in "[id]" form and
        # occasionally echoes the brackets back too — strip them rather than
        # silently dropping an otherwise-valid bullet over a formatting slip.
        if isinstance(node_id, str):
            node_id = node_id.strip().removeprefix("[").removesuffix("]").strip()
        bullet_text = bullet.get("text")
        node = nodes.get(node_id) if isinstance(node_id, str) else None
        if (
            node is None
            or node_id in seen
            or node.get("unit") != "money"
            or not isinstance(bullet_text, str)
            or not bullet_text.strip()
        ):
            continue
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

    if not structured_bullets:
        raise NarrationUnavailable("OpenAI did not reference a valid monetary contributor")

    return {
        "headline": headline.strip(),
        "netAmount": root_delta,
        "bullets": structured_bullets,
    }


def generate_narration(
    cache_key: tuple,
    root: str,
    nodes: dict[str, dict],
    period_a: str,
    period_b: str,
) -> dict[str, Any]:
    if cache_key in _cache:
        return _cache[cache_key]

    api_key = os.environ.get("OPENAI_API_KEY")
    if not api_key:
        raise NarrationUnavailable("OPENAI_API_KEY is not configured")

    try:
        from openai import OpenAI
    except ImportError as exc:
        raise NarrationUnavailable("openai package not installed") from exc

    model = os.environ.get("OPENAI_MODEL", "gpt-4o-mini")
    prompt = build_prompt(root, nodes, period_a, period_b)

    try:
        client = OpenAI(api_key=api_key)
        response = client.chat.completions.create(
            model=model,
            messages=[{"role": "user", "content": prompt}],
            temperature=0.3,
        )
        text: Optional[str] = response.choices[0].message.content
    except Exception as exc:
        raise NarrationUnavailable(f"OpenAI request failed: {exc}") from exc

    if not text:
        raise NarrationUnavailable("OpenAI returned an empty response")

    narration = _parse_narration(text, root, nodes)
    _cache[cache_key] = narration
    return narration
