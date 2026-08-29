import json
from pathlib import Path

COMPANIES_PATH = Path(__file__).parent / "data" / "companies.json"


def load_business_units() -> list[dict]:
    return json.loads(COMPANIES_PATH.read_text(encoding="utf-8"))["businessUnits"]


def sample_companies() -> list[dict]:
    """3 companies per BU, or all of them where a BU has 3 or fewer. See docs/adr/0024."""
    sampled = []
    for bu in load_business_units():
        for company in bu["companies"][:3]:
            sampled.append({"code": company["code"], "bu": bu["code"]})
    return sampled
