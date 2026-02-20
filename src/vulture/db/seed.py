from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.orm import Session

from vulture.db.models import QuestionBank
from vulture.db.repositories import Repository, hash_question

COMMON_QUESTIONS: list[dict[str, object]] = [
    {
        "text": "Are you legally authorized to work in the United States?",
        "type": "work_auth",
        "tags": ["authorization", "us", "legal", "compliance"],
        "section": "compliance",
        "importance": "high",
    },
    {
        "text": "Will you now or in the future require visa sponsorship?",
        "type": "work_auth",
        "tags": ["sponsorship", "visa", "legal", "compliance"],
        "section": "compliance",
        "importance": "high",
    },
    {
        "text": "What are your salary expectations?",
        "type": "salary",
        "tags": ["compensation", "legal"],
        "section": "preferences",
        "importance": "high",
    },
    {
        "text": "Are you willing to relocate?",
        "type": "boolean",
        "tags": ["relocation", "preference"],
        "section": "preferences",
        "importance": "medium",
    },
    {
        "text": "What is your notice period?",
        "type": "short_text",
        "tags": ["notice", "availability"],
        "section": "preferences",
        "importance": "medium",
    },
    {
        "text": "LinkedIn profile URL",
        "type": "url",
        "tags": ["social", "profile"],
        "section": "contact",
        "importance": "high",
    },
    {
        "text": "Portfolio URL",
        "type": "url",
        "tags": ["portfolio"],
        "section": "contact",
        "importance": "medium",
    },
    {
        "text": "GitHub profile URL",
        "type": "url",
        "tags": ["github", "portfolio"],
        "section": "contact",
        "importance": "medium",
    },
    {
        "text": "Google Scholar profile URL",
        "type": "url",
        "tags": ["scholar", "research"],
        "section": "contact",
        "importance": "medium",
    },
    {
        "text": "Do you identify as Hispanic or Latino?",
        "type": "eeo",
        "tags": ["eeo", "demographics", "compliance", "legal"],
        "section": "compliance",
        "importance": "high",
    },
    {
        "text": "Please select your race/ethnicity.",
        "type": "eeo",
        "tags": ["eeo", "race", "compliance", "legal"],
        "section": "compliance",
        "importance": "high",
    },
    {
        "text": "Protected veteran status",
        "type": "veteran",
        "tags": ["veteran", "compliance", "legal"],
        "section": "compliance",
        "importance": "high",
    },
    {
        "text": "Disability self-identification",
        "type": "disability",
        "tags": ["disability", "compliance", "legal"],
        "section": "compliance",
        "importance": "high",
    },
    {
        "text": "Are you at least 18 years old?",
        "type": "boolean",
        "tags": ["legal", "age"],
        "section": "compliance",
        "importance": "high",
    },
    {
        "text": "Earliest available start date",
        "type": "date",
        "tags": ["availability", "start_date"],
        "section": "preferences",
        "importance": "medium",
    },
    {
        "text": "Why are you interested in this role?",
        "type": "long_text",
        "tags": ["motivation", "essay"],
        "section": "motivation",
        "importance": "medium",
    },
    {
        "text": "Describe a relevant project you led.",
        "type": "long_text",
        "tags": ["experience", "project"],
        "section": "projects",
        "importance": "medium",
    },
    {
        "text": "Preferred work location",
        "type": "single_select",
        "tags": ["location", "preference"],
        "section": "preferences",
        "importance": "medium",
    },
    {
        "text": "Are you willing to travel for work?",
        "type": "boolean",
        "tags": ["travel", "preference"],
        "section": "preferences",
        "importance": "medium",
    },
    {
        "text": "Current company",
        "type": "short_text",
        "tags": ["employment"],
        "section": "experience",
        "importance": "medium",
    },
    {
        "text": "Current title",
        "type": "short_text",
        "tags": ["employment"],
        "section": "experience",
        "importance": "medium",
    },
]


def seed_question_bank(session: Session) -> int:
    repo = Repository(session)
    inserted = 0
    for question in COMMON_QUESTIONS:
        q_hash = hash_question(str(question["text"]))
        existing = session.scalar(select(QuestionBank).where(QuestionBank.question_hash == q_hash))
        repo.upsert_question(
            str(question["text"]),
            question_type=str(question["type"]),
            tags=list(question["tags"]),
            section=str(question.get("section", "general")),
            importance=str(question.get("importance", "medium")),
            is_cv_derived=False,
        )
        if not existing:
            inserted += 1

    return inserted
