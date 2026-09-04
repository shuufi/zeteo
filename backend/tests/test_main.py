"""Thin TestClient smoke tests for the two new VDT endpoints — status codes
and top-level response shape, not exhaustive value assertions (those live in
test_vdt_tree.py against the tree-walk directly).
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from fastapi.testclient import TestClient  # noqa: E402

from db import get_session  # noqa: E402
from main import app  # noqa: E402

from conftest import fixture_graph  # noqa: E402


def _client(session) -> TestClient:
    app.dependency_overrides[get_session] = lambda: session
    return TestClient(app)


def test_vdt_tree_endpoint_shape(session):
    codes = fixture_graph(session)
    client = _client(session)

    resp = client.get("/api/vdt/tree", params={"scope": codes["company"], "period": codes["year"]})
    assert resp.status_code == 200
    body = resp.json()
    assert body["scope"] == codes["company"]
    assert body["scopeKind"] == "company"
    assert body["currency"] == "MYR"
    assert body["notYetModelled"] is False
    assert codes["cor"] in body["nodes"]
    assert body["nodes"][codes["cor"]]["childIds"] == [codes["act_top"]]
    assert body["nodes"][codes["cor"]]["unit"] == "money"


def test_vdt_reconciliation_endpoint_shape(session):
    codes = fixture_graph(session)
    client = _client(session)

    resp = client.get("/api/vdt/reconciliation", params={"scope": codes["company"], "node": codes["cor"], "period": codes["year"]})
    assert resp.status_code == 200
    body = resp.json()
    assert set(body.keys()) >= {"accounting", "vdt", "node", "scope"}
    # Accounting side keeps the old GL subtree; VDT side replaced it wholesale.
    assert codes["gl_old_leaf"] in body["accounting"]["nodes"]
    assert codes["gl_old_leaf"] not in body["vdt"]["nodes"]
    assert codes["act_top"] in body["vdt"]["nodes"]
    # No delta/polarity fields — this isn't a diff, see docs/adr/0033.
    assert "delta" not in body["accounting"]["nodes"][codes["cor"]]


def test_vdt_reconciliation_rejects_leaf_node(session):
    codes = fixture_graph(session)
    client = _client(session)

    resp = client.get("/api/vdt/reconciliation", params={"scope": codes["company"], "node": codes["gl_leaf_rev"], "period": codes["year"]})
    assert resp.status_code == 400


def test_vdt_reconciliation_rejects_unknown_node(session):
    codes = fixture_graph(session)
    client = _client(session)

    resp = client.get("/api/vdt/reconciliation", params={"scope": codes["company"], "node": "NOT-REAL", "period": codes["year"]})
    assert resp.status_code == 404


def test_vdt_tree_rejects_unknown_scope(session):
    fixture_graph(session)
    client = _client(session)

    resp = client.get("/api/vdt/tree", params={"scope": "NOT-REAL"})
    assert resp.status_code == 404


def test_monetary_endpoints_reject_group_and_business_unit_scopes(session):
    codes = fixture_graph(session)
    client = _client(session)

    for scope in (codes["group"], codes["business_unit"]):
        resp = client.get("/api/gl/tree", params={"scope": scope, "period": codes["year"]})
        assert resp.status_code == 422
        assert resp.json()["detail"] == f"Company scope required: {scope}"
