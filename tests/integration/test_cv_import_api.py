from fastapi.testclient import TestClient

from vulture.api.app import create_app


def test_cv_import_creates_questionnaire_and_needs_review_items() -> None:
    app = create_app()
    client = TestClient(app)

    profile_resp = client.post(
        "/api/profiles",
        json={"name": "CV User", "job_family": "ML Systems", "summary": ""},
    )
    assert profile_resp.status_code == 200
    profile_id = profile_resp.json()["id"]

    cv_text = r"""
\begin{rSection}{Summary}
ML systems researcher focused on HPC workflows.
\end{rSection}
\begin{rSection}{Research Experience}
\begin{itemize}
\item Built scalable transformer pipelines with PyTorch
\end{itemize}
\end{rSection}
\begin{rSection}{Technical Skills}
Programming Languages: Python, C++, CUDA
Machine Learning: PyTorch, TensorFlow, Transformers
\end{rSection}
\begin{rSection}{Publications & Preprints}
\begin{itemize}
\item Sample publication 2025
\end{itemize}
\end{rSection}
"""

    import_resp = client.post(
        f"/api/profiles/{profile_id}/cv/import",
        json={"raw_text": cv_text, "format": "latex", "scope": "all", "create_questions": True},
    )
    assert import_resp.status_code == 200
    payload = import_resp.json()
    assert payload["created_questions"] >= 120

    questionnaire_resp = client.get(f"/api/profiles/{profile_id}/questionnaire")
    assert questionnaire_resp.status_code == 200
    questionnaire = questionnaire_resp.json()
    assert len(questionnaire) >= 120

    review_resp = client.get(f"/api/profiles/{profile_id}/questionnaire/review")
    assert review_resp.status_code == 200
    review_items = review_resp.json()
    assert len(review_items) > 0

    first = review_items[0]
    verify_resp = client.post(
        f"/api/profiles/{profile_id}/questionnaire/{first['question_hash']}/verify"
    )
    assert verify_resp.status_code == 200
    assert verify_resp.json()["verification_state"] == "verified"
