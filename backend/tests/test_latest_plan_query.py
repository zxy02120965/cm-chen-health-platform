from datetime import datetime, timedelta

import pytest
from sqlalchemy import create_engine, event
from sqlalchemy.orm import sessionmaker

from app import db


@pytest.fixture
def query_db(monkeypatch):
    engine = create_engine("sqlite:///:memory:")
    db.Base.metadata.create_all(engine)
    session_factory = sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)
    monkeypatch.setattr(db, "SessionLocal", session_factory)
    yield engine, session_factory


def _seed_versions(session_factory, versions):
    with session_factory() as session:
        plan = db.PlanRow(
            patient_id="P003",
            status="IN_REVIEW",
            current_version_no=max(v[0] for v in versions),
            updated_at=datetime(2026, 9, 20),
        )
        session.add(plan)
        session.flush()
        for offset, (version_no, status) in enumerate(versions):
            session.add(
                db.PlanVersionRow(
                    plan_id=plan.plan_id,
                    version_no=version_no,
                    status=status,
                    published_at=datetime(2026, 9, 1) + timedelta(days=offset) if status == "PUBLISHED" else None,
                    content_json={"marker": f"v{version_no}-{offset}", "large_snapshot": "x" * 10000},
                )
            )
        session.commit()
        return plan.plan_id


def test_clinician_latest_version_uses_highest_version(query_db):
    _, session_factory = query_db
    plan_id = _seed_versions(session_factory, [(1, "PUBLISHED"), (2, "IN_REVIEW"), (3, "RULE_GENERATED_PENDING_REVIEW")])

    with session_factory() as session:
        plan, version = db._latest_plan(session, "P003")

    assert plan.plan_id == plan_id
    assert version.version_no == 3


def test_patient_latest_published_ignores_newer_draft(query_db):
    _, session_factory = query_db
    _seed_versions(session_factory, [(1, "PUBLISHED"), (2, "RULE_GENERATED_PENDING_REVIEW")])

    result = db.read_published_plan("P003")

    assert result["status"] == "PUBLISHED"
    assert result["version"] == 1


def test_patient_latest_published_selects_highest_published_version(query_db):
    _, session_factory = query_db
    _seed_versions(session_factory, [(1, "PUBLISHED"), (2, "PUBLISHED"), (3, "IN_REVIEW")])

    result = db.read_published_plan("P003")

    assert result["status"] == "PUBLISHED"
    assert result["version"] == 2


def test_same_version_number_uses_larger_plan_version_id(query_db):
    _, session_factory = query_db
    _seed_versions(session_factory, [(5, "IN_REVIEW"), (5, "IN_REVIEW")])

    with session_factory() as session:
        _, version = db._latest_plan(session, "P003")
        ids = [row.plan_version_id for row in session.query(db.PlanVersionRow).all()]

    assert version.plan_version_id == max(ids)


def test_latest_locator_does_not_sort_content_json(query_db):
    engine, session_factory = query_db
    statements = []

    def capture(_conn, _cursor, statement, _parameters, _context, _executemany):
        statements.append(statement)

    event.listen(engine, "before_cursor_execute", capture)
    try:
        _seed_versions(session_factory, [(1, "PUBLISHED"), (2, "IN_REVIEW")])
        with session_factory() as session:
            db._latest_plan(session, "P003")
    finally:
        event.remove(engine, "before_cursor_execute", capture)

    locator_statements = [s.lower() for s in statements if "order by plan_version.version_no" in s.lower()]
    assert locator_statements
    assert all("content_json" not in statement for statement in locator_statements)
