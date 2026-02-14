from __future__ import annotations

import json
from pathlib import Path

import typer
import uvicorn

from vulture.api.app import create_app
from vulture.config import get_settings
from vulture.core.orchestrator import RunOrchestrator
from vulture.db.init import init_database
from vulture.db.repositories import Repository
from vulture.db.session import SessionLocal
from vulture.logging_config import configure_logging

app = typer.Typer(help="Vulture CLI")
profile_app = typer.Typer(help="Manage applicant profiles")
run_app = typer.Typer(help="Run approvals and status")
jobs_app = typer.Typer(help="Job registry commands")

app.add_typer(profile_app, name="profile")
app.add_typer(run_app, name="run")
app.add_typer(jobs_app, name="jobs")

_INITIALIZED = False


def ensure_initialized() -> None:
    global _INITIALIZED
    if _INITIALIZED:
        return
    init_database()
    _INITIALIZED = True


@app.command("init")
def init_cmd() -> None:
    """Initialize database, directories, and seed records."""
    configure_logging()
    result = init_database()
    typer.echo(json.dumps({"ok": True, **result}, indent=2))


@profile_app.command("create")
def profile_create(
    name: str = typer.Option(..., "--name"),
    job_family: str = typer.Option(..., "--job-family"),
    summary: str = typer.Option("", "--summary"),
) -> None:
    configure_logging()
    ensure_initialized()
    with SessionLocal() as db:
        repo = Repository(db)
        profile = repo.create_profile(name=name, job_family=job_family, summary=summary)
        typer.echo(json.dumps({"id": profile.id, "name": profile.name}, indent=2))


@profile_app.command("import")
def profile_import(file: Path = typer.Option(..., "--file", exists=True, readable=True)) -> None:
    configure_logging()
    ensure_initialized()
    payload = json.loads(file.read_text(encoding="utf-8"))

    with SessionLocal() as db:
        repo = Repository(db)

        if isinstance(payload, list):
            imported = []
            for item in payload:
                profile = repo.create_profile(
                    name=item["name"],
                    job_family=item["job_family"],
                    summary=item.get("summary", ""),
                )
                for answer in item.get("answers", []):
                    repo.add_profile_answer(
                        profile_id=profile.id,
                        question=answer["question"],
                        answer=answer["answer"],
                        question_type=answer.get("question_type", "custom"),
                    )
                imported.append({"id": profile.id, "name": profile.name})
            typer.echo(json.dumps({"imported": imported}, indent=2))
            return

        profile = repo.create_profile(
            name=payload["name"],
            job_family=payload["job_family"],
            summary=payload.get("summary", ""),
        )
        for answer in payload.get("answers", []):
            repo.add_profile_answer(
                profile_id=profile.id,
                question=answer["question"],
                answer=answer["answer"],
                question_type=answer.get("question_type", "custom"),
            )

        typer.echo(json.dumps({"id": profile.id, "name": profile.name}, indent=2))


@profile_app.command("add-answer")
def profile_add_answer(
    profile_id: int = typer.Option(..., "--profile-id"),
    question: str = typer.Option(..., "--question"),
    answer: str = typer.Option(..., "--answer"),
    question_type: str = typer.Option("custom", "--question-type"),
) -> None:
    configure_logging()
    ensure_initialized()
    with SessionLocal() as db:
        repo = Repository(db)
        if not repo.get_profile(profile_id):
            raise typer.BadParameter(f"profile {profile_id} not found")
        row = repo.add_profile_answer(
            profile_id=profile_id,
            question=question,
            answer=answer,
            question_type=question_type,
        )
        typer.echo(json.dumps({"id": row.id, "question_hash": row.question_hash}, indent=2))


@app.command("apply")
def apply_cmd(
    url: str = typer.Option(..., "--url"),
    profile: int = typer.Option(..., "--profile"),
    mode: str = typer.Option("medium", "--mode"),
    submit: bool = typer.Option(False, "--submit"),
) -> None:
    configure_logging()
    ensure_initialized()
    with SessionLocal() as db:
        orchestrator = RunOrchestrator(db)
        run = orchestrator.start_application(url=url, profile_id=profile, mode=mode, submit=submit)
        events = Repository(db).get_pending_approval_events(run["id"])
        typer.echo(
            json.dumps(
                {
                    "run": run,
                    "pending_approvals": [
                        {"event_id": event.id, "stage": event.stage, "action": event.action}
                        for event in events
                    ],
                },
                indent=2,
            )
        )


@run_app.command("status")
def run_status(run_id: int = typer.Option(..., "--run-id")) -> None:
    configure_logging()
    ensure_initialized()
    with SessionLocal() as db:
        orchestrator = RunOrchestrator(db)
        run = orchestrator.serialize_run(run_id)
        events = Repository(db).list_run_events(run_id)
        typer.echo(
            json.dumps(
                {
                    "run": run,
                    "events": [
                        {
                            "id": event.id,
                            "stage": event.stage,
                            "action": event.action,
                            "requires_approval": event.requires_approval,
                            "approval_state": event.approval_state,
                        }
                        for event in events
                    ],
                },
                indent=2,
            )
        )


@run_app.command("approve")
def run_approve(
    run_id: int = typer.Option(..., "--run-id"),
    event_id: int = typer.Option(..., "--event-id"),
) -> None:
    configure_logging()
    ensure_initialized()
    with SessionLocal() as db:
        orchestrator = RunOrchestrator(db)
        run = orchestrator.approve_event(run_id=run_id, event_id=event_id)
        typer.echo(json.dumps(run, indent=2))


@run_app.command("reject")
def run_reject(
    run_id: int = typer.Option(..., "--run-id"),
    event_id: int = typer.Option(..., "--event-id"),
) -> None:
    configure_logging()
    ensure_initialized()
    with SessionLocal() as db:
        orchestrator = RunOrchestrator(db)
        run = orchestrator.reject_event(run_id=run_id, event_id=event_id)
        typer.echo(json.dumps(run, indent=2))


@jobs_app.command("list")
def jobs_list(limit: int = typer.Option(20, "--limit")) -> None:
    configure_logging()
    ensure_initialized()
    with SessionLocal() as db:
        repo = Repository(db)
        jobs = repo.list_jobs(limit=limit)
        typer.echo(
            json.dumps(
                [
                    {
                        "id": job.id,
                        "title": job.title,
                        "company": job.company,
                        "domain": job.domain,
                        "url": job.url,
                        "created_at": job.created_at.isoformat() if job.created_at else None,
                    }
                    for job in jobs
                ],
                indent=2,
            )
        )


@app.command("serve")
def serve(
    host: str | None = typer.Option(None, "--host"),
    port: int | None = typer.Option(None, "--port"),
) -> None:
    configure_logging()
    ensure_initialized()
    settings = get_settings()
    app_instance = create_app()
    uvicorn.run(app_instance, host=host or settings.app_host, port=port or settings.app_port)
