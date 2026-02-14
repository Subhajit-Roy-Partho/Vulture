from __future__ import annotations

from datetime import date, datetime
from typing import Any

from sqlalchemy import (
    JSON,
    Boolean,
    Date,
    DateTime,
    Float,
    ForeignKey,
    Integer,
    LargeBinary,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column

from vulture.db.base import Base, TimestampMixin


class Profile(TimestampMixin, Base):
    __tablename__ = "profiles"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    job_family: Mapped[str] = mapped_column(String(255), nullable=False)
    summary: Mapped[str] = mapped_column(Text, default="", nullable=False)
    is_default: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)


class ProfilePersonal(TimestampMixin, Base):
    __tablename__ = "profile_personal"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    profile_id: Mapped[int] = mapped_column(ForeignKey("profiles.id", ondelete="CASCADE"), unique=True)
    first_name: Mapped[str] = mapped_column(String(120), default="", nullable=False)
    last_name: Mapped[str] = mapped_column(String(120), default="", nullable=False)
    email: Mapped[str] = mapped_column(String(255), default="", nullable=False)
    phone_e164: Mapped[str] = mapped_column(String(40), default="", nullable=False)
    headline: Mapped[str] = mapped_column(String(255), default="", nullable=False)
    current_company: Mapped[str] = mapped_column(String(255), default="", nullable=False)


class ProfileAddress(TimestampMixin, Base):
    __tablename__ = "profile_addresses"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    profile_id: Mapped[int] = mapped_column(ForeignKey("profiles.id", ondelete="CASCADE"), index=True)
    line1: Mapped[str] = mapped_column(String(255), default="", nullable=False)
    line2: Mapped[str] = mapped_column(String(255), default="", nullable=False)
    city: Mapped[str] = mapped_column(String(120), default="", nullable=False)
    state: Mapped[str] = mapped_column(String(120), default="", nullable=False)
    postal_code: Mapped[str] = mapped_column(String(30), default="", nullable=False)
    country: Mapped[str] = mapped_column(String(120), default="", nullable=False)
    is_primary: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)


class ProfileLink(TimestampMixin, Base):
    __tablename__ = "profile_links"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    profile_id: Mapped[int] = mapped_column(ForeignKey("profiles.id", ondelete="CASCADE"), index=True)
    type: Mapped[str] = mapped_column(String(80), default="", nullable=False)
    url: Mapped[str] = mapped_column(String(500), default="", nullable=False)
    label: Mapped[str] = mapped_column(String(120), default="", nullable=False)


class ProfileWorkAuth(TimestampMixin, Base):
    __tablename__ = "profile_work_auth"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    profile_id: Mapped[int] = mapped_column(ForeignKey("profiles.id", ondelete="CASCADE"), unique=True)
    authorized_countries_json: Mapped[list[str]] = mapped_column(JSON, default=list, nullable=False)
    needs_sponsorship: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    visa_status: Mapped[str] = mapped_column(String(120), default="", nullable=False)
    clearance_level: Mapped[str] = mapped_column(String(120), default="", nullable=False)


class ProfilePreference(TimestampMixin, Base):
    __tablename__ = "profile_preferences"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    profile_id: Mapped[int] = mapped_column(ForeignKey("profiles.id", ondelete="CASCADE"), unique=True)
    employment_types_json: Mapped[list[str]] = mapped_column(JSON, default=list, nullable=False)
    remote_pref: Mapped[str] = mapped_column(String(120), default="", nullable=False)
    relocation_pref: Mapped[str] = mapped_column(String(120), default="", nullable=False)
    travel_pct: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    notice_period_days: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    salary_currency: Mapped[str] = mapped_column(String(10), default="USD", nullable=False)
    salary_min: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    salary_max: Mapped[int] = mapped_column(Integer, default=0, nullable=False)


class Experience(TimestampMixin, Base):
    __tablename__ = "experiences"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    profile_id: Mapped[int] = mapped_column(ForeignKey("profiles.id", ondelete="CASCADE"), index=True)
    company: Mapped[str] = mapped_column(String(255), nullable=False)
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    location: Mapped[str] = mapped_column(String(255), default="", nullable=False)
    start_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    end_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    is_current: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    description: Mapped[str] = mapped_column(Text, default="", nullable=False)
    advisor: Mapped[str] = mapped_column(String(255), default="", nullable=False)
    skills_json: Mapped[list[str]] = mapped_column(JSON, default=list, nullable=False)
    impact_summary: Mapped[str] = mapped_column(Text, default="", nullable=False)


