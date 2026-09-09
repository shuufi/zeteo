"""Tests for vdt_sensitivity.py + POST /api/vdt/sensitivity — see docs/adr/0043.

Unit tests exercise the module functions directly against `conftest.fixture_graph`
(mirrors test_vdt_tree.py); endpoint tests use TestClient's SSE-streaming support
(mirrors test_main.py's shape). Elasticity-computing tests use a short 2-month
window for readable fixture data — a driver-direction rerun batches every
month of the window into one call, so window length no longer drives rerun
count; window-length handling itself is covered separately by the
partial-window test.
"""

import asyncio
import sys
from decimal import Decimal
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent))

from fastapi.testclient import TestClient  # noqa: E402
from sqlmodel import select  # noqa: E402

import main  # noqa: E402
from db import get_session  # noqa: E402
from main import app  # noqa: E402
from driver_engine import DriverEngine  # noqa: E402
from models import (  # noqa: E402
    ActivityNode,
    Driver,
    DriverFact,
    DriverFormula,
    DriverFormulaTerm,
    FormulaOperator,
    OperationalUnit,
    PostingActivityAccount,
    Scenario,
)
from periods import load_period_hierarchy, ordered_month_codes_of_year  # noqa: E402
from vdt_sensitivity import (  # noqa: E402
    DriverOverride,
    SENSITIVITY_MAX_CYCLES,
    compute_npat_with_overrides,
    compute_sensitivity,
    terminal_driver_candidates,
)
from vdt_tree import build_vdt_tree  # noqa: E402

from conftest import fixture_graph  # noqa: E402


def _window(session, codes, n=2):
    period_by_code, period_children = load_period_hierarchy(session)
    return ordered_month_codes_of_year(period_by_code, period_children, codes["year"])[:n]


def _client(session) -> TestClient:
    app.dependency_overrides[get_session] = lambda: session
    return TestClient(app)


# --- override primitive -----------------------------------------------------


def test_override_primitive_recomputes_npat_and_never_mutates_driver_fact(session):
    codes = fixture_graph(session)
    window = _window(session, codes, 12)

    before = sorted((r.code, r.period_code, r.scenario, r.amount) for r in session.exec(select(DriverFact)).all())

    result = compute_npat_with_overrides(
        session,
        codes["company"],
        "actual",
        window,
        [DriverOverride(codes["driver_headcount"], [Decimal("99")] * len(window))],
        codes["root"],
    )

    after = sorted((r.code, r.period_code, r.scenario, r.amount) for r in session.exec(select(DriverFact)).all())
    assert before == after  # overrides never leak into the persisted row

    # Overriding headcount to 99 must move NPAT away from the un-overridden baseline.
    baseline = compute_npat_with_overrides(session, codes["company"], "actual", window, [], codes["root"])
    assert sum(result["npat"]) != sum(baseline["npat"])


def test_override_primitive_calls_are_independent(session):
    codes = fixture_graph(session)
    window = _window(session, codes, 2)

    up = compute_npat_with_overrides(
        session, codes["company"], "actual", window,
        [DriverOverride(codes["driver_headcount"], [Decimal("20")] * len(window))], codes["root"],
    )
    down = compute_npat_with_overrides(
        session, codes["company"], "actual", window,
        [DriverOverride(codes["driver_headcount"], [Decimal("1")] * len(window))], codes["root"],
    )

    # A fresh engine (and fresh _cache) every call — the second call's very
    # different override must not be shadowed by anything the first call cached.
    assert sum(up["npat"]) != sum(down["npat"])


def test_override_primitive_defaults_subtree_to_none_unless_requested(session):
    codes = fixture_graph(session)
    window = _window(session, codes, 2)

    result = compute_npat_with_overrides(session, codes["company"], "actual", window, [], codes["root"])
    assert result["subtree"] is None

    with_subtree = compute_npat_with_overrides(
        session, codes["company"], "actual", window, [], codes["root"], include_subtree=True
    )
    assert codes["root"] in with_subtree["subtree"]


# --- candidate discovery -----------------------------------------------------


