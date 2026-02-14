from fastapi.testclient import TestClient

from vulture.api.app import create_app


def test_profile_create_and_list_api() -> None:
    app = create_app()
    client = TestClient(app)

    create_resp = client.post(
        "/api/profiles",
        json={"name": "Main", "job_family": "Engineering", "summary": "Candidate"},
    )
    assert create_resp.status_code == 200
    profile_id = create_resp.json()["id"]

    answer_resp = client.post(
        f"/api/profiles/{profile_id}/answers",
        json={"question": "Authorized to work in US?", "answer": "Yes", "question_type": "work_auth"},
    )
    assert answer_resp.status_code == 200

    list_resp = client.get("/api/profiles")
    assert list_resp.status_code == 200
    assert any(item["id"] == profile_id for item in list_resp.json())
