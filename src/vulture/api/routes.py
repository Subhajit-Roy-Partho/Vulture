from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, WebSocket, WebSocketDisconnect
from sqlalchemy.orm import Session

from vulture.api.deps import get_db
from vulture.api.schemas import (
    JobIntakeRequest,
    JobIntakeResponse,
    ProfileAnswerRequest,
    ProfileCreateRequest,
    ProfileResponse,
    RunCreateRequest,
    RunDecisionRequest,
    RunEventResponse,
    RunResponse,
)
from vulture.core.job_fetcher import fetch_job_text
from vulture.core.orchestrator import RunOrchestrator
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