def test_terminal_driver_candidates_from_root_excludes_composite_and_root(session):
    codes = fixture_graph(session)
    engine = DriverEngine(session, [codes["company"]], _window(session, codes, 12))
    vdt_nodes = build_vdt_tree(session, [codes["company"]], codes["year"])

    candidates = terminal_driver_candidates(engine, codes["root"], vdt_nodes)

    assert candidates == sorted([codes["driver_headcount"], codes["driver_base_rate"]])
    assert codes["driver_rate"] not in candidates  # composite (is_driven) Driver
    assert codes["root"] not in candidates


def test_terminal_driver_candidates_narrower_scope(session):
    codes = fixture_graph(session)
    engine = DriverEngine(session, [codes["company"]], _window(session, codes, 12))
    vdt_nodes = build_vdt_tree(session, [codes["company"]], codes["year"])

    candidates = terminal_driver_candidates(engine, codes["act_top"], vdt_nodes)
    assert candidates == sorted([codes["driver_headcount"], codes["driver_base_rate"]])

    # Revenue's subtree has no driven descendants at all.
    empty = terminal_driver_candidates(engine, codes["rev"], vdt_nodes)
    assert empty == []


def test_terminal_driver_candidates_cycle_safe_terminates(session):
    codes = fixture_graph(session)
    vdt_nodes = build_vdt_tree(session, [codes["company"]], codes["year"])

    # A cyclic pair of Driver Formulas, wired into VA-1's formula as an extra
    # additive term so the walk actually reaches them from a real scope node.
    session.add_all(
        [
            Driver(code="DRV-CYCLE-A", description="Cycle A", unit=OperationalUnit.RATIO),
            Driver(code="DRV-CYCLE-B", description="Cycle B", unit=OperationalUnit.RATIO),
            DriverFormula(code="FORMULA-CYCLE-A", description="Cycle A Formula", target_code="DRV-CYCLE-A"),
            DriverFormula(code="FORMULA-CYCLE-B", description="Cycle B Formula", target_code="DRV-CYCLE-B"),
        ]
    )
    session.add_all(
        [
            DriverFormulaTerm(formula_code="FORMULA-CYCLE-A", term_index=0, operand_index=0, driver_code="DRV-CYCLE-B"),
            DriverFormulaTerm(formula_code="FORMULA-CYCLE-B", term_index=0, operand_index=0, driver_code="DRV-CYCLE-A"),
            DriverFormulaTerm(
                formula_code=codes["formula_va1"], term_index=1, operand_index=0, driver_code="DRV-CYCLE-A"
            ),
        ]
    )
    session.commit()

    engine = DriverEngine(session, [codes["company"]], _window(session, codes, 12))

    # Must terminate (not hang) and must not fabricate a bogus terminal from
    # inside the cycle — both drivers in the cycle stay is_driven the whole
    # way round, so the guard yields an empty contribution from that branch.
    candidates = terminal_driver_candidates(engine, codes["root"], vdt_nodes)
    assert candidates == sorted([codes["driver_headcount"], codes["driver_base_rate"]])


# --- elasticity --------------------------------------------------------------


def test_elasticity_both_directions_kept_and_cost_driver_bump_is_adverse(session):
    codes = fixture_graph(session)
    window = _window(session, codes, 2)
    engine = DriverEngine(session, [codes["company"]], window)
    vdt_nodes = build_vdt_tree(session, [codes["company"]], month_codes=window)
    candidates = terminal_driver_candidates(engine, codes["root"], vdt_nodes)
    total = len(candidates) * 2

    events = list(
        compute_sensitivity(session, codes["company"], "actual", window, codes["root"], candidates, 10.0, engine, total)
    )
    progress = [e for e in events if e["type"] == "progress"]
    result = next(e for e in events if e["type"] == "result")

    assert len(progress) == total
    assert progress[-1]["completed"] == total

    headcount = next(c for c in result["candidates"] if c["driverCode"] == codes["driver_headcount"])
    assert not headcount["na"]
    assert headcount["up"]["elasticityPct"] is not None
    assert headcount["down"]["elasticityPct"] is not None
    # VA-1's FA anchor is DEBIT (a cost) — bumping headcount UP grows the cost,
    # which must read as adverse to NPAT (see docs/adr/0023's sign convention).
    assert headcount["up"]["polarity"] == "adverse"
    assert headcount["down"]["polarity"] == "favourable"

    # Ranking descending by max |elasticity|, N/A last (none here).
    magnitudes = [c["rankMagnitude"] for c in result["ranked"]]
    assert magnitudes == sorted(magnitudes, reverse=True)


