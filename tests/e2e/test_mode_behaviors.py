from vulture.core.orchestrator import RunOrchestrator
from vulture.db.repositories import Repository
from vulture.db.session import SessionLocal
from vulture.types import BrowserFillResult


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


def test_linkedin_yolo_uses_linkedin_action_sequence(monkeypatch) -> None:
    monkeypatch.setattr(
        "vulture.core.orchestrator.fetch_job_text",
        lambda url, timeout_sec=30: "Software Engineer\nRequirements: Python\nResponsibilities: APIs",
    )

    actions_seen: list[str] = []

    def fake_execute_action(self, context, action: str) -> BrowserFillResult:
        actions_seen.append(action)
        return BrowserFillResult(status="completed", stage="browser", action=action, message="ok")

    monkeypatch.setattr(
        "vulture.browser.engine.BrowserAutomationEngine.execute_action",
        fake_execute_action,
    )

    with SessionLocal() as db:
        profile = _setup_profile(db)
        orchestrator = RunOrchestrator(db)
        run = orchestrator.start_application(
            url="https://www.linkedin.com/jobs/view/123456789",
            profile_id=profile.id,
            mode="yolo",
            submit=False,
        )
        assert run["status"] == "completed"
        assert run["context"]["domain_adapter"] == "linkedin"
        assert actions_seen == [
            "start_session",
            "linkedin_open_easy_apply",
            "linkedin_fill_steps",
            "upload_resume",
            "submit_application",
        ]


def test_linkedin_non_easy_apply_blocks_run(monkeypatch) -> None:
    monkeypatch.setattr(
        "vulture.core.orchestrator.fetch_job_text",
        lambda url, timeout_sec=30: "Software Engineer\nRequirements: Python\nResponsibilities: APIs",
    )

    actions_seen: list[str] = []

    def fake_execute_action(self, context, action: str) -> BrowserFillResult:
        actions_seen.append(action)
        if action == "linkedin_open_easy_apply":
            return BrowserFillResult(
                status="blocked",
                stage="start_browser_session",
                action=action,
                message="LinkedIn Easy Apply is not available for this posting.",
            )
        return BrowserFillResult(status="completed", stage="browser", action=action, message="ok")

    monkeypatch.setattr(
        "vulture.browser.engine.BrowserAutomationEngine.execute_action",
        fake_execute_action,
    )

    with SessionLocal() as db:
        repo = Repository(db)
        profile = _setup_profile(db)
        orchestrator = RunOrchestrator(db)
        run = orchestrator.start_application(
            url="https://www.linkedin.com/jobs/view/987654321",
            profile_id=profile.id,
            mode="yolo",
            submit=True,
        )
        assert run["status"] == "blocked"
        assert run["current_stage"] == "blocked"
        assert actions_seen == ["start_session", "linkedin_open_easy_apply"]

        events = repo.list_run_events(run["id"])
        assert any(
            event.action == "blocked:linkedin_open_easy_apply"
            and "Easy Apply" in event.payload_json.get("message", "")
            for event in events
        )