class ExperienceBullet(TimestampMixin, Base):
    __tablename__ = "experience_bullets"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    experience_id: Mapped[int] = mapped_column(
        ForeignKey("experiences.id", ondelete="CASCADE"), index=True
    )
    bullet: Mapped[str] = mapped_column(Text, nullable=False)
    impact_metric: Mapped[str] = mapped_column(String(255), default="", nullable=False)
    sort_order: Mapped[int] = mapped_column(Integer, default=0, nullable=False)


class Education(TimestampMixin, Base):
    __tablename__ = "educations"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    profile_id: Mapped[int] = mapped_column(ForeignKey("profiles.id", ondelete="CASCADE"), index=True)
    institution: Mapped[str] = mapped_column(String(255), nullable=False)
    degree: Mapped[str] = mapped_column(String(255), default="", nullable=False)
    field: Mapped[str] = mapped_column(String(255), default="", nullable=False)
    start_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    end_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    gpa: Mapped[str] = mapped_column(String(20), default="", nullable=False)
    honors: Mapped[str] = mapped_column(String(255), default="", nullable=False)
    thesis_title: Mapped[str] = mapped_column(Text, default="", nullable=False)
    advisor: Mapped[str] = mapped_column(String(255), default="", nullable=False)
    lab: Mapped[str] = mapped_column(String(255), default="", nullable=False)


