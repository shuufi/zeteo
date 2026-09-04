"""Movement narration keeps prose separate from raw monetary references."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from narration import _parse_narration, build_prompt  # noqa: E402


NODES = {
    "ROOT": {
        "name": "Crew Cost",
        "nodeType": "Reporting Node",
        "unit": "money",
        "valueA": -1_000_000.00,
        "valueB": -1_250_000.00,
        "delta": -250_000.00,
        "deltaPct": 25.0,
        "childIds": ["CHILD"],
    },
    "CHILD": {
        "name": "Officer Cost",
        "nodeType": "Activity Node",
        "unit": "money",
        "valueA": -400_000.00,
        "valueB": -550_000.00,
        "delta": -150_000.00,
        "deltaPct": 37.5,
        "childIds": [],
    },
}


def test_narration_parser_attaches_authoritative_raw_deltas():
    result = _parse_narration(
        '{"headline":"Crew cost increased.","bullets":[{"nodeId":"CHILD","text":"Officer cost was the main contributor."}]}',
        "ROOT",
        NODES,
    )

    assert result["netAmount"] == -250_000.00
    assert result["bullets"][0]["amount"] == -150_000.00
    assert result["bullets"][0]["nodeName"] == "Officer Cost"


def test_narration_prompt_uses_generic_money_unit_and_requests_no_formatted_amounts():
    prompt = build_prompt("ROOT", NODES, "FY26-M01", "FY26-M02")

    assert "Reporting Node, money" in prompt
    assert "RM_M" not in prompt
    assert "Do not put currency symbols" in prompt
