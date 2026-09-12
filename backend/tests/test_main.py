"""Thin TestClient smoke tests for the two new VDT endpoints — status codes
and top-level response shape, not exhaustive value assertions (those live in
test_vdt_tree.py against the tree-walk directly).
"""

from fastapi.testclient import TestClient  # noqa: E402

import backend.api.routes as main
from backend.app import app
from backend.infrastructure.db import get_session

from conftest import fixture_graph  # noqa: E402


def _client(session) -> TestClient:
    app.dependency_overrides[get_session] = lambda: session
    return TestClient(app)


def test_vdt_tree_endpoint_shape(session):
    codes = fixture_graph(session)
    client = _client(session)

    resp = client.get("/api/vdt/tree", params={"scope": codes["company"], "year": codes["year"]})
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

    resp = client.get(
        "/api/vdt/reconciliation", params={"scope": codes["company"], "node": codes["act_top"], "year": codes["year"]}
    )
    assert resp.status_code == 200
    body = resp.json()
    assert set(body.keys()) >= {"accounting", "vdt", "node", "scope"}
    # node anchors in the VDT tree — act_top is VDT-only, no same-code
    # Accounting node exists for it at all (see docs/adr/0037).
    assert codes["act_top"] in body["vdt"]["nodes"]
    assert codes["act_sub"] in body["vdt"]["nodes"]
    assert codes["gl_old_leaf"] not in body["vdt"]["nodes"]
    # accounting.nodes is a minimal FA-GL-anchor lookup, not a same-code
    # subtree — both va_driven/va_undriven point at gl_anchor_leaf, so it's
    # the only Accounting node returned; the old GL subtree is absent.
    assert set(body["accounting"]["nodes"].keys()) == {codes["gl_anchor_leaf"]}
    assert codes["gl_old_leaf"] not in body["accounting"]["nodes"]
    # No delta/polarity fields — this isn't a diff, see docs/adr/0033.
    assert "delta" not in body["accounting"]["nodes"][codes["gl_anchor_leaf"]]


def test_vdt_reconciliation_ytd_scopes_both_trees(session):
    codes = fixture_graph(session)
    client = _client(session)

    plain = client.get(
        "/api/vdt/reconciliation",
        params={"scope": codes["company"], "node": codes["act_top"], "year": codes["year"], "quarter": 2},
    ).json()
    ytd = client.get(
        "/api/vdt/reconciliation",
        params={"scope": codes["company"], "node": codes["act_top"], "year": codes["year"], "quarter": 2, "ytd": "true"},
    ).json()
    assert ytd["ytd"] is True
    # gl_anchor_leaf's fact is a uniform 30.0/month — Q2 alone sums 3 months,
    # YTD through Q2 sums 6 (see docs/adr/0037, periods.py's Quarter YTD fix).
    plain_gl = plain["accounting"]["nodes"][codes["gl_anchor_leaf"]]["actual"]
    ytd_gl = ytd["accounting"]["nodes"][codes["gl_anchor_leaf"]]["actual"]
    assert ytd_gl == plain_gl * 2
    # Same cumulative widening on the VDT side (va_driven's Driver Formula
    # output), not just the Accounting anchor.
    plain_vdt = plain["vdt"]["nodes"][codes["va_driven"]]["actual"]
    ytd_vdt = ytd["vdt"]["nodes"][codes["va_driven"]]["actual"]
    assert ytd_vdt == plain_vdt * 2


def test_vdt_comparison_accepts_quarter_and_year_pairs(session):
    codes = fixture_graph(session)
    client = _client(session)

    for params_a, params_b in (
        ({"yearA": codes["year"], "quarterA": 1}, {"yearB": codes["year"], "quarterB": 2}),
        ({"yearA": codes["year"]}, {"yearB": codes["year"]}),
    ):
        resp = client.get(
            "/api/vdt/comparison",
            params={
                "scope": codes["company"],
                "node": codes["act_top"],
                **params_a,
                **params_b,
            },
        )

        assert resp.status_code == 200
        body = resp.json()
        assert body["yearA"] == params_a["yearA"]
        assert body["yearB"] == params_b["yearB"]
        assert body.get("quarterA") == params_a.get("quarterA")
        assert body.get("quarterB") == params_b.get("quarterB")


def test_vdt_reconciliation_rejects_leaf_node(session):
    codes = fixture_graph(session)
    client = _client(session)

    resp = client.get(
        "/api/vdt/reconciliation", params={"scope": codes["company"], "node": codes["gl_leaf_rev"], "year": codes["year"]}
    )
    assert resp.status_code == 400


def test_vdt_reconciliation_rejects_unknown_node(session):
    codes = fixture_graph(session)
    client = _client(session)

    resp = client.get("/api/vdt/reconciliation", params={"scope": codes["company"], "node": "NOT-REAL", "year": codes["year"]})
    assert resp.status_code == 404