class Certification(TimestampMixin, Base):
    __tablename__ = "certifications"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    profile_id: Mapped[int] = mapped_column(ForeignKey("profiles.id", ondelete="CASCADE"), index=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    issuer: Mapped[str] = mapped_column(String(255), default="", nullable=False)
    credential_id: Mapped[str] = mapped_column(String(255), default="", nullable=False)
    issue_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    expiry_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    url: Mapped[str] = mapped_column(String(500), default="", nullable=False)


class Project(TimestampMixin, Base):
    __tablename__ = "projects"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    profile_id: Mapped[int] = mapped_column(ForeignKey("profiles.id", ondelete="CASCADE"), index=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    role: Mapped[str] = mapped_column(String(255), default="", nullable=False)
    description: Mapped[str] = mapped_column(Text, default="", nullable=False)
    tech_stack_json: Mapped[list[str]] = mapped_column(JSON, default=list, nullable=False)
    url: Mapped[str] = mapped_column(String(500), default="", nullable=False)
    start_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    end_date: Mapped[date | None] = mapped_column(Date, nullable=True)


class Skill(TimestampMixin, Base):
    __tablename__ = "skills"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    profile_id: Mapped[int] = mapped_column(ForeignKey("profiles.id", ondelete="CASCADE"), index=True)
    name: Mapped[str] = mapped_column(String(120), nullable=False)
    category: Mapped[str] = mapped_column(String(120), default="", nullable=False)
    years: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
    proficiency: Mapped[str] = mapped_column(String(80), default="", nullable=False)
    last_used_year: Mapped[int] = mapped_column(Integer, default=0, nullable=False)


class Language(TimestampMixin, Base):
    __tablename__ = "languages"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    profile_id: Mapped[int] = mapped_column(ForeignKey("profiles.id", ondelete="CASCADE"), index=True)
    language: Mapped[str] = mapped_column(String(120), nullable=False)
    proficiency: Mapped[str] = mapped_column(String(80), default="", nullable=False)


class ProfileReference(TimestampMixin, Base):
    __tablename__ = "references"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    profile_id: Mapped[int] = mapped_column(ForeignKey("profiles.id", ondelete="CASCADE"), index=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    relationship: Mapped[str] = mapped_column(String(255), default="", nullable=False)
    email: Mapped[str] = mapped_column(String(255), default="", nullable=False)
    phone: Mapped[str] = mapped_column(String(50), default="", nullable=False)
    company: Mapped[str] = mapped_column(String(255), default="", nullable=False)


class ProfileDocument(TimestampMixin, Base):
    __tablename__ = "profile_documents"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    profile_id: Mapped[int] = mapped_column(ForeignKey("profiles.id", ondelete="CASCADE"), index=True)
    doc_type: Mapped[str] = mapped_column(String(80), nullable=False)
    file_path: Mapped[str] = mapped_column(String(600), nullable=False)
    mime_type: Mapped[str] = mapped_column(String(120), default="", nullable=False)
    version: Mapped[str] = mapped_column(String(80), default="v1", nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)


class Publication(TimestampMixin, Base):
    __tablename__ = "publications"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    profile_id: Mapped[int] = mapped_column(ForeignKey("profiles.id", ondelete="CASCADE"), index=True)
    title: Mapped[str] = mapped_column(Text, nullable=False)
    venue: Mapped[str] = mapped_column(String(255), default="", nullable=False)
    publication_year: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    status: Mapped[str] = mapped_column(String(80), default="", nullable=False)
    doi: Mapped[str] = mapped_column(String(255), default="", nullable=False)
    url: Mapped[str] = mapped_column(String(800), default="", nullable=False)
    authors_json: Mapped[list[str]] = mapped_column(JSON, default=list, nullable=False)
    contribution: Mapped[str] = mapped_column(Text, default="", nullable=False)


class AwardHonor(TimestampMixin, Base):
    __tablename__ = "awards_honors"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    profile_id: Mapped[int] = mapped_column(ForeignKey("profiles.id", ondelete="CASCADE"), index=True)
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    issuer: Mapped[str] = mapped_column(String(255), default="", nullable=False)
    award_year: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    details: Mapped[str] = mapped_column(Text, default="", nullable=False)


class ConferencePresentation(TimestampMixin, Base):
    __tablename__ = "conference_presentations"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    profile_id: Mapped[int] = mapped_column(ForeignKey("profiles.id", ondelete="CASCADE"), index=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    event_year: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    role: Mapped[str] = mapped_column(String(120), default="", nullable=False)
    details: Mapped[str] = mapped_column(Text, default="", nullable=False)


class TeachingMentoring(TimestampMixin, Base):
    __tablename__ = "teaching_mentoring"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    profile_id: Mapped[int] = mapped_column(ForeignKey("profiles.id", ondelete="CASCADE"), index=True)
    role: Mapped[str] = mapped_column(String(255), nullable=False)
    organization: Mapped[str] = mapped_column(String(255), default="", nullable=False)
    term: Mapped[str] = mapped_column(String(120), default="", nullable=False)
    start_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    end_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    details: Mapped[str] = mapped_column(Text, default="", nullable=False)


class ServiceOutreach(TimestampMixin, Base):
    __tablename__ = "service_outreach"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    profile_id: Mapped[int] = mapped_column(ForeignKey("profiles.id", ondelete="CASCADE"), index=True)
    role: Mapped[str] = mapped_column(String(255), default="", nullable=False)
    organization: Mapped[str] = mapped_column(String(255), default="", nullable=False)
    event_name: Mapped[str] = mapped_column(String(255), default="", nullable=False)
    event_year: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    details: Mapped[str] = mapped_column(Text, default="", nullable=False)


class AdditionalProject(TimestampMixin, Base):
    __tablename__ = "additional_projects"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    profile_id: Mapped[int] = mapped_column(ForeignKey("profiles.id", ondelete="CASCADE"), index=True)
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    summary: Mapped[str] = mapped_column(Text, default="", nullable=False)
    skills_json: Mapped[list[str]] = mapped_column(JSON, default=list, nullable=False)
    impact: Mapped[str] = mapped_column(Text, default="", nullable=False)


class CVImportRun(TimestampMixin, Base):
    __tablename__ = "cv_import_runs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    profile_id: Mapped[int] = mapped_column(ForeignKey("profiles.id", ondelete="CASCADE"), index=True)
    input_format: Mapped[str] = mapped_column(String(40), default="latex", nullable=False)
    scope: Mapped[str] = mapped_column(String(40), default="all", nullable=False)
    status: Mapped[str] = mapped_column(String(40), default="created", nullable=False)
    warnings_json: Mapped[list[str]] = mapped_column(JSON, default=list, nullable=False)
    raw_text_hash: Mapped[str] = mapped_column(String(64), default="", nullable=False)


class CVImportItem(TimestampMixin, Base):
    __tablename__ = "cv_import_items"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    import_run_id: Mapped[int] = mapped_column(
        ForeignKey("cv_import_runs.id", ondelete="CASCADE"), index=True
    )
    profile_id: Mapped[int] = mapped_column(ForeignKey("profiles.id", ondelete="CASCADE"), index=True)
    section: Mapped[str] = mapped_column(String(120), nullable=False)
    item_key: Mapped[str] = mapped_column(String(255), default="", nullable=False)
    payload_json: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict, nullable=False)
    created_question_hash: Mapped[str] = mapped_column(String(64), default="", nullable=False)


class Job(TimestampMixin, Base):
    __tablename__ = "jobs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    url: Mapped[str] = mapped_column(String(800), nullable=False)
    domain: Mapped[str] = mapped_column(String(255), default="", nullable=False)
    company: Mapped[str] = mapped_column(String(255), default="", nullable=False)
    title: Mapped[str] = mapped_column(String(255), default="", nullable=False)
    location: Mapped[str] = mapped_column(String(255), default="", nullable=False)
    jd_text: Mapped[str] = mapped_column(Text, default="", nullable=False)
    jd_hash: Mapped[str] = mapped_column(String(64), default="", nullable=False)


class JobRequirement(TimestampMixin, Base):
    __tablename__ = "job_requirements"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    job_id: Mapped[int] = mapped_column(ForeignKey("jobs.id", ondelete="CASCADE"), index=True)
    kind: Mapped[str] = mapped_column(String(80), nullable=False)
    value: Mapped[str] = mapped_column(Text, nullable=False)
    priority: Mapped[str] = mapped_column(String(50), default="medium", nullable=False)
    source_quote: Mapped[str] = mapped_column(Text, default="", nullable=False)


class QuestionBank(TimestampMixin, Base):
    __tablename__ = "question_bank"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    question_hash: Mapped[str] = mapped_column(String(64), unique=True, index=True)
    canonical_text: Mapped[str] = mapped_column(Text, nullable=False)
    question_type: Mapped[str] = mapped_column(String(80), default="custom", nullable=False)
    options_json: Mapped[list[str]] = mapped_column(JSON, default=list, nullable=False)
    tags_json: Mapped[list[str]] = mapped_column(JSON, default=list, nullable=False)
    section: Mapped[str] = mapped_column(String(120), default="general", nullable=False)
    importance: Mapped[str] = mapped_column(String(20), default="medium", nullable=False)
    is_cv_derived: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)


class Attachment(TimestampMixin, Base):
    __tablename__ = "attachments"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    profile_id: Mapped[int] = mapped_column(ForeignKey("profiles.id", ondelete="CASCADE"), index=True)
    kind: Mapped[str] = mapped_column(String(80), nullable=False)
    file_path: Mapped[str] = mapped_column(String(600), nullable=False)
    checksum: Mapped[str] = mapped_column(String(128), default="", nullable=False)
    mime_type: Mapped[str] = mapped_column(String(120), default="", nullable=False)
    size_bytes: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    blob: Mapped[bytes | None] = mapped_column(LargeBinary, nullable=True)


class ProfileAnswer(TimestampMixin, Base):
    __tablename__ = "profile_answers"
    __table_args__ = (UniqueConstraint("profile_id", "question_hash", name="uq_profile_answer"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    profile_id: Mapped[int] = mapped_column(ForeignKey("profiles.id", ondelete="CASCADE"), index=True)
    question_hash: Mapped[str] = mapped_column(String(64), index=True)
    answer_text: Mapped[str] = mapped_column(Text, default="", nullable=False)
    answer_json: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict, nullable=False)
    attachment_id: Mapped[int | None] = mapped_column(ForeignKey("attachments.id", ondelete="SET NULL"))
    confidence: Mapped[float] = mapped_column(Float, default=1.0, nullable=False)
    verified: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    source: Mapped[str] = mapped_column(String(120), default="manual", nullable=False)
    verification_state: Mapped[str] = mapped_column(String(40), default="verified", nullable=False)
    source_section: Mapped[str] = mapped_column(String(120), default="general", nullable=False)
    evidence_json: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict, nullable=False)


class ComplianceDemographics(TimestampMixin, Base):
    __tablename__ = "compliance_demographics"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    profile_id: Mapped[int] = mapped_column(ForeignKey("profiles.id", ondelete="CASCADE"), unique=True)
    gender: Mapped[str] = mapped_column(String(120), default="", nullable=False)
    ethnicity: Mapped[str] = mapped_column(String(120), default="", nullable=False)
    race_categories_json: Mapped[list[str]] = mapped_column(JSON, default=list, nullable=False)
    veteran_status: Mapped[str] = mapped_column(String(120), default="", nullable=False)
    disability_status: Mapped[str] = mapped_column(String(120), default="", nullable=False)


class ComplianceConsent(TimestampMixin, Base):
    __tablename__ = "compliance_consents"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    profile_id: Mapped[int] = mapped_column(ForeignKey("profiles.id", ondelete="CASCADE"), index=True)
    consent_type: Mapped[str] = mapped_column(String(120), nullable=False)
    consent_value: Mapped[str] = mapped_column(String(120), nullable=False)
    consent_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    jurisdiction: Mapped[str] = mapped_column(String(120), default="", nullable=False)
    source: Mapped[str] = mapped_column(String(120), default="", nullable=False)


class RunSession(TimestampMixin, Base):
    __tablename__ = "run_sessions"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    job_id: Mapped[int] = mapped_column(ForeignKey("jobs.id", ondelete="CASCADE"), index=True)
    profile_id: Mapped[int] = mapped_column(ForeignKey("profiles.id", ondelete="CASCADE"), index=True)
    mode: Mapped[str] = mapped_column(String(20), nullable=False)
    status: Mapped[str] = mapped_column(String(40), default="created", nullable=False)
    current_stage: Mapped[str] = mapped_column(String(80), default="job_parse", nullable=False)
    context_json: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict, nullable=False)
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    submission_url: Mapped[str] = mapped_column(String(800), default="", nullable=False)
    error: Mapped[str] = mapped_column(Text, default="", nullable=False)


class AIPatchSuggestion(TimestampMixin, Base):
    __tablename__ = "ai_patch_suggestions"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    run_id: Mapped[int] = mapped_column(ForeignKey("run_sessions.id", ondelete="CASCADE"), index=True)
    provider: Mapped[str] = mapped_column(String(80), nullable=False)
    rationale: Mapped[str] = mapped_column(Text, default="", nullable=False)
    patch_json: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict, nullable=False)
    confidence: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
    status: Mapped[str] = mapped_column(String(40), default="suggested", nullable=False)


