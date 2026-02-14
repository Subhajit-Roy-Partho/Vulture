from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel


class ProfileCreateRequest(BaseModel):
    name: str
    job_family: str
    summary: str = ""


class ProfileResponse(BaseModel):
    id: int
    name: str
    job_family: str
    summary: str
    is_default: bool


class ProfileAnswerRequest(BaseModel):
    question: str
    answer: str
    question_type: str = "custom"


class JobIntakeRequest(BaseModel):
    url: str
    profile_id: int
    mode: Literal["strict", "medium", "yolo"] = "medium"


class JobIntakeResponse(BaseModel):
    job_id: int
    title: str
    company: str
    location: str
    requirements: list[str]


class RunCreateRequest(BaseModel):
    url: str
    profile_id: int
    mode: Literal["strict", "medium", "yolo"] = "medium"
    submit: bool = False


class RunDecisionRequest(BaseModel):
    event_id: int


class RunResponse(BaseModel):
    id: int
    job_id: int
    profile_id: int
    mode: str
    status: str
    current_stage: str
    context: dict[str, Any]
    submission_url: str
    error: str
    started_at: str | None
    completed_at: str | None


class RunEventResponse(BaseModel):
    id: int
    run_id: int
    stage: str
    action: str
    payload_json: dict[str, Any]
    requires_approval: bool
    approval_state: str
    created_at: str | None
