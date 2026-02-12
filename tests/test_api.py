from pathlib import Path


def _auth_headers(client):
    register = client.post("/auth/register", json={"email": "user@example.com", "password": "secret123"})
    assert register.status_code == 201
    login = client.post("/auth/login", json={"email": "user@example.com", "password": "secret123"})
    assert login.status_code == 200
    token = login.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


def test_end_to_end_flow(client):
    headers = _auth_headers(client)

    fixture = Path("tests/fixtures/generic_chat.json")
    with fixture.open("rb") as handle:
        upload_resp = client.post(
            "/uploads",
            headers=headers,
            files={"file": ("generic_chat.json", handle, "application/json")},
            data={"platform": "generic", "timezone_name": "UTC"},
        )
    assert upload_resp.status_code == 201, upload_resp.text
    upload_id = upload_resp.json()["upload_id"]

    get_upload = client.get(f"/uploads/{upload_id}", headers=headers)
    assert get_upload.status_code == 200
    assert get_upload.json()["status"] == "parsed"

    analyze_resp = client.post(f"/uploads/{upload_id}/analyze", headers=headers)
    assert analyze_resp.status_code == 202
    job_id = analyze_resp.json()["job_id"]

    job_resp = client.get(f"/jobs/{job_id}", headers=headers)
    assert job_resp.status_code == 200
    assert job_resp.json()["status"] in {"succeeded", "running", "queued"}

    report_resp = client.get(f"/reports/{upload_id}", headers=headers)
    assert report_resp.status_code == 200
    assert "mixed_signal_index" in report_resp.json()

    highlights_resp = client.get(f"/reports/{upload_id}/highlights", headers=headers)
    assert highlights_resp.status_code == 200
    assert "highlights" in highlights_resp.json()

    delete_resp = client.delete(f"/uploads/{upload_id}", headers=headers)
    assert delete_resp.status_code == 204

