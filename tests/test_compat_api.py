from pathlib import Path


def test_compat_end_to_end(client):
    fixture = Path("tests/fixtures/generic_chat.json")
    with fixture.open("rb") as handle:
        upload_resp = client.post(
            "/compat/upload",
            files={"file": ("generic_chat.json", handle, "application/json")},
            data={"timezone_name": "UTC"},
        )
    assert upload_resp.status_code == 201, upload_resp.text
    upload_id = upload_resp.json()["upload_id"]

    analyze_resp = client.post(f"/compat/uploads/{upload_id}/analyze")
    assert analyze_resp.status_code == 202, analyze_resp.text
    job_id = analyze_resp.json()["job_id"]

    job_resp = client.get(f"/compat/jobs/{job_id}")
    assert job_resp.status_code == 200
    job = job_resp.json()
    assert "status" in job
    assert "progress" in job

    report_resp = client.get(f"/compat/reports/{upload_id}")
    assert report_resp.status_code == 200, report_resp.text
    payload = report_resp.json()
    assert "mixed_signal_index" in payload
    assert "confidence" in payload
    assert "timeline" in payload
    assert "stats" in payload

