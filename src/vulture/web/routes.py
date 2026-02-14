from __future__ import annotations

from pathlib import Path

from fastapi import APIRouter, Depends, Form, Request
from fastapi.responses import FileResponse, HTMLResponse, RedirectResponse, Response
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session

from vulture.api.deps import get_db
from vulture.core.orchestrator import RunOrchestrator
from vulture.db.repositories import Repository

router = APIRouter(tags=["web"])
templates = Jinja2Templates(
    directory=str(Path(__file__).resolve().parents[1] / "web" / "templates")
)
static_dir = Path(__file__).resolve().parents[1] / "web" / "static"


def _icon_response(*filenames: str) -> Response:
    for filename in filenames:
        icon_path = static_dir / filename
        if icon_path.is_file():
            return FileResponse(icon_path)
    # Avoid noisy 404s in browser/devtools when icon files are not provided.
    return Response(status_code=204)


@router.get("/favicon.ico", include_in_schema=False)
def favicon() -> Response:
    return _icon_response("favicon.ico", "favicon.png", "favicon.svg")


@router.get("/apple-touch-icon.png", include_in_schema=False)
def apple_touch_icon() -> Response:
    return _icon_response("apple-touch-icon.png", "apple-touch-icon.svg")


@router.get("/apple-touch-icon-precomposed.png", include_in_schema=False)
def apple_touch_icon_precomposed() -> Response:
    return _icon_response(
        "apple-touch-icon-precomposed.png",
        "apple-touch-icon.png",
        "apple-touch-icon.svg",
    )


@router.get("/", response_class=HTMLResponse)
def dashboard(request: Request, db: Session = Depends(get_db)) -> HTMLResponse:
    repo = Repository(db)
    return templates.TemplateResponse(
        "dashboard.html",
        {
            "request": request,
            "profiles": repo.list_profiles(),
            "jobs": repo.list_jobs(limit=20),
            "runs": repo.list_runs(limit=20),
        },
    )


@router.post("/web/profiles")
def create_profile(
    name: str = Form(...),
    job_family: str = Form(...),
    summary: str = Form(""),
    db: Session = Depends(get_db),
):
    repo = Repository(db)
    repo.create_profile(name=name, job_family=job_family, summary=summary)
    return RedirectResponse(url="/", status_code=303)


@router.post("/web/runs")
def create_run(
    url: str = Form(...),
    profile_id: int = Form(...),
    mode: str = Form("medium"),
    submit: bool = Form(False),
    db: Session = Depends(get_db),
):
    orchestrator = RunOrchestrator(db)
    run = orchestrator.start_application(url=url, profile_id=profile_id, mode=mode, submit=submit)
    return RedirectResponse(url=f"/runs/{run['id']}", status_code=303)


@router.get("/runs/{run_id}", response_class=HTMLResponse)
def run_detail(run_id: int, request: Request, db: Session = Depends(get_db)) -> HTMLResponse:
    repo = Repository(db)
    run = repo.get_run(run_id)
    if not run:
        return templates.TemplateResponse(
            "not_found.html",
            {"request": request, "message": "Run not found"},
            status_code=404,
        )

    events = repo.list_run_events(run_id)
    pending = repo.get_pending_approval_events(run_id)
    job = repo.get_job(run.job_id)
    profile = repo.get_profile(run.profile_id)

    return templates.TemplateResponse(
        "run_detail.html",
        {
            "request": request,
            "run": run,
            "events": events,
            "pending": pending,
            "job": job,
            "profile": profile,
        },
    )


@router.post("/web/runs/{run_id}/approve")
def approve(
    run_id: int,
    event_id: int = Form(...),
    db: Session = Depends(get_db),
):
    orchestrator = RunOrchestrator(db)
    orchestrator.approve_event(run_id=run_id, event_id=event_id)
    return RedirectResponse(url=f"/runs/{run_id}", status_code=303)


@router.post("/web/runs/{run_id}/reject")
def reject(
    run_id: int,
    event_id: int = Form(...),
    db: Session = Depends(get_db),
):
    orchestrator = RunOrchestrator(db)
    orchestrator.reject_event(run_id=run_id, event_id=event_id)
    return RedirectResponse(url=f"/runs/{run_id}", status_code=303)
