from __future__ import annotations

import pytest

from vulture.db.base import Base
from vulture.db.seed import seed_question_bank
from vulture.db.session import SessionLocal, engine


@pytest.fixture(autouse=True)
def reset_db() -> None:
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)
    with SessionLocal() as session:
        seed_question_bank(session)
    yield
