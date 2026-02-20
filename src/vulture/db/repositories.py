from __future__ import annotations

import hashlib
from datetime import UTC, date, datetime
from urllib.parse import urlparse

from sqlalchemy import and_, delete, select
from sqlalchemy.orm import Session

from vulture.core.cv_parser import ParsedCV
from vulture.db.models import (
    AIPatchSuggestion,
    AdditionalProject,
    ApplicationSubmission,
    AwardHonor,
    CVImportItem,
    CVImportRun,
    ConferencePresentation,
    CoverLetterVersion,
    Education,
    Experience,
    FieldFillResult,
    Job,
    JobRequirement,
    Profile,
    ProfileAnswer,
    ProfilePersonal,
    ProfilePreference,
    ProfileWorkAuth,
    Publication,
    QuestionBank,
    ResumeVersion,
    RunEvent,
    RunSession,
    ServiceOutreach,
    Skill,
    TeachingMentoring,
)
from vulture.types import (
    CVImportResult,
    FieldFillPlan,
    JobAnalysis,
    PatchOperation,
    ProfilePatchBundle,
    QuestionTemplate,
)

CRITICAL_QUESTION_TYPES = {"work_auth", "salary", "eeo", "veteran", "disability"}
CRITICAL_TAGS = {"legal", "compliance", "attestation", "compensation"}


def canonicalize_question(question: str) -> str:
    return " ".join(question.strip().lower().split())


def hash_question(question: str) -> str:
    return hashlib.sha256(canonicalize_question(question).encode("utf-8")).hexdigest()


