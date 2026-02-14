from __future__ import annotations

from pathlib import Path

from vulture.config import get_settings
from vulture.db.base import Base
from vulture.db.session import SessionLocal, engine
from vulture.db import models  # noqa: F401
from vulture.db.seed import seed_question_bank


def ensure_data_directories() -> None:
    settings = get_settings()
    paths: list[Path] = [
        settings.data_dir,
        settings.upload_dir,
        settings.resume_dir,
        settings.cover_letter_dir,
        settings.run_artifact_dir,
        settings.browser_use_user_data_dir,
    ]
    for path in paths:
        path.mkdir(parents=True, exist_ok=True)


def init_database() -> dict[str, int]:
    ensure_data_directories()
    Base.metadata.create_all(bind=engine)

    with SessionLocal() as session:
        inserted = seed_question_bank(session)
    return {"seeded_questions": inserted}
