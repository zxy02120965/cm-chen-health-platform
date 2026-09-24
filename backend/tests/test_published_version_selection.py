from datetime import datetime, timedelta

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app import db
from app import main


@pytest.fixture
def isolated_db(monkeypatch):
    """Exercise published reads against an isolated SQLite database only."""
    test_engine = create_engine("sqlite:///:memory:")
    db.Base.metadata.create_all(test_engine)
    TestSession = sessionmaker(bind=test_engine, autoflush=False, expire_on_commit=False)
    monkeypatch.setattr(db, "SessionLocal", TestSession)
    monkeypatch.setattr(main, "SessionLocal", TestSession)
    yield TestSession


def _plan_with_versions(session, *, plan_status, versions):
    plan = db.PlanRow(
        patient_id="P001",
        status=plan_status,
        current_version_no=max(version_no for version_no, _ in versions),
        updated_at=datetime(2026, 9, 17),
    )
    session.add(plan)
    session.flush()
    for index, (version_no, status) in enumerate(versions):
        session.add(
            db.PlanVersionRow(
                plan_id=plan.plan_id,
                version_no=version_no,
                status=status,
                content_json={"marker": f"v{version_no}"},
                published_at=datetime(2026, 9, 1) + timedelta(days=index) if status == "PUBLISHED" else None,
            )
        )
    session.commit()
    return plan


def test_reads_latest_published_when_plan_is_in_review(isolated_db):
    with isolated_db() as session:
        _plan_with_versions(session, plan_status="IN_REVIEW", versions=[(13, "PUBLISHED"), (14, "IN_REVIEW")])

    result = db.read_published_plan("P001")
    assert result["plan_version_id"] == 1
    assert result["version"] == 13
    assert result["status"] == "PUBLISHED"
    assert result["marker"] == "v13"


def test_selects_highest_published_version_not_current_draft(isolated_db):
    with isolated_db() as session:
        _plan_with_versions(
            session,
            plan_status="IN_REVIEW",
            versions=[(10, "PUBLISHED"), (12, "PUBLISHED"), (13, "PUBLISHED"), (14, "IN_REVIEW")],
        )

    result = db.read_published_plan("P001")
    assert result["version"] == 13
    assert result["marker"] == "v13"


def test_returns_none_when_no_published_version_exists(isolated_db):
    with isolated_db() as session:
        _plan_with_versions(session, plan_status="IN_REVIEW", versions=[(1, "RULE_GENERATED_PENDING_REVIEW"), (2, "IN_REVIEW")])

    assert db.read_published_plan("P001") is None


def test_published_plan_row_still_reads_published_version(isolated_db):
    with isolated_db() as session:
        _plan_with_versions(session, plan_status="PUBLISHED", versions=[(1, "PUBLISHED")])

    result = db.read_published_plan("P001")
    assert result["version"] == 1
    assert result["status"] == "PUBLISHED"


def test_plan_tasks_follow_same_published_version(isolated_db, monkeypatch):
    with isolated_db() as session:
        plan = _plan_with_versions(session, plan_status="IN_REVIEW", versions=[(13, "PUBLISHED"), (14, "IN_REVIEW")])
        versions = session.query(db.PlanVersionRow).filter_by(plan_id=plan.plan_id).order_by(db.PlanVersionRow.version_no).all()
        session.add_all([
            db.PlanTaskRow(plan_version_id=versions[0].plan_version_id, patient_id="P001", task_type="DIET", task_name="published task"),
            db.PlanTaskRow(plan_version_id=versions[1].plan_version_id, patient_id="P001", task_type="EXERCISE", task_name="draft task"),
        ])
        session.commit()

    monkeypatch.setattr(main, "_patient_or_404", lambda patient_id: {"patient_id": patient_id})
    tasks = main.list_plan_tasks("P001")
    assert tasks
    assert {task["plan_version_id"] for task in tasks} == {1}
    assert [task["task_name"] for task in tasks] == ["published task"]
