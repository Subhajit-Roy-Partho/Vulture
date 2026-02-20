from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, WebSocket, WebSocketDisconnect
from sqlalchemy.orm import Session

from vulture.api.deps import get_db
from vulture.api.schemas import (
    AdditionalProjectRequest,
    AdditionalProjectResponse,
    AwardRequest,
    AwardResponse,
    CVImportAPIRequest,
    CVImportAPIResponse,
    ConferenceRequest,
    ConferenceResponse,
    EducationRequest,
    EducationResponse,
    ExperienceRequest,
    ExperienceResponse,
    JobIntakeRequest,
    JobIntakeResponse,
    ProfileAnswerRequest,
    ProfileCreateRequest,
    ProfileResponse,
    PublicationRequest,
    PublicationResponse,
    QuestionnaireDecisionResponse,
    QuestionnaireItemResponse,
    RunCreateRequest,
    RunDecisionRequest,
    RunEventResponse,
    RunResponse,
    ServiceRequest,
    ServiceResponse,
    SkillRequest,
    SkillResponse,
    TeachingRequest,
    TeachingResponse,
)
from vulture.core.cv_parser import parse_cv_text
from vulture.core.job_fetcher import fetch_job_text
from vulture.core.orchestrator import RunOrchestrator
from vulture.core.question_templates import generate_question_templates
from vulture.core.runtime import get_event_bus
from vulture.db.repositories import Repository
from vulture.llm.router import LLMRouter

router = APIRouter(prefix="/api", tags=["api"])


@router.post("/profiles", response_model=ProfileResponse)
def create_profile(payload: ProfileCreateRequest, db: Session = Depends(get_db)) -> ProfileResponse:
    repo = Repository(db)
    profile = repo.create_profile(name=payload.name, job_family=payload.job_family, summary=payload.summary)
    return ProfileResponse(
        id=profile.id,
        name=profile.name,
        job_family=profile.job_family,
        summary=profile.summary,
        is_default=profile.is_default,
    )


@router.get("/profiles", response_model=list[ProfileResponse])
def list_profiles(db: Session = Depends(get_db)) -> list[ProfileResponse]:
    repo = Repository(db)
    rows = repo.list_profiles()
    return [
        ProfileResponse(
            id=row.id,
            name=row.name,
            job_family=row.job_family,
            summary=row.summary,
            is_default=row.is_default,
        )
        for row in rows
    ]


@router.post("/profiles/{profile_id}/answers")
def add_profile_answer(
    profile_id: int,
    payload: ProfileAnswerRequest,
    db: Session = Depends(get_db),
) -> dict:
    repo = Repository(db)
    if not repo.get_profile(profile_id):
        raise HTTPException(status_code=404, detail="Profile not found")

    answer = repo.add_profile_answer(
        profile_id=profile_id,
        question=payload.question,
        answer=payload.answer,
        question_type=payload.question_type,
    )
    return {"id": answer.id, "question_hash": answer.question_hash}


@router.post("/profiles/{profile_id}/cv/import", response_model=CVImportAPIResponse)
def import_cv(
    profile_id: int,
    payload: CVImportAPIRequest,
    db: Session = Depends(get_db),
) -> CVImportAPIResponse:
    repo = Repository(db)
    if not repo.get_profile(profile_id):
        raise HTTPException(status_code=404, detail="Profile not found")

    parsed = parse_cv_text(payload.raw_text, input_format=payload.format)
    templates = generate_question_templates(parsed, scope=payload.scope)
    if not payload.create_questions:
        templates = []

    result = repo.import_cv_payload(
        profile_id=profile_id,
        parsed=parsed,
        templates=templates,
        input_format=payload.format,
        scope=payload.scope,
    )
    return CVImportAPIResponse.model_validate(result.model_dump())


@router.get("/profiles/{profile_id}/questionnaire", response_model=list[QuestionnaireItemResponse])
def profile_questionnaire(profile_id: int, db: Session = Depends(get_db)) -> list[QuestionnaireItemResponse]:
    repo = Repository(db)
    if not repo.get_profile(profile_id):
        raise HTTPException(status_code=404, detail="Profile not found")
    return [QuestionnaireItemResponse.model_validate(item) for item in repo.list_profile_questionnaire(profile_id)]


