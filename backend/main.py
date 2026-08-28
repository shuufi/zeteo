import json
from pathlib import Path

from fastapi import FastAPI

app = FastAPI(title="Zeteo API")

COMPANIES_PATH = Path(__file__).parent / "data" / "companies.json"


@app.get("/api/companies")
def get_companies():
    return json.loads(COMPANIES_PATH.read_text(encoding="utf-8"))
