from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, Field, field_validator

RunMode = Literal["strict", "medium", "yolo"]
LLMProvider = Literal["openai", "local"]
QuestionType = Literal[
    "short_text",
    "long_text",
    "boolean",
    "single_select",
    "multi_select",
    "date",
    "number",
    "email",
    "phone",
    "url",
    "file",
    "address",
    "salary",
    "work_auth",
    "eeo",
    "veteran",
    "disability",
    "publication",
    "award",
    "conference",
    "teaching",
    "service",
    "research",
    "project_metric",
    "custom",
]
AnswerVerificationState = Literal["verified", "needs_review", "rejected"]


class JobIntakeRequest(BaseModel):
    url: str
    profile_id: int
    mode: RunMode


class JobAnalysis(BaseModel):
    title: str = ""
    company: str = ""
    location: str = ""
    responsibilities: list[str] = Field(default_factory=list)
    requirements: list[str] = Field(default_factory=list)
    compensation: str = ""
    keywords: list[str] = Field(default_factory=list)


class PatchOperation(BaseModel):
    table: str
    operation: Literal["insert", "update", "upsert"]
    key: dict[str, Any] = Field(default_factory=dict)
    values: dict[str, Any] = Field(default_factory=dict)
    source: str = "llm"
    confidence: float = 0.0

    @field_validator("confidence")
    @classmethod
    def validate_confidence(cls, value: float) -> float:
        if value < 0 or value > 1:
            raise ValueError("confidence must be between 0 and 1")
        return value


class ProfilePatchBundle(BaseModel):
    rationale: str = ""
    operations: list[PatchOperation] = Field(default_factory=list)
    confidence: float = 0.0

    @field_validator("confidence")
    @classmethod
    def validate_confidence(cls, value: float) -> float:
        if value < 0 or value > 1:
            raise ValueError("confidence must be between 0 and 1")
        return value


class FieldFillPlan(BaseModel):
    field_key: str
    locator: str = ""
    value_source: str = ""
    confidence: float = 0.0


class RunEventPayload(BaseModel):
    stage: str
    action: str
    payload: dict[str, Any] = Field(default_factory=dict)
    requires_approval: bool = False
    status: Literal["logged", "pending", "approved", "rejected", "error"] = "logged"


class TailoredDocuments(BaseModel):
    resume_markdown: str
    cover_letter_markdown: str
    metadata: dict[str, Any] = Field(default_factory=dict)


class BrowserFillResult(BaseModel):
    status: Literal["completed", "waiting_approval", "waiting_captcha", "failed", "blocked"]
    stage: str = ""
    action: str = ""
    message: str = ""
    fields: list[FieldFillPlan] = Field(default_factory=list)


class ModelResponse(BaseModel):
    content: str
    raw: dict[str, Any] = Field(default_factory=dict)


class CVImportRequest(BaseModel):
    profile_id: int
    raw_text: str
    format: Literal["latex", "text"] = "latex"
    scope: Literal["all", "hiring_core", "research_core"] = "all"
    create_questions: bool = True


class QuestionTemplate(BaseModel):
    canonical_text: str
    question_type: QuestionType = "custom"
    tags: list[str] = Field(default_factory=list)
    suggested_answer: str = ""
    source_section: str = "general"
    importance: Literal["low", "medium", "high"] = "medium"


class CVImportResult(BaseModel):
    imported_sections: dict[str, int] = Field(default_factory=dict)
    created_questions: int = 0
    created_answers: int = 0
    warnings: list[str] = Field(default_factory=list)