@router.get(
    "/profiles/{profile_id}/questionnaire/review",
    response_model=list[QuestionnaireItemResponse],
)
def profile_questionnaire_review(
    profile_id: int,
    db: Session = Depends(get_db),
) -> list[QuestionnaireItemResponse]:
    repo = Repository(db)
    if not repo.get_profile(profile_id):
        raise HTTPException(status_code=404, detail="Profile not found")
    return [
        QuestionnaireItemResponse.model_validate(item)
        for item in repo.list_profile_questionnaire_review(profile_id)
    ]


@router.post(
    "/profiles/{profile_id}/questionnaire/{question_hash}/verify",
    response_model=QuestionnaireDecisionResponse,
)
def verify_question_answer(
    profile_id: int,
    question_hash: str,
    db: Session = Depends(get_db),
) -> QuestionnaireDecisionResponse:
    repo = Repository(db)
    try:
        repo.set_profile_answer_verification(profile_id, question_hash, "verified")
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    return QuestionnaireDecisionResponse(
        profile_id=profile_id,
        question_hash=question_hash,
        verification_state="verified",
    )


@router.post(
    "/profiles/{profile_id}/questionnaire/{question_hash}/reject",
    response_model=QuestionnaireDecisionResponse,
)
def reject_question_answer(
    profile_id: int,
    question_hash: str,
    db: Session = Depends(get_db),
) -> QuestionnaireDecisionResponse:
    repo = Repository(db)
    try:
        repo.set_profile_answer_verification(profile_id, question_hash, "rejected")
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    return QuestionnaireDecisionResponse(
        profile_id=profile_id,
        question_hash=question_hash,
        verification_state="rejected",
    )


@router.get("/profiles/{profile_id}/publications", response_model=list[PublicationResponse])
def list_publications(profile_id: int, db: Session = Depends(get_db)) -> list[PublicationResponse]:
    repo = Repository(db)
    rows = repo.list_publications(profile_id)
    return [
        PublicationResponse(
            id=row.id,
            title=row.title,
            venue=row.venue,
            publication_year=row.publication_year,
            status=row.status,
            doi=row.doi,
            url=row.url,
            authors_json=row.authors_json,
            contribution=row.contribution,
        )
        for row in rows
    ]


@router.post("/profiles/{profile_id}/publications", response_model=PublicationResponse)
def create_publication(
    profile_id: int,
    payload: PublicationRequest,
    db: Session = Depends(get_db),
) -> PublicationResponse:
    repo = Repository(db)
    row = repo.add_publication(profile_id=profile_id, **payload.model_dump())
    return PublicationResponse(id=row.id, **payload.model_dump())


@router.get("/profiles/{profile_id}/awards", response_model=list[AwardResponse])
def list_awards(profile_id: int, db: Session = Depends(get_db)) -> list[AwardResponse]:
    repo = Repository(db)
    rows = repo.list_awards(profile_id)
    return [AwardResponse(id=row.id, title=row.title, issuer=row.issuer, award_year=row.award_year, details=row.details) for row in rows]


@router.post("/profiles/{profile_id}/awards", response_model=AwardResponse)
def create_award(
    profile_id: int,
    payload: AwardRequest,
    db: Session = Depends(get_db),
) -> AwardResponse:
    repo = Repository(db)
    row = repo.add_award(profile_id=profile_id, **payload.model_dump())
    return AwardResponse(id=row.id, **payload.model_dump())


@router.get("/profiles/{profile_id}/conferences", response_model=list[ConferenceResponse])
def list_conferences(profile_id: int, db: Session = Depends(get_db)) -> list[ConferenceResponse]:
    repo = Repository(db)
    rows = repo.list_conferences(profile_id)
    return [ConferenceResponse(id=row.id, name=row.name, event_year=row.event_year, role=row.role, details=row.details) for row in rows]


@router.post("/profiles/{profile_id}/conferences", response_model=ConferenceResponse)
def create_conference(
    profile_id: int,
    payload: ConferenceRequest,
    db: Session = Depends(get_db),
) -> ConferenceResponse:
    repo = Repository(db)
    row = repo.add_conference(profile_id=profile_id, **payload.model_dump())
    return ConferenceResponse(id=row.id, **payload.model_dump())


