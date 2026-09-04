"""LLM-generated movement narration for VDT Statement comparisons — see docs/adr/0034.

Backend-mediated: the OpenAI key never reaches the browser, and the prompt is
built entirely from numbers the backend already computed (a comparison
subtree from vdt_tree.build_vdt_tree()/gl_tree.diff_subtree()) — the model is
asked to narrate given facts, never to compute its own deltas.
"""

import os
from typing import Optional

_cache: dict[tuple, str] = {}


class NarrationUnavailable(Exception):
    pass


def _render_node(nodes: dict[str, dict], code: str, depth: int, lines: list[str]) -> None:
    node = nodes.get(code)
    if node is None:
        return
    indent = "  " * depth
    unit = "RM_M" if node["unit"] == "RM_M" else node["unit"]
    lines.append(
        f"{indent}- {node['name']} ({node['nodeType']}, {unit}): "
        f"A={node['valueA']}, B={node['valueB']}, delta={node['delta']:+}"
        + (f" ({node['deltaPct']:+}%)" if node.get("deltaPct") is not None else "")
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
        "Write one headline sentence summarising the net movement, then 2-4 bullet "
        "points naming the key contributors and, where a driver breakdown is given, "
        "their underlying cause.\n\n"
        f"Hierarchy (A = {period_a}, B = {period_b}):\n{tree_text}"
    )


def generate_narration(cache_key: tuple, root: str, nodes: dict[str, dict], period_a: str, period_b: str) -> str:
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

    text = text.strip()
    _cache[cache_key] = text
    return text
