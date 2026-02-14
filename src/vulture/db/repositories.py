from __future__ import annotations

import hashlib
from datetime import UTC, datetime
from urllib.parse import urlparse

from sqlalchemy import and_, delete, select
from sqlalchemy.orm import Session

from vulture.db.models import (
    AIPatchSuggestion,
    ApplicationSubmission,
    CoverLetterVersion,
    FieldFillResult,
    Job,
    JobRequirement,
    Profile,
    ProfileAnswer,
    ProfilePersonal,
    ProfilePreference,
    ProfileWorkAuth,
    QuestionBank,
    ResumeVersion,
    RunEvent,
    RunSession,
    Skill,
)
from vulture.types import FieldFillPlan, JobAnalysis, PatchOperation


def canonicalize_question(question: str) -> str:
    return " ".join(question.strip().lower().split())


def hash_question(question: str) -> str:
    return hashlib.sha256(canonicalize_question(question).encode("utf-8")).hexdigest()


def hash_text(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


class Repository:
    def __init__(self, session: Session):
        self.session = session

    def create_profile(self, name: str, job_family: str, summary: str = "") -> Profile:
        profile = Profile(name=name, job_family=job_family, summary=summary)
        self.session.add(profile)
        self.session.commit()
        self.session.refresh(profile)
        return profile

    def list_profiles(self) -> list[Profile]:
        return list(self.session.scalars(select(Profile).order_by(Profile.id.desc())).all())

    def get_profile(self, profile_id: int) -> Profile | None:
        return self.session.get(Profile, profile_id)

    def create_or_update_profile_personal(self, profile_id: int, values: dict) -> ProfilePersonal:
        existing = self.session.scalar(
            select(ProfilePersonal).where(ProfilePersonal.profile_id == profile_id)
        )
        if existing:
            for key, value in values.items():
                setattr(existing, key, value)
            obj = existing
        else:
            obj = ProfilePersonal(profile_id=profile_id, **values)
            self.session.add(obj)

        self.session.commit()
        self.session.refresh(obj)
        return obj

    def create_job(self, url: str) -> Job:
        parsed = urlparse(url)
        job = Job(url=url, domain=parsed.netloc)
        self.session.add(job)
        self.session.commit()
        self.session.refresh(job)
        return job

    def get_job(self, job_id: int) -> Job | None:
        return self.session.get(Job, job_id)

    def list_jobs(self, limit: int = 50) -> list[Job]:
        statement = select(Job).order_by(Job.created_at.desc()).limit(limit)
        return list(self.session.scalars(statement).all())

    def update_job_analysis(self, job_id: int, analysis: JobAnalysis, jd_text: str) -> Job:
        job = self.session.get(Job, job_id)
        if not job:
            raise ValueError(f"job {job_id} not found")

        job.title = analysis.title
        job.company = analysis.company
        job.location = analysis.location
        job.jd_text = jd_text
        job.jd_hash = hash_text(jd_text)

        self.session.execute(delete(JobRequirement).where(JobRequirement.job_id == job_id))
        for item in analysis.requirements:
            self.session.add(
                JobRequirement(
                    job_id=job_id,
                    kind="requirement",
                    value=item,
                    priority="high",
                    source_quote=item,
                )
            )
        for item in analysis.responsibilities:
            self.session.add(
                JobRequirement(
                    job_id=job_id,
                    kind="responsibility",
                    value=item,
                    priority="medium",
                    source_quote=item,
                )
            )

        self.session.commit()
        self.session.refresh(job)
        return job

    def create_run(
        self,
        *,
        job_id: int,
        profile_id: int,
        mode: str,
        current_stage: str = "job_parse",
        status: str = "created",
        context_json: dict | None = None,
    ) -> RunSession:
        run = RunSession(
            job_id=job_id,
            profile_id=profile_id,
            mode=mode,
            status=status,
            current_stage=current_stage,
            context_json=context_json or {},
            started_at=datetime.now(UTC),
        )
        self.session.add(run)
        self.session.commit()
        self.session.refresh(run)
        return run

    def get_run(self, run_id: int) -> RunSession | None:
        return self.session.get(RunSession, run_id)

    def list_runs(self, limit: int = 50) -> list[RunSession]:
        statement = select(RunSession).order_by(RunSession.started_at.desc()).limit(limit)
        return list(self.session.scalars(statement).all())

    def update_run(
        self,
        run_id: int,
        *,
        status: str | None = None,
        current_stage: str | None = None,
        context_json: dict | None = None,
        error: str | None = None,
        submission_url: str | None = None,
        completed: bool = False,
    ) -> RunSession:
        run = self.session.get(RunSession, run_id)
        if not run:
            raise ValueError(f"run {run_id} not found")

        if status is not None:
            run.status = status
        if current_stage is not None:
            run.current_stage = current_stage
        if context_json is not None:
            run.context_json = context_json
        if error is not None:
            run.error = error
        if submission_url is not None:
            run.submission_url = submission_url
        if completed:
            run.completed_at = datetime.now(UTC)

        self.session.commit()
        self.session.refresh(run)
        return run

    def append_run_event(
        self,
        *,
        run_id: int,
        stage: str,
        action: str,
        payload_json: dict | None = None,
        requires_approval: bool = False,
        approval_state: str = "not_required",
    ) -> RunEvent:
        event = RunEvent(
            run_id=run_id,
            stage=stage,
            action=action,
            payload_json=payload_json or {},
            requires_approval=requires_approval,
            approval_state=approval_state,
        )
        self.session.add(event)
        self.session.commit()
        self.session.refresh(event)
        return event

    def list_run_events(self, run_id: int) -> list[RunEvent]:
        statement = select(RunEvent).where(RunEvent.run_id == run_id).order_by(RunEvent.id.asc())
        return list(self.session.scalars(statement).all())

    def get_run_event(self, event_id: int) -> RunEvent | None:
        return self.session.get(RunEvent, event_id)

    def set_event_approval(self, event_id: int, approval_state: str) -> RunEvent:
        event = self.session.get(RunEvent, event_id)
        if not event:
            raise ValueError(f"event {event_id} not found")
        event.approval_state = approval_state
        self.session.commit()
        self.session.refresh(event)
        return event

    def get_approval_event(
        self,
        run_id: int,
        stage: str,
        action: str,
        approval_state: str,
    ) -> RunEvent | None:
        statement = (
            select(RunEvent)
            .where(
                and_(
                    RunEvent.run_id == run_id,
                    RunEvent.stage == stage,
                    RunEvent.action == action,
                    RunEvent.approval_state == approval_state,
                    RunEvent.requires_approval.is_(True),
                )
            )
            .order_by(RunEvent.id.desc())
        )
        return self.session.scalar(statement)

    def get_pending_approval_events(self, run_id: int) -> list[RunEvent]:
        statement = (
            select(RunEvent)
            .where(
                and_(
                    RunEvent.run_id == run_id,
                    RunEvent.requires_approval.is_(True),
                    RunEvent.approval_state == "pending",
                )
            )
            .order_by(RunEvent.id.asc())
        )
        return list(self.session.scalars(statement).all())

    def upsert_question(self, question: str, question_type: str = "custom") -> QuestionBank:
        q_hash = hash_question(question)
        existing = self.session.scalar(select(QuestionBank).where(QuestionBank.question_hash == q_hash))
        if existing:
            return existing

        record = QuestionBank(
            question_hash=q_hash,
            canonical_text=question,
            question_type=question_type,
            options_json=[],
            tags_json=[],
        )
        self.session.add(record)
        self.session.commit()
        self.session.refresh(record)
        return record

    def add_profile_answer(
        self,
        *,
        profile_id: int,
        question: str,
        answer: str,
        question_type: str = "custom",
        confidence: float = 1.0,
        verified: bool = True,
    ) -> ProfileAnswer:
        q_hash = hash_question(question)
        self.upsert_question(question, question_type=question_type)
        existing = self.session.scalar(
            select(ProfileAnswer).where(
                and_(
                    ProfileAnswer.profile_id == profile_id,
                    ProfileAnswer.question_hash == q_hash,
                )
            )
        )

        if existing:
            existing.answer_text = answer
            existing.answer_json = {"answer": answer}
            existing.confidence = confidence
            existing.verified = verified
            obj = existing
        else:
            obj = ProfileAnswer(
                profile_id=profile_id,
                question_hash=q_hash,
                answer_text=answer,
                answer_json={"answer": answer},
                confidence=confidence,
                verified=verified,
            )
            self.session.add(obj)

        self.session.commit()
        self.session.refresh(obj)
        return obj

    def get_answer_for_question(self, profile_id: int, question: str) -> ProfileAnswer | None:
        q_hash = hash_question(question)
        statement = select(ProfileAnswer).where(
            and_(
                ProfileAnswer.profile_id == profile_id,
                ProfileAnswer.question_hash == q_hash,
            )
        )
        return self.session.scalar(statement)

    def list_profile_answers(self, profile_id: int) -> list[ProfileAnswer]:
        statement = (
            select(ProfileAnswer)
            .where(ProfileAnswer.profile_id == profile_id)
            .order_by(ProfileAnswer.updated_at.desc())
        )
        return list(self.session.scalars(statement).all())

    def create_ai_patch_suggestion(
        self,
        *,
        run_id: int,
        provider: str,
        rationale: str,
        patch_json: dict,
        confidence: float,
        status: str = "suggested",
    ) -> AIPatchSuggestion:
        item = AIPatchSuggestion(
            run_id=run_id,
            provider=provider,
            rationale=rationale,
            patch_json=patch_json,
            confidence=confidence,
            status=status,
        )
        self.session.add(item)
        self.session.commit()
        self.session.refresh(item)
        return item

    def update_ai_patch_status(self, suggestion_id: int, status: str) -> AIPatchSuggestion:
        item = self.session.get(AIPatchSuggestion, suggestion_id)
        if not item:
            raise ValueError(f"patch suggestion {suggestion_id} not found")
        item.status = status
        self.session.commit()
        self.session.refresh(item)
        return item

    def apply_patch_operation(self, profile_id: int, operation: PatchOperation) -> None:
        table = operation.table
        op = operation.operation

        if table == "profile_personal":
            model = ProfilePersonal
            key = {"profile_id": profile_id} | operation.key
        elif table == "profile_preferences":
            model = ProfilePreference
            key = {"profile_id": profile_id} | operation.key
        elif table == "profile_work_auth":
            model = ProfileWorkAuth
            key = {"profile_id": profile_id} | operation.key
        elif table == "skills":
            model = Skill
            key = {"profile_id": profile_id} | operation.key
        else:
            raise ValueError(f"unsupported patch table '{table}'")

        existing = self.session.scalar(select(model).filter_by(**key))

        if op == "insert":
            if existing:
                return
            payload = key | operation.values
            self.session.add(model(**payload))
        elif op == "update":
            if not existing:
                raise ValueError(f"cannot update missing row in table '{table}'")
            for field, value in operation.values.items():
                setattr(existing, field, value)
        elif op == "upsert":
            if existing:
                for field, value in operation.values.items():
                    setattr(existing, field, value)
            else:
                payload = key | operation.values
                self.session.add(model(**payload))
        else:
            raise ValueError(f"unsupported patch operation '{op}'")

        self.session.commit()

    def save_resume_version(
        self,
        *,
        profile_id: int,
        job_id: int,
        file_path: str,
        markdown_snapshot: str,
        llm_metadata_json: dict,
    ) -> ResumeVersion:
        item = ResumeVersion(
            profile_id=profile_id,
            job_id=job_id,
            file_path=file_path,
            markdown_snapshot=markdown_snapshot,
            llm_metadata_json=llm_metadata_json,
        )
        self.session.add(item)
        self.session.commit()
        self.session.refresh(item)
        return item

    def save_cover_letter_version(
        self,
        *,
        profile_id: int,
        job_id: int,
        file_path: str,
        markdown_snapshot: str,
        llm_metadata_json: dict,
    ) -> CoverLetterVersion:
        item = CoverLetterVersion(
            profile_id=profile_id,
            job_id=job_id,
            file_path=file_path,
            markdown_snapshot=markdown_snapshot,
            llm_metadata_json=llm_metadata_json,
        )
        self.session.add(item)
        self.session.commit()
        self.session.refresh(item)
        return item

    def record_field_fill(
        self,
        *,
        run_id: int,
        page_url: str,
        field: FieldFillPlan,
        fill_status: str = "filled",
    ) -> FieldFillResult:
        item = FieldFillResult(
            run_id=run_id,
            page_url=page_url,
            field_key=field.field_key,
            locator=field.locator,
            value_source=field.value_source,
            fill_status=fill_status,
            confidence=field.confidence,
        )
        self.session.add(item)
        self.session.commit()
        self.session.refresh(item)
        return item

    def create_submission(
        self,
        *,
        run_id: int,
        confirmation_text: str,
        confirmation_ref: str,
        screenshot_path: str,
    ) -> ApplicationSubmission:
        submission = ApplicationSubmission(
            run_id=run_id,
            submitted_at=datetime.now(UTC),
            confirmation_text=confirmation_text,
            confirmation_ref=confirmation_ref,
            screenshot_path=screenshot_path,
        )
        self.session.add(submission)
        self.session.commit()
        self.session.refresh(submission)
        return submission
