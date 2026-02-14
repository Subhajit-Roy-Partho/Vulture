from vulture.core.orchestrator import RunOrchestrator
from vulture.db.repositories import Repository
from vulture.db.session import SessionLocal


def _setup_profile(db):
    repo = Repository(db)
    return repo.create_profile(name="Main", job_family="Engineering", summary="")


def test_medium_mode_auto_parse_then_pause_for_cv_review(monkeypatch) -> None:
    monkeypatch.setattr(
        "vulture.core.orchestrator.fetch_job_text",
        lambda url, timeout_sec=30: "Software Engineer\nRequirements: Python\nResponsibilities: APIs",
    )

    with SessionLocal() as db:
        profile = _setup_profile(db)
        repo = Repository(db)
        orchestrator = RunOrchestrator(db)
        run = orchestrator.start_application(
            url="https://example.com/jobs/medium",
            profile_id=profile.id,
            mode="medium",
            submit=False,
        )
        assert run["status"] == "waiting_approval"
        pending = repo.get_pending_approval_events(run["id"])
        assert any(event.stage == "cv_tailoring_output" for event in pending)


def test_yolo_mode_completes_without_approval(monkeypatch) -> None:
    monkeypatch.setattr(
        "vulture.core.orchestrator.fetch_job_text",
        lambda url, timeout_sec=30: "Software Engineer\nRequirements: Python\nResponsibilities: APIs",
    )

    with SessionLocal() as db:
        profile = _setup_profile(db)
        orchestrator = RunOrchestrator(db)
        run = orchestrator.start_application(
            url="https://example.com/jobs/yolo",
            profile_id=profile.id,
            mode="yolo",
            submit=False,
        )
        assert run["status"] == "completed"


def test_captcha_url_requires_human_intervention(monkeypatch) -> None:
    monkeypatch.setattr(
        "vulture.core.orchestrator.fetch_job_text",
        lambda url, timeout_sec=30: "Software Engineer\nRequirements: Python\nResponsibilities: APIs",
    )

    with SessionLocal() as db:
        repo = Repository(db)
        profile = _setup_profile(db)
        orchestrator = RunOrchestrator(db)
        run = orchestrator.start_application(
            url="https://example.com/jobs/captcha",
            profile_id=profile.id,
            mode="yolo",
            submit=True,
        )
        assert run["status"] == "waiting_captcha"
        pending = repo.get_pending_approval_events(run["id"])
        assert pending
        resumed = orchestrator.approve_event(run_id=run["id"], event_id=pending[0].id)
        assert resumed["status"] == "completed"