class RunEvent(TimestampMixin, Base):
    __tablename__ = "run_events"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    run_id: Mapped[int] = mapped_column(ForeignKey("run_sessions.id", ondelete="CASCADE"), index=True)
    stage: Mapped[str] = mapped_column(String(80), nullable=False)
    action: Mapped[str] = mapped_column(String(120), nullable=False)
    payload_json: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict, nullable=False)
    requires_approval: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    approval_state: Mapped[str] = mapped_column(String(40), default="not_required", nullable=False)


class FieldFillResult(TimestampMixin, Base):
    __tablename__ = "field_fill_results"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    run_id: Mapped[int] = mapped_column(ForeignKey("run_sessions.id", ondelete="CASCADE"), index=True)
    page_url: Mapped[str] = mapped_column(String(800), default="", nullable=False)
    field_key: Mapped[str] = mapped_column(String(255), nullable=False)
    locator: Mapped[str] = mapped_column(String(255), default="", nullable=False)
    value_source: Mapped[str] = mapped_column(String(255), default="", nullable=False)
    fill_status: Mapped[str] = mapped_column(String(60), default="filled", nullable=False)
    confidence: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)


class ResumeVersion(TimestampMixin, Base):
    __tablename__ = "resume_versions"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    profile_id: Mapped[int] = mapped_column(ForeignKey("profiles.id", ondelete="CASCADE"), index=True)
    job_id: Mapped[int] = mapped_column(ForeignKey("jobs.id", ondelete="CASCADE"), index=True)
    file_path: Mapped[str] = mapped_column(String(600), nullable=False)
    markdown_snapshot: Mapped[str] = mapped_column(Text, default="", nullable=False)
    llm_metadata_json: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict, nullable=False)


class CoverLetterVersion(TimestampMixin, Base):
    __tablename__ = "cover_letter_versions"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    profile_id: Mapped[int] = mapped_column(ForeignKey("profiles.id", ondelete="CASCADE"), index=True)
    job_id: Mapped[int] = mapped_column(ForeignKey("jobs.id", ondelete="CASCADE"), index=True)
    file_path: Mapped[str] = mapped_column(String(600), nullable=False)
    markdown_snapshot: Mapped[str] = mapped_column(Text, default="", nullable=False)
    llm_metadata_json: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict, nullable=False)


class ApplicationSubmission(TimestampMixin, Base):
    __tablename__ = "application_submissions"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    run_id: Mapped[int] = mapped_column(ForeignKey("run_sessions.id", ondelete="CASCADE"), index=True)
    submitted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    confirmation_text: Mapped[str] = mapped_column(Text, default="", nullable=False)
    confirmation_ref: Mapped[str] = mapped_column(String(120), default="", nullable=False)
    screenshot_path: Mapped[str] = mapped_column(String(600), default="", nullable=False)