def test_vdt_tree_rejects_unknown_scope(session):
    fixture_graph(session)
    client = _client(session)

    resp = client.get("/api/vdt/tree", params={"scope": "NOT-REAL"})
    assert resp.status_code == 404


def test_vdt_tree_endpoint_trailing_end(session):
    # fixture_graph only seeds one fiscal year (2024), so an anchor mid-year
    # necessarily produces a partial window — no 2023 exists to reach back
    # into. That's the deliberate docs/adr/0042 behavior, not a limitation
    # of this test.
    codes = fixture_graph(session)
    client = _client(session)

    resp = client.get(
        "/api/vdt/tree",
        params={"scope": codes["company"], "trailingEndYear": codes["year"], "trailingEndPeriod": 6},
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["months"] == [{"year": codes["year"], "period": i} for i in range(1, 7)]
    assert body["year"] is None
    assert codes["gl_leaf_rev"] in body["nodes"]
    assert body["nodes"][codes["gl_leaf_rev"]]["actual"] == 600.0  # 100/month * 6 months, not 12


def test_vdt_tree_endpoint_trailing_end_rejects_unknown_fiscal_year(session):
    codes = fixture_graph(session)
    client = _client(session)

    resp = client.get(
        "/api/vdt/tree",
        params={"scope": codes["company"], "trailingEndYear": 1900, "trailingEndPeriod": 6},
    )
    assert resp.status_code == 404


def test_vdt_tree_endpoint_trailing_end_requires_period_with_year(session):
    codes = fixture_graph(session)
    client = _client(session)

    resp = client.get("/api/vdt/tree", params={"scope": codes["company"], "trailingEndYear": codes["year"]})
    assert resp.status_code == 400


def test_trend_analysis_endpoint_requires_exactly_one_of_year_or_trailing_end(session):
    codes = fixture_graph(session)
    client = _client(session)

    resp = client.post("/api/vdt/trend-analysis", params={"scope": codes["company"]})
    assert resp.status_code == 400

    resp = client.post(
        "/api/vdt/trend-analysis",
        params={
            "scope": codes["company"],
            "year": codes["year"],
            "trailingEndYear": codes["year"],
            "trailingEndPeriod": 6,
        },
    )
    assert resp.status_code == 400


def test_trend_analysis_endpoint_trailing_end_quiet_window(session, monkeypatch):
    # fixture_graph's facts are uniform month-to-month, so no MoM movement is
    # ever flagged — the endpoint returns the deterministic "quiet window"
    # result without ever calling OpenAI, so this needs no API key. The fixed
    # pilot anchor (V201000000) isn't part of this fixture's graph, so it's
    # monkeypatched to a code the fixture does seed — anchor-selection itself
    # is unrelated to what this test covers.
    codes = fixture_graph(session)
    monkeypatch.setattr(main, "VDT_TRENDS_ANCHOR", codes["act_top"])
    client = _client(session)

    resp = client.post(
        "/api/vdt/trend-analysis",
        params={"scope": codes["company"], "trailingEndYear": codes["year"], "trailingEndPeriod": 6},
    )
    assert resp.status_code == 200
    body = resp.json()["trendAnalysis"]
    assert body["bullets"] == []
    assert "trailing 6 months" in body["headline"]


def test_gl_master_tree_endpoint_shape(session):
    codes = fixture_graph(session)
    client = _client(session)

    resp = client.get("/api/gl")
    assert resp.status_code == 200
    body = resp.json()
    assert codes["root"] in body
    assert body[codes["root"]]["nodeType"] == "Reporting Root"
    assert "actual" not in body[codes["root"]]
    assert body[codes["gl_leaf_rev"]]["normalBalance"] == "C"


def test_company_hierarchy_endpoint_shape(session):
    codes = fixture_graph(session)
    client = _client(session)

    resp = client.get("/api/company-hierarchy", params={"kind": "BU"})
    assert resp.status_code == 200
    body = resp.json()
    assert body[codes["group"]]["parentId"] is None
    assert body[codes["business_unit"]]["parentId"] == codes["group"]
    assert body[codes["company"]]["childIds"] == []
    assert body[codes["company"]]["isCompany"] is True
    assert body[codes["business_unit"]]["isCompany"] is False


def test_monetary_endpoints_reject_group_and_business_unit_scopes(session):
    codes = fixture_graph(session)
    client = _client(session)

    for scope in (codes["group"], codes["business_unit"]):
        resp = client.get("/api/financial/tree", params={"scope": scope, "year": codes["year"]})
        assert resp.status_code == 422
        assert resp.json()["detail"] == f"Company scope required: {scope}"
