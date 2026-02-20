from __future__ import annotations

import os
import sqlite3
import subprocess
import sys
from pathlib import Path


def test_alembic_upgrade_and_downgrade_for_cv_expansion(tmp_path: Path) -> None:
    repo_root = Path(__file__).resolve().parents[2]
    db_path = tmp_path / "migration_test.db"
    env = os.environ.copy()
    env["DATABASE_URL"] = f"sqlite:///{db_path}"

    subprocess.run(
        [sys.executable, "-m", "alembic", "-c", "alembic.ini", "upgrade", "0002_cv_profile_expansion"],
        cwd=repo_root,
        env=env,
        check=True,
    )

    conn = sqlite3.connect(db_path)
    cur = conn.cursor()
    cur.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='publications'")
    assert cur.fetchone() is not None

    cur.execute("PRAGMA table_info(profile_answers)")
    profile_cols = {row[1] for row in cur.fetchall()}
    assert "verification_state" in profile_cols

    subprocess.run(
        [sys.executable, "-m", "alembic", "-c", "alembic.ini", "downgrade", "0001_initial_schema"],
        cwd=repo_root,
        env=env,
        check=True,
    )

    cur.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='publications'")
    assert cur.fetchone() is None

    cur.execute("PRAGMA table_info(profile_answers)")
    profile_cols_after = {row[1] for row in cur.fetchall()}
    assert "verification_state" not in profile_cols_after

    conn.close()
