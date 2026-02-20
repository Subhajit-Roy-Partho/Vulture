from __future__ import annotations

from sqlalchemy.orm import Session

from vulture.db.repositories import Repository
from vulture.llm.router import LLMRouter
from vulture.types import JobAnalysis, RunMode


class AnswerResolver:
    def __init__(self, session: Session, llm: LLMRouter):
        self.repo = Repository(session)
        self.llm = llm

    def resolve(
        self,
        *,
        profile_id: int,
        question: str,
        analysis: JobAnalysis,
        profile,
        mode: RunMode = "medium",
    ) -> tuple[str, str, float]:
        existing = self.repo.get_answer_for_question(profile_id, question)
        critical = self.repo.is_critical_question(question)

        if existing and existing.answer_text:
            if existing.verification_state == "verified":
                return existing.answer_text, "profile_answers_verified", 0.98

            if existing.verification_state == "needs_review":
                if mode == "strict":
                    return "", "needs_review_pending", 0.0
                if mode == "medium" and critical:
                    return "", "needs_review_pending_critical", 0.0
                if mode == "yolo" and critical:
                    return "", "critical_needs_review_blocked", 0.0
                return existing.answer_text, "profile_answers_needs_review", 0.55

            if existing.verification_state == "rejected":
                return "", "rejected_answer", 0.0

            return existing.answer_text, "profile_answers", 0.9

        candidate = self.llm.draft_answer(question=question, profile=profile, analysis=analysis)
        if candidate == "UNKNOWN":
            return "", "unknown", 0.0

        if critical and mode == "yolo":
            return "", "critical_unknown_blocked", 0.0

        if critical and mode == "medium":
            return "", "critical_unknown_requires_review", 0.0

        if mode == "strict":
            return "", "strict_requires_review", 0.0

        return candidate, "llm_inferred", 0.6
