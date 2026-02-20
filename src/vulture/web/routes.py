from __future__ import annotations

from pathlib import Path

from fastapi import APIRouter, Depends, Form, Request
from fastapi.responses import FileResponse, HTMLResponse, RedirectResponse, Response
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session

from vulture.api.deps import get_db
from vulture.core.cv_parser import parse_cv_text
from vulture.core.orchestrator import RunOrchestrator
from vulture.core.question_templates import generate_question_templates
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
        request,
        "dashboard.html",
        {
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
    profile = repo.create_profile(name=name, job_family=job_family, summary=summary)
    return RedirectResponse(url=f"/profiles/{profile.id}", status_code=303)


@router.get("/profiles/{profile_id}", response_class=HTMLResponse)
def profile_detail(profile_id: int, request: Request, db: Session = Depends(get_db)) -> HTMLResponse:
    repo = Repository(db)
    profile = repo.get_profile(profile_id)
    if not profile:
        return templates.TemplateResponse(
            request,
            "not_found.html",
            {"message": "Profile not found"},
            status_code=404,
        )

    personal = repo.create_or_update_profile_personal(profile_id, values={})
    context = {
        "request": request,
        "profile": profile,
        "personal": personal,
        "educations": repo.list_education(profile_id),
        "experiences": repo.list_experiences(profile_id),
        "skills": repo.list_skills(profile_id),
        "publications": repo.list_publications(profile_id),
        "awards": repo.list_awards(profile_id),
        "conferences": repo.list_conferences(profile_id),
        "teaching": repo.list_teaching(profile_id),
        "service": repo.list_service(profile_id),
        "additional_projects": repo.list_additional_projects(profile_id),
        "questionnaire": repo.list_profile_questionnaire(profile_id),
        "questionnaire_review": repo.list_profile_questionnaire_review(profile_id),
    }
    return templates.TemplateResponse(request, "profile_detail.html", context)


@router.get("/profiles/{profile_id}/questionnaire/review", response_class=HTMLResponse)
def profile_questionnaire_review_page(
    profile_id: int,
    request: Request,
    db: Session = Depends(get_db),
) -> HTMLResponse:
    repo = Repository(db)
    profile = repo.get_profile(profile_id)
    if not profile:
        return templates.TemplateResponse(
            request,
            "not_found.html",
            {"message": "Profile not found"},
            status_code=404,
        )

    return templates.TemplateResponse(
        request,
        "profile_questionnaire_review.html",
        {
            "profile": profile,
            "questionnaire_review": repo.list_profile_questionnaire_review(profile_id),
        },
    )


@router.post("/web/profiles/{profile_id}/cv/import")
def web_import_cv(
    profile_id: int,
    cv_text: str = Form(...),
    format: str = Form("latex"),
    scope: str = Form("all"),
    db: Session = Depends(get_db),
):
    repo = Repository(db)
    if not repo.get_profile(profile_id):
        return RedirectResponse(url="/", status_code=303)

    parsed = parse_cv_text(cv_text, input_format=format)
    templates = generate_question_templates(parsed, scope=scope)
    repo.import_cv_payload(
        profile_id=profile_id,
        parsed=parsed,
        templates=templates,
        input_format=format,
        scope=scope,
    )
    return RedirectResponse(url=f"/profiles/{profile_id}", status_code=303)


@router.post("/web/profiles/{profile_id}/questionnaire/{question_hash}/verify")
def web_verify_answer(
    profile_id: int,
    question_hash: str,
    db: Session = Depends(get_db),
):
    repo = Repository(db)
    try:
        repo.set_profile_answer_verification(profile_id, question_hash, "verified")
    except ValueError:
        pass
    return RedirectResponse(url=f"/profiles/{profile_id}/questionnaire/review", status_code=303)


@router.post("/web/profiles/{profile_id}/questionnaire/{question_hash}/reject")
def web_reject_answer(
    profile_id: int,
    question_hash: str,
    db: Session = Depends(get_db),
):
    repo = Repository(db)
    try:
        repo.set_profile_answer_verification(profile_id, question_hash, "rejected")
    except ValueError:
        pass
    return RedirectResponse(url=f"/profiles/{profile_id}/questionnaire/review", status_code=303)


@router.post("/web/profiles/{profile_id}/personal")
def update_personal(
    profile_id: int,
    first_name: str = Form(""),
    last_name: str = Form(""),
    email: str = Form(""),
    phone_e164: str = Form(""),
    headline: str = Form(""),
    current_company: str = Form(""),
    db: Session = Depends(get_db),
):
    repo = Repository(db)
    repo.create_or_update_profile_personal(
        profile_id,
        {
            "first_name": first_name,
            "last_name": last_name,
            "email": email,
            "phone_e164": phone_e164,
            "headline": headline,
            "current_company": current_company,
        },
    )
    return RedirectResponse(url=f"/profiles/{profile_id}", status_code=303)


@router.post("/web/profiles/{profile_id}/education")
def add_education(
    profile_id: int,
    institution: str = Form(...),
    degree: str = Form(...),
    field: str = Form(""),
    gpa: str = Form(""),
    thesis_title: str = Form(""),
    advisor: str = Form(""),
    lab: str = Form(""),
    db: Session = Depends(get_db),
):
    Repository(db).add_education(
        profile_id=profile_id,
        institution=institution,
        degree=degree,
        field=field,
        gpa=gpa,
        thesis_title=thesis_title,
        advisor=advisor,
        lab=lab,
    )
    return RedirectResponse(url=f"/profiles/{profile_id}", status_code=303)


@router.post("/web/profiles/{profile_id}/experience")
def add_experience(
    profile_id: int,
    company: str = Form(...),
    title: str = Form(...),
    description: str = Form(""),
    advisor: str = Form(""),
    impact_summary: str = Form(""),
    skills_csv: str = Form(""),
    db: Session = Depends(get_db),
):
    skills_json = [item.strip() for item in skills_csv.split(",") if item.strip()]
    Repository(db).add_experience(
        profile_id=profile_id,
        company=company,
        title=title,
        description=description,
        advisor=advisor,
        impact_summary=impact_summary,
        skills_json=skills_json,
    )
    return RedirectResponse(url=f"/profiles/{profile_id}", status_code=303)


@router.post("/web/profiles/{profile_id}/skill")
def add_skill(
    profile_id: int,
    name: str = Form(...),
    category: str = Form(...),
    years: float = Form(0.0),
    proficiency: str = Form(""),
    db: Session = Depends(get_db),
):
    Repository(db).add_skill(
        profile_id=profile_id,
        name=name,
        category=category,
        years=years,
        proficiency=proficiency,
    )
    return RedirectResponse(url=f"/profiles/{profile_id}", status_code=303)


@router.post("/web/profiles/{profile_id}/publication")
def add_publication(
    profile_id: int,
    title: str = Form(...),
    venue: str = Form(""),
    publication_year: int = Form(0),
    status: str = Form(""),
    doi: str = Form(""),
    url: str = Form(""),
    contribution: str = Form(""),
    db: Session = Depends(get_db),
):
    Repository(db).add_publication(
        profile_id=profile_id,
        title=title,
        venue=venue,
        publication_year=publication_year,
        status=status,
        doi=doi,
        url=url,
        contribution=contribution,
    )
    return RedirectResponse(url=f"/profiles/{profile_id}", status_code=303)


@router.post("/web/profiles/{profile_id}/award")
def add_award(
    profile_id: int,
    title: str = Form(...),
    issuer: str = Form(""),
    award_year: int = Form(0),
    details: str = Form(""),
    db: Session = Depends(get_db),
):
    Repository(db).add_award(
        profile_id=profile_id,
        title=title,
        issuer=issuer,
        award_year=award_year,
        details=details,
    )
    return RedirectResponse(url=f"/profiles/{profile_id}", status_code=303)


@router.post("/web/profiles/{profile_id}/conference")
def add_conference(
    profile_id: int,
    name: str = Form(...),
    event_year: int = Form(0),
    role: str = Form(""),
    details: str = Form(""),
    db: Session = Depends(get_db),
):
    Repository(db).add_conference(
        profile_id=profile_id,
        name=name,
        event_year=event_year,
        role=role,
        details=details,
    )
    return RedirectResponse(url=f"/profiles/{profile_id}", status_code=303)


@router.post("/web/profiles/{profile_id}/teaching")
def add_teaching(
    profile_id: int,
    role: str = Form(...),
    organization: str = Form(""),
    term: str = Form(""),
    details: str = Form(""),
    db: Session = Depends(get_db),
):
    Repository(db).add_teaching(
        profile_id=profile_id,
        role=role,
        organization=organization,
        term=term,
        details=details,
    )
    return RedirectResponse(url=f"/profiles/{profile_id}", status_code=303)


@router.post("/web/profiles/{profile_id}/service")
def add_service(
    profile_id: int,
    role: str = Form(""),
    organization: str = Form(""),
    event_name: str = Form(""),
    event_year: int = Form(0),
    details: str = Form(""),
    db: Session = Depends(get_db),
):
    Repository(db).add_service(
        profile_id=profile_id,
        role=role,
        organization=organization,
        event_name=event_name,
        event_year=event_year,
        details=details,
    )
    return RedirectResponse(url=f"/profiles/{profile_id}", status_code=303)


@router.post("/web/profiles/{profile_id}/additional-project")
def add_additional_project(
    profile_id: int,
    title: str = Form(...),
    summary: str = Form(""),
    skills_csv: str = Form(""),
    impact: str = Form(""),
    db: Session = Depends(get_db),
):
    skills_json = [item.strip() for item in skills_csv.split(",") if item.strip()]
    Repository(db).add_additional_project(
        profile_id=profile_id,
        title=title,
        summary=summary,
        skills_json=skills_json,
        impact=impact,
    )
    return RedirectResponse(url=f"/profiles/{profile_id}", status_code=303)


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
            request,
            "not_found.html",
            {"message": "Run not found"},
            status_code=404,
        )

    events = repo.list_run_events(run_id)
    pending = repo.get_pending_approval_events(run_id)
    job = repo.get_job(run.job_id)
    profile = repo.get_profile(run.profile_id)

    return templates.TemplateResponse(
        request,
        "run_detail.html",
        {
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
