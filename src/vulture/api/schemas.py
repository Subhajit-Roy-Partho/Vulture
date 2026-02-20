from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, Field


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


class CVImportAPIRequest(BaseModel):
    raw_text: str
    format: Literal["latex", "text"] = "latex"
    scope: Literal["all", "hiring_core", "research_core"] = "all"
    create_questions: bool = True


class CVImportAPIResponse(BaseModel):
    imported_sections: dict[str, int]
    created_questions: int
    created_answers: int
    warnings: list[str] = Field(default_factory=list)


class QuestionnaireItemResponse(BaseModel):
    question_hash: str
    question: str
    question_type: str
    tags: list[str]
    section: str
    importance: str
    is_cv_derived: bool
    answer: str
    verification_state: str
    source: str
    source_section: str


class QuestionnaireDecisionResponse(BaseModel):
    profile_id: int
    question_hash: str
    verification_state: str


class PublicationRequest(BaseModel):
    title: str
    venue: str = ""
    publication_year: int = 0
    status: str = ""
    doi: str = ""
    url: str = ""
    authors_json: list[str] = Field(default_factory=list)
    contribution: str = ""


class PublicationResponse(PublicationRequest):
    id: int


class AwardRequest(BaseModel):
    title: str
    issuer: str = ""
    award_year: int = 0
    details: str = ""


class AwardResponse(AwardRequest):
    id: int


class ConferenceRequest(BaseModel):
    name: str
    event_year: int = 0
    role: str = ""
    details: str = ""


class ConferenceResponse(ConferenceRequest):
    id: int


class TeachingRequest(BaseModel):
    role: str
    organization: str = ""
    term: str = ""
    details: str = ""


class TeachingResponse(TeachingRequest):
    id: int


class ServiceRequest(BaseModel):
    role: str = ""
    organization: str = ""
    event_name: str = ""
    event_year: int = 0
    details: str = ""


class ServiceResponse(ServiceRequest):
    id: int


class AdditionalProjectRequest(BaseModel):
    title: str
    summary: str = ""
    skills_json: list[str] = Field(default_factory=list)
    impact: str = ""


class AdditionalProjectResponse(AdditionalProjectRequest):
    id: int


class EducationRequest(BaseModel):
    institution: str
    degree: str
    field: str = ""
    gpa: str = ""
    thesis_title: str = ""
    advisor: str = ""
    lab: str = ""


class EducationResponse(EducationRequest):
    id: int


class ExperienceRequest(BaseModel):
    company: str
    title: str
    description: str = ""
    advisor: str = ""
    impact_summary: str = ""
    skills_json: list[str] = Field(default_factory=list)


class ExperienceResponse(ExperienceRequest):
    id: int


class SkillRequest(BaseModel):
    name: str
    category: str
    years: float = 0.0
    proficiency: str = ""
    last_used_year: int = 0


class SkillResponse(SkillRequest):
    id: int


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