def hash_text(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def _safe_year(value: int | None) -> int:
    if not value:
        return 0
    return int(value)


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

    def list_education(self, profile_id: int) -> list[Education]:
        statement = select(Education).where(Education.profile_id == profile_id).order_by(Education.id.desc())
        return list(self.session.scalars(statement).all())

    def add_education(
        self,
        *,
        profile_id: int,
        institution: str,
        degree: str,
        field: str,
        gpa: str = "",
        thesis_title: str = "",
        advisor: str = "",
        lab: str = "",
    ) -> Education:
        item = Education(
            profile_id=profile_id,
            institution=institution,
            degree=degree,
            field=field,
            gpa=gpa,
            thesis_title=thesis_title,
            advisor=advisor,
            lab=lab,
        )
        self.session.add(item)
        self.session.commit()
        self.session.refresh(item)
        return item

    def list_experiences(self, profile_id: int) -> list[Experience]:
        statement = select(Experience).where(Experience.profile_id == profile_id).order_by(Experience.id.desc())
        return list(self.session.scalars(statement).all())

    def add_experience(
        self,
        *,
        profile_id: int,
        company: str,
        title: str,
        description: str = "",
        advisor: str = "",
        impact_summary: str = "",
        skills_json: list[str] | None = None,
    ) -> Experience:
        item = Experience(
            profile_id=profile_id,
            company=company,
            title=title,
            description=description,
            advisor=advisor,
            impact_summary=impact_summary,
            skills_json=skills_json or [],
        )
        self.session.add(item)
        self.session.commit()
        self.session.refresh(item)
        return item

    def list_skills(self, profile_id: int) -> list[Skill]:
        statement = select(Skill).where(Skill.profile_id == profile_id).order_by(Skill.id.desc())
        return list(self.session.scalars(statement).all())

    def add_skill(
        self,
        *,
        profile_id: int,
        name: str,
        category: str,
        years: float = 0.0,
        proficiency: str = "",
        last_used_year: int = 0,
    ) -> Skill:
        item = Skill(
            profile_id=profile_id,
            name=name,
            category=category,
            years=years,
            proficiency=proficiency,
            last_used_year=last_used_year,
        )
        self.session.add(item)
        self.session.commit()
        self.session.refresh(item)
        return item

    def list_publications(self, profile_id: int) -> list[Publication]:
        statement = (
            select(Publication)
            .where(Publication.profile_id == profile_id)
            .order_by(Publication.publication_year.desc(), Publication.id.desc())
        )
        return list(self.session.scalars(statement).all())

    def add_publication(
        self,
        *,
        profile_id: int,
        title: str,
        venue: str = "",
        publication_year: int = 0,
        status: str = "",
        doi: str = "",
        url: str = "",
        authors_json: list[str] | None = None,
        contribution: str = "",
    ) -> Publication:
        item = Publication(
            profile_id=profile_id,
            title=title,
            venue=venue,
            publication_year=_safe_year(publication_year),
            status=status,
            doi=doi,
            url=url,
            authors_json=authors_json or [],
            contribution=contribution,
        )
        self.session.add(item)
        self.session.commit()
        self.session.refresh(item)
        return item

    def list_awards(self, profile_id: int) -> list[AwardHonor]:
        statement = (
            select(AwardHonor)
            .where(AwardHonor.profile_id == profile_id)
            .order_by(AwardHonor.award_year.desc(), AwardHonor.id.desc())
        )
        return list(self.session.scalars(statement).all())

    def add_award(
        self,
        *,
        profile_id: int,
        title: str,
        issuer: str = "",
        award_year: int = 0,
        details: str = "",
    ) -> AwardHonor:
        item = AwardHonor(
            profile_id=profile_id,
            title=title,
            issuer=issuer,
            award_year=_safe_year(award_year),
            details=details,
        )
        self.session.add(item)
        self.session.commit()
        self.session.refresh(item)
        return item

    def list_conferences(self, profile_id: int) -> list[ConferencePresentation]:
        statement = (
            select(ConferencePresentation)
            .where(ConferencePresentation.profile_id == profile_id)
            .order_by(ConferencePresentation.event_year.desc(), ConferencePresentation.id.desc())
        )
        return list(self.session.scalars(statement).all())

    def add_conference(
        self,
        *,
        profile_id: int,
        name: str,
        event_year: int = 0,
        role: str = "",
        details: str = "",
    ) -> ConferencePresentation:
        item = ConferencePresentation(
            profile_id=profile_id,
            name=name,
            event_year=_safe_year(event_year),
            role=role,
            details=details,
        )
        self.session.add(item)
        self.session.commit()
        self.session.refresh(item)
        return item

    def list_teaching(self, profile_id: int) -> list[TeachingMentoring]:
        statement = select(TeachingMentoring).where(TeachingMentoring.profile_id == profile_id).order_by(
            TeachingMentoring.id.desc()
        )
        return list(self.session.scalars(statement).all())

    def add_teaching(
        self,
        *,
        profile_id: int,
        role: str,
        organization: str = "",
        term: str = "",
        details: str = "",
    ) -> TeachingMentoring:
        item = TeachingMentoring(
            profile_id=profile_id,
            role=role,
            organization=organization,
            term=term,
            details=details,
        )
        self.session.add(item)
        self.session.commit()
        self.session.refresh(item)
        return item

    def list_service(self, profile_id: int) -> list[ServiceOutreach]:
        statement = (
            select(ServiceOutreach)
            .where(ServiceOutreach.profile_id == profile_id)
            .order_by(ServiceOutreach.event_year.desc(), ServiceOutreach.id.desc())
        )
        return list(self.session.scalars(statement).all())

    def add_service(
        self,
        *,
        profile_id: int,
        role: str = "",
        organization: str = "",
        event_name: str = "",
        event_year: int = 0,
        details: str = "",
    ) -> ServiceOutreach:
        item = ServiceOutreach(
            profile_id=profile_id,
            role=role,
            organization=organization,
            event_name=event_name,
            event_year=_safe_year(event_year),
            details=details,
        )
        self.session.add(item)
        self.session.commit()
        self.session.refresh(item)
        return item

    def list_additional_projects(self, profile_id: int) -> list[AdditionalProject]:
        statement = (
            select(AdditionalProject)
            .where(AdditionalProject.profile_id == profile_id)
            .order_by(AdditionalProject.id.desc())
        )
        return list(self.session.scalars(statement).all())

    def add_additional_project(
        self,
        *,
        profile_id: int,
        title: str,
        summary: str = "",
        skills_json: list[str] | None = None,
        impact: str = "",
    ) -> AdditionalProject:
        item = AdditionalProject(
            profile_id=profile_id,
            title=title,
            summary=summary,
            skills_json=skills_json or [],
            impact=impact,
        )
        self.session.add(item)
        self.session.commit()
        self.session.refresh(item)
        return item

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

    def upsert_question(
        self,
        question: str,
        question_type: str = "custom",
        *,
        tags: list[str] | None = None,
        section: str = "general",
        importance: str = "medium",
        is_cv_derived: bool = False,
    ) -> QuestionBank:
        q_hash = hash_question(question)
        existing = self.session.scalar(select(QuestionBank).where(QuestionBank.question_hash == q_hash))
        if existing:
            if tags:
                merged = sorted(set(existing.tags_json + list(tags)))
                existing.tags_json = merged
            if section and existing.section == "general":
                existing.section = section
            if importance and existing.importance == "medium":
                existing.importance = importance
            existing.is_cv_derived = existing.is_cv_derived or is_cv_derived
            self.session.commit()
            self.session.refresh(existing)
            return existing

        record = QuestionBank(
            question_hash=q_hash,
            canonical_text=question,
            question_type=question_type,
            options_json=[],
            tags_json=list(tags or []),
            section=section,
            importance=importance,
            is_cv_derived=is_cv_derived,
        )
        self.session.add(record)
        self.session.commit()
        self.session.refresh(record)
        return record

    def upsert_question_template(self, template: QuestionTemplate) -> QuestionBank:
        return self.upsert_question(
            template.canonical_text,
            question_type=template.question_type,
            tags=template.tags,
            section=template.source_section,
            importance=template.importance,
            is_cv_derived=True,
        )

    def add_profile_answer(
        self,
        *,
        profile_id: int,
        question: str,
        answer: str,
        question_type: str = "custom",
        confidence: float = 1.0,
        verified: bool = True,
        source: str = "manual",
        verification_state: str = "verified",
        source_section: str = "general",
        evidence_json: dict | None = None,
        tags: list[str] | None = None,
        importance: str = "medium",
        is_cv_derived: bool = False,
    ) -> ProfileAnswer:
        q_hash = hash_question(question)
        self.upsert_question(
            question,
            question_type=question_type,
            tags=tags,
            section=source_section,
            importance=importance,
            is_cv_derived=is_cv_derived,
        )
        existing = self.session.scalar(
            select(ProfileAnswer).where(
                and_(
                    ProfileAnswer.profile_id == profile_id,
                    ProfileAnswer.question_hash == q_hash,
                )
            )
        )

        verified_value = verified and verification_state == "verified"
        if existing:
            existing.answer_text = answer
            existing.answer_json = {"answer": answer}
            existing.confidence = confidence
            existing.verified = verified_value
            existing.source = source
            existing.verification_state = verification_state
            existing.source_section = source_section
            existing.evidence_json = evidence_json or {}
            obj = existing
        else:
            obj = ProfileAnswer(
                profile_id=profile_id,
                question_hash=q_hash,
                answer_text=answer,
                answer_json={"answer": answer},
                confidence=confidence,
                verified=verified_value,
                source=source,
                verification_state=verification_state,
                source_section=source_section,
                evidence_json=evidence_json or {},
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

    def get_question_by_hash(self, question_hash: str) -> QuestionBank | None:
        return self.session.scalar(select(QuestionBank).where(QuestionBank.question_hash == question_hash))

    def get_question_for_text(self, question: str) -> QuestionBank | None:
        return self.get_question_by_hash(hash_question(question))

    def is_critical_question(self, question: str) -> bool:
        item = self.get_question_for_text(question)
        if not item:
            lowered = question.lower()
            return any(token in lowered for token in ["salary", "authorized", "sponsorship", "veteran", "disability"])
        tags = {tag.lower() for tag in item.tags_json}
        return item.question_type in CRITICAL_QUESTION_TYPES or bool(tags & CRITICAL_TAGS)

    def get_answer_by_hash(self, profile_id: int, question_hash: str) -> ProfileAnswer | None:
        statement = select(ProfileAnswer).where(
            and_(
                ProfileAnswer.profile_id == profile_id,
                ProfileAnswer.question_hash == question_hash,
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

    def list_profile_questionnaire(self, profile_id: int) -> list[dict]:
        statement = (
            select(QuestionBank, ProfileAnswer)
            .outerjoin(
                ProfileAnswer,
                and_(
                    ProfileAnswer.question_hash == QuestionBank.question_hash,
                    ProfileAnswer.profile_id == profile_id,
                ),
            )
            .order_by(QuestionBank.section.asc(), QuestionBank.canonical_text.asc())
        )
        rows = self.session.execute(statement).all()
        return [
            {
                "question_hash": question.question_hash,
                "question": question.canonical_text,
                "question_type": question.question_type,
                "tags": question.tags_json,
                "section": question.section,
                "importance": question.importance,
                "is_cv_derived": question.is_cv_derived,
                "answer": answer.answer_text if answer else "",
                "verification_state": answer.verification_state if answer else "missing",
                "source": answer.source if answer else "",
                "source_section": answer.source_section if answer else question.section,
            }
            for question, answer in rows
        ]

    def list_profile_questionnaire_review(self, profile_id: int) -> list[dict]:
        items = self.list_profile_questionnaire(profile_id)
        return [item for item in items if item["verification_state"] == "needs_review"]

    def set_profile_answer_verification(
        self, profile_id: int, question_hash: str, verification_state: str
    ) -> ProfileAnswer:
        item = self.get_answer_by_hash(profile_id, question_hash)
        if not item:
            raise ValueError("profile answer not found")
        item.verification_state = verification_state
        item.verified = verification_state == "verified"
        self.session.commit()
        self.session.refresh(item)
        return item

    def count_pending_review_answers(self, profile_id: int, *, critical_only: bool = False) -> int:
        statement = (
            select(QuestionBank, ProfileAnswer)
            .join(
                ProfileAnswer,
                and_(
                    ProfileAnswer.question_hash == QuestionBank.question_hash,
                    ProfileAnswer.profile_id == profile_id,
                ),
            )
            .where(ProfileAnswer.verification_state == "needs_review")
        )
        rows = self.session.execute(statement).all()
        if not critical_only:
            return len(rows)

        count = 0
        for question, _answer in rows:
            tags = {tag.lower() for tag in question.tags_json}
            if question.question_type in CRITICAL_QUESTION_TYPES or bool(tags & CRITICAL_TAGS):
                count += 1
        return count

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

    def create_cv_import_run(
        self,
        *,
        profile_id: int,
        input_format: str,
        scope: str,
        status: str,
        warnings: list[str] | None,
        raw_text_hash: str,
    ) -> CVImportRun:
        run = CVImportRun(
            profile_id=profile_id,
            input_format=input_format,
            scope=scope,
            status=status,
            warnings_json=warnings or [],
            raw_text_hash=raw_text_hash,
        )
        self.session.add(run)
        self.session.commit()
        self.session.refresh(run)
        return run

    def update_cv_import_run(
        self,
        run_id: int,
        *,
        status: str | None = None,
        warnings: list[str] | None = None,
    ) -> CVImportRun:
        run = self.session.get(CVImportRun, run_id)
        if not run:
            raise ValueError("cv import run not found")
        if status is not None:
            run.status = status
        if warnings is not None:
            run.warnings_json = warnings
        self.session.commit()
        self.session.refresh(run)
        return run

    def add_cv_import_item(
        self,
        *,
        import_run_id: int,
        profile_id: int,
        section: str,
        item_key: str,
        payload_json: dict,
        created_question_hash: str = "",
    ) -> CVImportItem:
        item = CVImportItem(
            import_run_id=import_run_id,
            profile_id=profile_id,
            section=section,
            item_key=item_key,
            payload_json=payload_json,
            created_question_hash=created_question_hash,
        )
        self.session.add(item)
        self.session.commit()
        self.session.refresh(item)
        return item

    def import_cv_payload(
        self,
        *,
        profile_id: int,
        parsed: ParsedCV,
        templates: list[QuestionTemplate],
        input_format: str,
        scope: str,
    ) -> CVImportResult:
        if not self.get_profile(profile_id):
            raise ValueError("profile not found")

        run = self.create_cv_import_run(
            profile_id=profile_id,
            input_format=input_format,
            scope=scope,
            status="running",
            warnings=parsed.warnings,
            raw_text_hash=hash_text("\n".join(parsed.metadata.get("all_lines", []))),
        )

        imported_sections: dict[str, int] = {}
        created_questions = 0
        created_answers = 0

        for template in templates:
            question = self.upsert_question_template(template)
            created_questions += 1
            answer_text = template.suggested_answer or ""
            if answer_text:
                self.add_profile_answer(
                    profile_id=profile_id,
                    question=template.canonical_text,
                    answer=answer_text,
                    question_type=template.question_type,
                    verified=False,
                    source="cv_import",
                    verification_state="needs_review",
                    source_section=template.source_section,
                    evidence_json={"template": True},
                    tags=template.tags,
                    importance=template.importance,
                    is_cv_derived=True,
                )
                created_answers += 1
            self.add_cv_import_item(
                import_run_id=run.id,
                profile_id=profile_id,
                section=template.source_section,
                item_key=template.canonical_text[:140],
                payload_json=template.model_dump(),
                created_question_hash=question.question_hash,
            )

        for section_name, section in parsed.sections.items():
            imported_sections[section_name] = len(section.lines) + len(section.bullets)
            if section_name == "publications":
                for entry in section.bullets:
                    self.add_publication(
                        profile_id=profile_id,
                        title=entry,
                        status="imported",
                        contribution="Imported from CV",
                    )
            elif section_name == "awards":
                for entry in section.bullets:
                    self.add_award(profile_id=profile_id, title=entry, details="Imported from CV")
            elif section_name == "conferences":
                for entry in section.bullets:
                    self.add_conference(profile_id=profile_id, name=entry, role="Imported from CV")
            elif section_name == "teaching":
                for entry in section.bullets:
                    self.add_teaching(profile_id=profile_id, role=entry, details="Imported from CV")
            elif section_name == "service":
                for entry in section.bullets:
                    self.add_service(profile_id=profile_id, role=entry, details="Imported from CV")
            elif section_name == "additional_projects":
                for entry in section.bullets:
                    self.add_additional_project(
                        profile_id=profile_id,
                        title=entry[:120],
                        summary=entry,
                        impact="Imported from CV",
                    )
            elif section_name == "education":
                for line in section.lines:
                    if any(token in line.lower() for token in ["phd", "ph.d", "integrated", "bs", "ms"]):
                        self.add_education(
                            profile_id=profile_id,
                            institution="Imported from CV",
                            degree=line,
                            field="",
                            gpa="",
                        )
            elif section_name == "research_experience":
                for entry in section.bullets[:12]:
                    self.add_experience(
                        profile_id=profile_id,
                        company="Imported from CV",
                        title="Research Experience",
                        description=entry,
                        impact_summary=entry,
                    )
            elif section_name == "technical_skills":
                for line in section.lines:
                    if ":" not in line:
                        continue
                    head, tail = [part.strip() for part in line.split(":", 1)]
                    for item in [token.strip() for token in tail.split(",") if token.strip()][:20]:
                        self.add_skill(profile_id=profile_id, name=item, category=head)

        self.update_cv_import_run(run.id, status="completed", warnings=parsed.warnings)
        return CVImportResult(
            imported_sections=imported_sections,
            created_questions=created_questions,
            created_answers=created_answers,
            warnings=parsed.warnings,
        )
