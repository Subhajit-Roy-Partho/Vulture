from fastapi.testclient import TestClient

from vulture.api.app import create_app
from vulture.db.repositories import Repository
from vulture.db.session import SessionLocal


def test_profile_questionnaire_review_page_and_actions() -> None:
    app = create_app()
    client = TestClient(app)

    profile_resp = client.post(
        "/api/profiles",
        json={"name": "Web User", "job_family": "Research", "summary": ""},
    )
    profile_id = profile_resp.json()["id"]

    cv_text = r"""
\begin{rSection}{Summary}
Research systems engineer.
\end{rSection}
\begin{rSection}{Technical Skills}
Programming Languages: Python, CUDA
\end{rSection}
\begin{rSection}{Research Experience}
\begin{itemize}
\item Built infrastructure on SLURM
\end{itemize}
\end{rSection}
"""

    import_resp = client.post(
        f"/api/profiles/{profile_id}/cv/import",
        json={"raw_text": cv_text, "format": "latex", "scope": "all", "create_questions": True},
    )
    assert import_resp.status_code == 200

    page_resp = client.get(f"/profiles/{profile_id}/questionnaire/review")
    assert page_resp.status_code == 200
    assert "Pending review items" in page_resp.text

    with SessionLocal() as db:
        repo = Repository(db)
        pending = repo.list_profile_questionnaire_review(profile_id)
        assert pending
        q_hash = pending[0]["question_hash"]

    verify_resp = client.post(
        f"/web/profiles/{profile_id}/questionnaire/{q_hash}/verify",
        follow_redirects=True,
    )
    assert verify_resp.status_code == 200

    with SessionLocal() as db:
        repo = Repository(db)
        still_pending = [
            item for item in repo.list_profile_questionnaire_review(profile_id) if item["question_hash"] == q_hash
        ]
        assert not still_pending