@router.get("/profiles/{profile_id}/teaching", response_model=list[TeachingResponse])
def list_teaching(profile_id: int, db: Session = Depends(get_db)) -> list[TeachingResponse]:
    repo = Repository(db)
    rows = repo.list_teaching(profile_id)
    return [TeachingResponse(id=row.id, role=row.role, organization=row.organization, term=row.term, details=row.details) for row in rows]


@router.post("/profiles/{profile_id}/teaching", response_model=TeachingResponse)
def create_teaching(
    profile_id: int,
    payload: TeachingRequest,
    db: Session = Depends(get_db),
) -> TeachingResponse:
    repo = Repository(db)
    row = repo.add_teaching(profile_id=profile_id, **payload.model_dump())
    return TeachingResponse(id=row.id, **payload.model_dump())


@router.get("/profiles/{profile_id}/service", response_model=list[ServiceResponse])
def list_service(profile_id: int, db: Session = Depends(get_db)) -> list[ServiceResponse]:
    repo = Repository(db)
    rows = repo.list_service(profile_id)
    return [
        ServiceResponse(
            id=row.id,
            role=row.role,
            organization=row.organization,
            event_name=row.event_name,
            event_year=row.event_year,
            details=row.details,
        )
        for row in rows
    ]


@router.post("/profiles/{profile_id}/service", response_model=ServiceResponse)
def create_service(
    profile_id: int,
    payload: ServiceRequest,
    db: Session = Depends(get_db),
) -> ServiceResponse:
    repo = Repository(db)
    row = repo.add_service(profile_id=profile_id, **payload.model_dump())
    return ServiceResponse(id=row.id, **payload.model_dump())


@router.get(
    "/profiles/{profile_id}/additional-projects",
    response_model=list[AdditionalProjectResponse],
)
def list_additional_projects(
    profile_id: int,
    db: Session = Depends(get_db),
) -> list[AdditionalProjectResponse]:
    repo = Repository(db)
    rows = repo.list_additional_projects(profile_id)
    return [
        AdditionalProjectResponse(
            id=row.id,
            title=row.title,
            summary=row.summary,
            skills_json=row.skills_json,
            impact=row.impact,
        )
        for row in rows
    ]


@router.post(
    "/profiles/{profile_id}/additional-projects",
    response_model=AdditionalProjectResponse,
)
def create_additional_project(
    profile_id: int,
    payload: AdditionalProjectRequest,
    db: Session = Depends(get_db),
) -> AdditionalProjectResponse:
    repo = Repository(db)
    row = repo.add_additional_project(profile_id=profile_id, **payload.model_dump())
    return AdditionalProjectResponse(id=row.id, **payload.model_dump())


@router.get("/profiles/{profile_id}/educations", response_model=list[EducationResponse])
def list_educations(profile_id: int, db: Session = Depends(get_db)) -> list[EducationResponse]:
    repo = Repository(db)
    rows = repo.list_education(profile_id)
    return [
        EducationResponse(
            id=row.id,
            institution=row.institution,
            degree=row.degree,
            field=row.field,
            gpa=row.gpa,
            thesis_title=row.thesis_title,
            advisor=row.advisor,
            lab=row.lab,
        )
        for row in rows
    ]


@router.post("/profiles/{profile_id}/educations", response_model=EducationResponse)
def create_education(
    profile_id: int,
    payload: EducationRequest,
    db: Session = Depends(get_db),
) -> EducationResponse:
    repo = Repository(db)
    row = repo.add_education(profile_id=profile_id, **payload.model_dump())
    return EducationResponse(id=row.id, **payload.model_dump())


@router.get("/profiles/{profile_id}/experiences", response_model=list[ExperienceResponse])
def list_experiences(profile_id: int, db: Session = Depends(get_db)) -> list[ExperienceResponse]:
    repo = Repository(db)
    rows = repo.list_experiences(profile_id)
    return [
        ExperienceResponse(
            id=row.id,
            company=row.company,
            title=row.title,
            description=row.description,
            advisor=row.advisor,
            impact_summary=row.impact_summary,
            skills_json=row.skills_json,
        )
        for row in rows
    ]


@router.post("/profiles/{profile_id}/experiences", response_model=ExperienceResponse)
def create_experience(
    profile_id: int,
    payload: ExperienceRequest,
    db: Session = Depends(get_db),
) -> ExperienceResponse:
    repo = Repository(db)
    row = repo.add_experience(profile_id=profile_id, **payload.model_dump())
    return ExperienceResponse(id=row.id, **payload.model_dump())


