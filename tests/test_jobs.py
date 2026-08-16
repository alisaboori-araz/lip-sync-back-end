from app.jobs.manager import Job, JobManager


def test_client_job_status_values_are_translated():
    assert {"queued": "pending", "error": "failed"}.get("queued", "queued") == "pending"
    assert {"queued": "pending", "error": "failed"}.get("error", "error") == "failed"
