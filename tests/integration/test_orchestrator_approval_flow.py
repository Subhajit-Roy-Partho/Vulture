from vulture.core.orchestrator import RunOrchestrator
from vulture.db.repositories import Repository
from vulture.db.session import SessionLocal


def test_strict_mode_pauses_for_approval_and_resumes(monkeypatch) -> None:
    monkeypatch.setattr(
        "vulture.core.orchestrator.fetch_job_text",
        lambda url, timeout_sec=30: (
            "Backend Engineer\nResponsibilities: Build APIs\nRequirements: Python, SQL"
        ),
    )

    with SessionLocal() as db:
        repo = Repository(db)
        profile = repo.create_profile(name="Main", job_family="Engineering", summary="")
        orchestrator = RunOrchestrator(db)

        run = orchestrator.start_application(
            url="https://example.com/jobs/1",
            profile_id=profile.id,
            mode="strict",
            submit=False,
        )
        assert run["status"] == "waiting_approval"

        pending = repo.get_pending_approval_events(run["id"])
        assert pending
        assert pending[0].stage == "job_parsing_start"

        run_after = orchestrator.approve_event(run_id=run["id"], event_id=pending[0].id)
        assert run_after["status"] in {"waiting_approval", "running"}

        pending_after = repo.get_pending_approval_events(run["id"])
        assert any(event.stage == "cv_tailoring_output" for event in pending_after)
