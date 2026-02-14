from __future__ import annotations

from sqlalchemy.orm import Session

from vulture.db.repositories import Repository
from vulture.llm.router import LLMRouter
from vulture.types import JobAnalysis


class AnswerResolver:
    def __init__(self, session: Session, llm: LLMRouter):
        self.repo = Repository(session)
        self.llm = llm

    def resolve(self, *, profile_id: int, question: str, analysis: JobAnalysis, profile) -> tuple[str, str, float]:
        existing = self.repo.get_answer_for_question(profile_id, question)
        if existing and existing.answer_text:
            return existing.answer_text, "profile_answers", 0.98

        candidate = self.llm.draft_answer(question=question, profile=profile, analysis=analysis)
        if candidate == "UNKNOWN":
            return "", "unknown", 0.0

        return candidate, "llm_inferred", 0.6