@router.get("/profiles/{profile_id}/skills", response_model=list[SkillResponse])
def list_skills(profile_id: int, db: Session = Depends(get_db)) -> list[SkillResponse]:
    repo = Repository(db)
    rows = repo.list_skills(profile_id)
    return [
        SkillResponse(
            id=row.id,
            name=row.name,
            category=row.category,
            years=row.years,
            proficiency=row.proficiency,
            last_used_year=row.last_used_year,
        )
        for row in rows
    ]


@router.post("/profiles/{profile_id}/skills", response_model=SkillResponse)
def create_skill(
    profile_id: int,
    payload: SkillRequest,
    db: Session = Depends(get_db),
) -> SkillResponse:
    repo = Repository(db)
    row = repo.add_skill(profile_id=profile_id, **payload.model_dump())
    return SkillResponse(id=row.id, **payload.model_dump())


@router.post("/jobs/intake", response_model=JobIntakeResponse)
def intake_job(payload: JobIntakeRequest, db: Session = Depends(get_db)) -> JobIntakeResponse:
    repo = Repository(db)
    if not repo.get_profile(payload.profile_id):
        raise HTTPException(status_code=404, detail="Profile not found")

    job = repo.create_job(payload.url)
    jd_text = fetch_job_text(payload.url)
    analysis = LLMRouter().analyze_job(job_url=payload.url, job_text=jd_text)
    repo.update_job_analysis(job.id, analysis, jd_text)

    return JobIntakeResponse(
        job_id=job.id,
        title=analysis.title,
        company=analysis.company,
        location=analysis.location,
        requirements=analysis.requirements,
    )


@router.post("/runs", response_model=RunResponse)
def create_run(payload: RunCreateRequest, db: Session = Depends(get_db)) -> RunResponse:
    orchestrator = RunOrchestrator(db)
    try:
        run = orchestrator.start_application(
            url=payload.url,
            profile_id=payload.profile_id,
            mode=payload.mode,
            submit=payload.submit,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    return RunResponse.model_validate(run)


@router.get("/runs/{run_id}", response_model=RunResponse)
def get_run(run_id: int, db: Session = Depends(get_db)) -> RunResponse:
    orchestrator = RunOrchestrator(db)
    try:
        return RunResponse.model_validate(orchestrator.serialize_run(run_id))
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.post("/runs/{run_id}/approve", response_model=RunResponse)
def approve_run(
    run_id: int,
    payload: RunDecisionRequest,
    db: Session = Depends(get_db),
) -> RunResponse:
    orchestrator = RunOrchestrator(db)
    try:
        data = orchestrator.approve_event(run_id=run_id, event_id=payload.event_id)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    return RunResponse.model_validate(data)


@router.post("/runs/{run_id}/reject", response_model=RunResponse)
def reject_run(
    run_id: int,
    payload: RunDecisionRequest,
    db: Session = Depends(get_db),
) -> RunResponse:
    orchestrator = RunOrchestrator(db)
    try:
        data = orchestrator.reject_event(run_id=run_id, event_id=payload.event_id)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    return RunResponse.model_validate(data)


@router.get("/runs/{run_id}/events", response_model=list[RunEventResponse])
def get_run_events(run_id: int, db: Session = Depends(get_db)) -> list[RunEventResponse]:
    repo = Repository(db)
    if not repo.get_run(run_id):
        raise HTTPException(status_code=404, detail="Run not found")
    events = repo.list_run_events(run_id)
    return [
        RunEventResponse(
            id=row.id,
            run_id=row.run_id,
            stage=row.stage,
            action=row.action,
            payload_json=row.payload_json,
            requires_approval=row.requires_approval,
            approval_state=row.approval_state,
            created_at=row.created_at.isoformat() if row.created_at else None,
        )
        for row in events
    ]


@router.websocket("/runs/{run_id}/stream")
async def stream_run_events(websocket: WebSocket, run_id: int) -> None:
    await websocket.accept()
    event_bus = get_event_bus()
    try:
        async for event in event_bus.subscribe(run_id):
            await websocket.send_json(event)
    except WebSocketDisconnect:
        return
