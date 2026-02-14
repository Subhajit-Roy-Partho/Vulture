from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.orm import Session

from vulture.db.models import QuestionBank
from vulture.db.repositories import hash_question

COMMON_QUESTIONS: list[dict[str, object]] = [
    {
        "text": "Are you legally authorized to work in the United States?",
        "type": "work_auth",
        "tags": ["authorization", "us"],
    },
    {
        "text": "Will you now or in the future require visa sponsorship?",
        "type": "work_auth",
        "tags": ["sponsorship", "visa"],
    },
    {
        "text": "What are your salary expectations?",
        "type": "salary",
        "tags": ["compensation"],
    },
    {
        "text": "Are you willing to relocate?",
        "type": "boolean",
        "tags": ["relocation", "preference"],
    },
    {
        "text": "What is your notice period?",
        "type": "short_text",
        "tags": ["notice", "availability"],
    },
    {
        "text": "LinkedIn profile URL",
        "type": "url",
        "tags": ["social", "profile"],
    },
    {
        "text": "Portfolio URL",
        "type": "url",
        "tags": ["portfolio"],
    },
    {
        "text": "GitHub profile URL",
        "type": "url",
        "tags": ["github", "portfolio"],
    },
    {
        "text": "Do you identify as Hispanic or Latino?",
        "type": "eeo",
        "tags": ["eeo", "demographics"],
    },
    {
        "text": "Please select your race/ethnicity.",
        "type": "eeo",
        "tags": ["eeo", "race"],
    },
    {
        "text": "Protected veteran status",
        "type": "veteran",
        "tags": ["veteran", "compliance"],
    },
    {
        "text": "Disability self-identification",
        "type": "disability",
        "tags": ["disability", "compliance"],
    },
    {
        "text": "Are you at least 18 years old?",
        "type": "boolean",
        "tags": ["legal", "age"],
    },
    {
        "text": "Earliest available start date",
        "type": "date",
        "tags": ["availability", "start_date"],
    },
    {
        "text": "Why are you interested in this role?",
        "type": "long_text",
        "tags": ["motivation", "essay"],
    },
    {
        "text": "Describe a relevant project you led.",
        "type": "long_text",
        "tags": ["experience", "project"],
    },
    {
        "text": "Preferred work location",
        "type": "single_select",
        "tags": ["location", "preference"],
    },
    {
        "text": "Are you willing to travel for work?",
        "type": "boolean",
        "tags": ["travel", "preference"],
    },
    {
        "text": "Current company",
        "type": "short_text",
        "tags": ["employment"],
    },
    {
        "text": "Current title",
        "type": "short_text",
        "tags": ["employment"],
    },
]


def seed_question_bank(session: Session) -> int:
    inserted = 0
    for question in COMMON_QUESTIONS:
        canonical_text = str(question["text"])
        q_hash = hash_question(canonical_text)
        existing = session.scalar(select(QuestionBank).where(QuestionBank.question_hash == q_hash))
        if existing:
            continue
        session.add(
            QuestionBank(
                question_hash=q_hash,
                canonical_text=canonical_text,
                question_type=str(question["type"]),
                options_json=[],
                tags_json=list(question["tags"]),
            )
        )
        inserted += 1

    session.commit()
    return inserted