def test_shared_driver_outside_scope_measured_to_npat_in_full(session):
    codes = fixture_graph(session)
    window = _window(session, codes, 2)

    # A second Activity Node/Posting Activity Account, sibling to act_top,
    # reusing the SAME terminal Driver (headcount) but living OUTSIDE act_top.
    session.add_all(
        [
            ActivityNode(code="ACT-OTHER", description="Other Activity", parent_code=codes["cor"], level=2),
        ]
    )
    session.commit()
    session.add_all(
        [
            PostingActivityAccount(
                code="VA-3", description="Other Driven Account", parent_code="ACT-OTHER", fa_gl_code=codes["gl_anchor_leaf"]
            ),
        ]
    )
    session.commit()
    session.add_all(
        [DriverFormula(code="FORMULA-VA3", description="VA-3 Formula", target_code="VA-3", sign=1)]
    )
    session.commit()
    session.add_all(
        [
            DriverFormulaTerm(
                formula_code="FORMULA-VA3", term_index=0, operand_index=0, driver_code=codes["driver_headcount"]
            )
        ]
    )
    session.commit()

    engine_before = DriverEngine(session, [codes["company"]], window)
    vdt_before = build_vdt_tree(session, [codes["company"]], month_codes=window)
    # scope=ACT-TOP still discovers headcount (via VA-1) even though VA-3 (also
    # using headcount) sits entirely outside ACT-TOP's subtree.
    candidates = terminal_driver_candidates(engine_before, codes["act_top"], vdt_before)
    assert codes["driver_headcount"] in candidates
    assert "VA-3" not in vdt_before[codes["act_top"]]["childIds"]

    total = len(candidates) * 2
    result = next(
        e
        for e in compute_sensitivity(
            session, codes["company"], "actual", window, codes["root"], candidates, 10.0, engine_before, total
        )
        if e["type"] == "result"
    )
    with_va3 = next(c for c in result["candidates"] if c["driverCode"] == codes["driver_headcount"])

    # Compare against the same run on the ORIGINAL fixture (no VA-3) — the
    # scoped-but-globally-shared candidate's reported impact must be strictly
    # larger once a second, out-of-scope consumer of the same Driver exists,
    # proving elasticity is measured to NPAT (full usage), not truncated to scope.
    session2_codes = None

    from sqlmodel import Session, SQLModel, create_engine as _create_engine
    from sqlalchemy.pool import StaticPool

    plain_engine = _create_engine("sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool)
    SQLModel.metadata.create_all(plain_engine)
    with Session(plain_engine) as plain_session:
        session2_codes = fixture_graph(plain_session)
        plain_driver_engine = DriverEngine(plain_session, [session2_codes["company"]], window)
        plain_vdt = build_vdt_tree(plain_session, [session2_codes["company"]], month_codes=window)
        plain_candidates = terminal_driver_candidates(plain_driver_engine, session2_codes["act_top"], plain_vdt)
        plain_total = len(plain_candidates) * 2
        without_va3_result = next(
            e
            for e in compute_sensitivity(
                plain_session, session2_codes["company"], "actual", window, session2_codes["root"],
                plain_candidates, 10.0, plain_driver_engine, plain_total,
            )
            if e["type"] == "result"
        )
    without_va3 = next(
        c for c in without_va3_result["candidates"] if c["driverCode"] == session2_codes["driver_headcount"]
    )

    assert abs(with_va3["up"]["npatImpact"]) > abs(without_va3["up"]["npatImpact"])


# --- N/A semantics ------------------------------------------------------------


def test_baseline_npat_near_zero_flags_all_na_but_keeps_dollar_impact(session):
    codes = fixture_graph(session)
    window = _window(session, codes, 2)

    # Revenue's monthly fact (100/month) offset down to exactly cancel
    # COR's fixed -20/month VDT rollup (headcount 10 x rate 2 = 20, DEBIT
    # anchor flips sign) — NPAT lands at exactly 0 every month in the window.
    for row in session.exec(select(DriverFact)).all():
        pass
    from models import GLFact

    for row in session.exec(select(GLFact)).all():
        if row.code == codes["gl_leaf_rev"] and row.scenario == Scenario.ACTUAL:
            row.amount = Decimal("20.00")
            session.add(row)
    session.commit()

    engine = DriverEngine(session, [codes["company"]], window)
    vdt_nodes = build_vdt_tree(session, [codes["company"]], month_codes=window)
    candidates = terminal_driver_candidates(engine, codes["root"], vdt_nodes)
    total = len(candidates) * 2

    result = next(
        e
        for e in compute_sensitivity(
            session, codes["company"], "actual", window, codes["root"], candidates, 10.0, engine, total
        )
        if e["type"] == "result"
    )

    assert result["npatNearZero"] is True
    assert result["reason"] == "all-na"
    assert result["ranked"] == []
    for candidate in result["candidates"]:
        assert candidate["na"] is True
        assert candidate["naReason"] == "baseline-npat-zero"
        assert candidate["up"]["elasticityPct"] is None
        # $ impact still meaningful even though elasticity is undefined.
        assert candidate["up"]["npatImpact"] != 0.0 or candidate["down"]["npatImpact"] != 0.0


def test_baseline_driver_zero_flags_na(session):
    codes = fixture_graph(session)
    window = _window(session, codes, 2)

    for row in session.exec(select(DriverFact)).all():
        if row.code == codes["driver_headcount"]:
            row.amount = Decimal("0")
            session.add(row)
    session.commit()

    engine = DriverEngine(session, [codes["company"]], window)
    vdt_nodes = build_vdt_tree(session, [codes["company"]], month_codes=window)
    candidates = terminal_driver_candidates(engine, codes["root"], vdt_nodes)
    total = len(candidates) * 2

    result = next(
        e
        for e in compute_sensitivity(
            session, codes["company"], "actual", window, codes["root"], candidates, 10.0, engine, total
        )
        if e["type"] == "result"
    )
    headcount = next(c for c in result["candidates"] if c["driverCode"] == codes["driver_headcount"])
    assert headcount["na"] is True
    assert headcount["naReason"] == "baseline-driver-zero"
    # Base rate is unaffected — only headcount is zeroed.
    base_rate = next(c for c in result["candidates"] if c["driverCode"] == codes["driver_base_rate"])
    assert base_rate["na"] is False


def test_divide_by_zero_site_flags_candidate_feeding_it(session):
    codes = fixture_graph(session)
    window = _window(session, codes, 12)

    # A new terminal Driver used as a DIVIDE operand in FORMULA-RATE, exactly
    # zero in one month (not near-zero on average — isolates this from the
    # baseline-driver-zero relative check).
    session.add(Driver(code="DRV-ZERO-DIVISOR", description="Zero Divisor", unit=OperationalUnit.RATIO))
    session.commit()
    session.add(
        DriverFormulaTerm(
            formula_code=codes["formula_rate"], term_index=0, operand_index=1,
            driver_code="DRV-ZERO-DIVISOR", operator=FormulaOperator.DIVIDE,
        )
    )
    facts = []
    for i, month_code in enumerate(window):
        amount = Decimal("0") if i == 5 else Decimal("5")
        facts.append(DriverFact(code="DRV-ZERO-DIVISOR", company=codes["company"], period_code=month_code, scenario=Scenario.ACTUAL, amount=amount))
    session.add_all(facts)
    session.commit()

    engine = DriverEngine(session, [codes["company"]], window)
    vdt_nodes = build_vdt_tree(session, [codes["company"]], month_codes=window)
    candidates = terminal_driver_candidates(engine, codes["root"], vdt_nodes)
    assert "DRV-ZERO-DIVISOR" in candidates
    total = len(candidates) * 2

    result = next(
        e
        for e in compute_sensitivity(
            session, codes["company"], "actual", window, codes["root"], candidates, 10.0, engine, total
        )
        if e["type"] == "result"
    )
    divisor_result = next(c for c in result["candidates"] if c["driverCode"] == "DRV-ZERO-DIVISOR")
    assert divisor_result["na"] is True
    assert divisor_result["naReason"] == "divide-by-zero"


def test_empty_scope_returns_no_terminal_drivers_reason(session):
    codes = fixture_graph(session)
    window = _window(session, codes, 2)
    engine = DriverEngine(session, [codes["company"]], window)
    vdt_nodes = build_vdt_tree(session, [codes["company"]], month_codes=window)

    candidates = terminal_driver_candidates(engine, codes["rev"], vdt_nodes)
    assert candidates == []
    total = len(candidates) * 2
    assert total == 0

    events = list(
        compute_sensitivity(session, codes["company"], "actual", window, codes["root"], candidates, 10.0, engine, total)
    )
    assert [e["type"] for e in events] == ["result"]
    result = events[0]
    assert result["reason"] == "no-terminal-drivers"
    assert result["ranked"] == []
    assert result["candidates"] == []


def test_partial_trailing_window_batches_reruns_independent_of_width(session):
    """Window width no longer multiplies the cycle count — every month in the
    window batches into ONE compute_npat_with_overrides() call per direction
    (see vdt_sensitivity.py's SENSITIVITY_MAX_CYCLES note), so a 3-month
    partial window costs the same `candidates * 2` reruns as a 12-month one;
    this only proves a partial (narrower-than-12) window still threads
    correctly through that single batched call, not that reruns scale with it."""
    codes = fixture_graph(session)
    window = _window(session, codes, 3)  # a short "partial window" stand-in
    engine = DriverEngine(session, [codes["company"]], window)
    vdt_nodes = build_vdt_tree(session, [codes["company"]], month_codes=window)
    candidates = terminal_driver_candidates(engine, codes["root"], vdt_nodes)
    total = len(candidates) * 2
    assert total == len(candidates) * 2  # width-independent, unlike pre-batching

    events = list(
        compute_sensitivity(session, codes["company"], "actual", window, codes["root"], candidates, 10.0, engine, total)
    )
    progress = [e for e in events if e["type"] == "progress"]
    assert len(progress) == total
    result = next(e for e in events if e["type"] == "result")
    assert result["months"] == window


# --- endpoint -----------------------------------------------------------------


def _read_sse_events(resp) -> list[dict]:
    import json

    events = []
    buffer = ""
    for chunk in resp.iter_text():
        buffer += chunk
    for frame in buffer.split("\n\n"):
        frame = frame.strip()
        if not frame:
            continue
        assert frame.startswith("data: ")
        events.append(json.loads(frame[len("data: "):]))
    return events


def test_sensitivity_endpoint_streams_progress_then_result(session):
    codes = fixture_graph(session)
    client = _client(session)

    with client.stream(
        "POST",
        "/api/vdt/sensitivity",
        json={"scope": codes["company"], "scopeNode": codes["act_top"], "bumpPct": 10.0, "scenario": "actual", "year": codes["year"]},
    ) as resp:
        assert resp.status_code == 200
        assert resp.headers["content-type"].startswith("text/event-stream")
        events = _read_sse_events(resp)

    assert any(e["type"] == "progress" for e in events)
    result = next(e for e in events if e["type"] == "result")
    assert result["scope"] == codes["company"]
    assert result["scopeNode"] == codes["act_top"]
    assert result["bumpPct"] == 10.0
    assert result["candidateCount"] == 2


def test_sensitivity_endpoint_rejects_bump_pct_out_of_range(session):
    codes = fixture_graph(session)
    client = _client(session)

    resp = client.post(
        "/api/vdt/sensitivity",
        json={"scope": codes["company"], "scopeNode": codes["root"], "bumpPct": 21.0, "year": codes["year"]},
    )
    assert resp.status_code == 422

    # Lower bound is exclusive-below-1 too, not just the upper bound above 20.
    resp = client.post(
        "/api/vdt/sensitivity",
        json={"scope": codes["company"], "scopeNode": codes["root"], "bumpPct": 0.5, "year": codes["year"]},
    )
    assert resp.status_code == 422


def test_sensitivity_endpoint_trailing_window_resolves_and_streams(session):
    """Coverage gap: every other endpoint test drives the Financial Year
    (`year=`) branch only — `trailingEnd` is otherwise exercised solely by
    the "both provided -> 400" rejection test, which never reaches
    `_resolve_trailing_window`. `fixture_graph` seeds a single fiscal year
    (FY24 only, see conftest.py), so this can't be a genuine cross-fiscal-year
    trailing window without extending the fixture, but anchoring mid-year
    (FY24-M06) with only one year of history seeded still exercises the real
    partial-window behaviour `trailing_month_codes()` documents ("fewer than
    window_length codes if history runs out before the window is full") and
    walks the endpoint's `trailingEnd` branch end-to-end: window resolution,
    `calendar_month_label` month labels, and the "trailing N months ending..."
    windowLabel format."""
    codes = fixture_graph(session)
    client = _client(session)

    with client.stream(
        "POST",
        "/api/vdt/sensitivity",
        json={
            "scope": codes["company"], "scopeNode": codes["root"], "bumpPct": 10.0,
            "scenario": "actual", "trailingEnd": f"{codes['year']}-M06",
        },
    ) as resp:
        assert resp.status_code == 200
        events = _read_sse_events(resp)

    result = next(e for e in events if e["type"] == "result")
    # History runs out at FY24-M01, so the 12-month-wide window request is
    # truncated to the 6 months actually available (M01..M06 inclusive).
    assert result["months"] == [f"{codes['year']}-M{m:02d}" for m in range(1, 7)]
    assert len(result["monthLabels"]) == 6
    assert result["monthLabels"][-1] == "Jun '24"
    assert result["windowLabel"] == "trailing 6 months ending Jun '24"


def test_sensitivity_endpoint_rejects_bad_scenario(session):
    codes = fixture_graph(session)
    client = _client(session)

    resp = client.post(
        "/api/vdt/sensitivity",
        json={"scope": codes["company"], "scopeNode": codes["root"], "bumpPct": 10.0, "scenario": "nope", "year": codes["year"]},
    )
    assert resp.status_code == 400


def test_sensitivity_endpoint_requires_exactly_one_of_year_or_trailing_end(session):
    codes = fixture_graph(session)
    client = _client(session)

    resp = client.post("/api/vdt/sensitivity", json={"scope": codes["company"], "scopeNode": codes["root"], "bumpPct": 10.0})
    assert resp.status_code == 400

    resp = client.post(
        "/api/vdt/sensitivity",
        json={
            "scope": codes["company"], "scopeNode": codes["root"], "bumpPct": 10.0,
            "year": codes["year"], "trailingEnd": f"{codes['year']}-M06",
        },
    )
    assert resp.status_code == 400


def test_sensitivity_endpoint_rejects_unknown_scope_node(session):
    codes = fixture_graph(session)
    client = _client(session)

    resp = client.post(
        "/api/vdt/sensitivity",
        json={"scope": codes["company"], "scopeNode": "NOT-REAL", "bumpPct": 10.0, "year": codes["year"]},
    )
    assert resp.status_code == 404


def test_sensitivity_endpoint_rejects_not_yet_modelled_company(session):
    fixture_graph(session)
    client = _client(session)

    resp = client.post(
        "/api/vdt/sensitivity",
        json={"scope": "NOT-REAL", "scopeNode": "NPAT", "bumpPct": 10.0, "year": "FY24"},
    )
    assert resp.status_code == 404


def test_sensitivity_endpoint_cap_guard(session, monkeypatch):
    codes = fixture_graph(session)
    monkeypatch.setattr(main, "SENSITIVITY_MAX_CYCLES", 1)
    client = _client(session)

    resp = client.post(
        "/api/vdt/sensitivity",
        json={"scope": codes["company"], "scopeNode": codes["root"], "bumpPct": 10.0, "year": codes["year"]},
    )
    assert resp.status_code == 422
    assert "cap 1" in resp.json()["detail"]


def test_sensitivity_event_stream_stops_on_disconnect_without_further_compute():
    class FakeRequest:
        async def is_disconnected(self) -> bool:
            return True

    pulled: list[int] = []

    def fake_events():
        pulled.append(1)
        yield {"type": "progress", "completed": 1, "total": 5}
        pulled.append(2)
        yield {"type": "progress", "completed": 2, "total": 5}

    async def collect() -> list[bytes]:
        chunks = []
        async for chunk in main._sensitivity_event_stream(fake_events(), FakeRequest(), lambda e: e):
            chunks.append(chunk)
        return chunks

    chunks = asyncio.run(collect())
    assert chunks == []
    # The generator was pulled once (to obtain the first event) and then
    # abandoned as soon as is_disconnected() came back True — no second rerun.
    assert pulled == [1]
