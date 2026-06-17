import pytest
from fastapi.testclient import TestClient

from backend.app.models import Severity, WorkOrderCreate
from backend.app.main import app, openai_orchestrator, repository
from backend.app.services.openai_ai import OpenAIOrchestrationResult


@pytest.fixture(autouse=True)
def isolated_repository(tmp_path):
    repository.db_path = tmp_path / "fieldvoice_test.db"
    repository.initialize()
    repository.reset()
    yield
    repository.reset()


def test_ingest_is_idempotent_for_offline_replay():
    client = TestClient(app)
    payload = {
        "client_uuid": "offline-123",
        "worker_id": "tech-1",
        "transcript": "Inspecting pump PMP 204 Bravo fault code F-12 action applied coolant need seal kit severity high",
    }

    first = client.post("/api/ingest", json=payload)
    second = client.post("/api/ingest", json=payload)

    assert first.status_code == 200
    assert second.status_code == 200
    assert first.json()["work_order"]["id"] == second.json()["work_order"]["id"]
    assert second.json()["idempotent"] is True
    assert len(client.get("/api/work-orders").json()) == 1


def test_query_returns_domain_answer_under_latency_budget():
    client = TestClient(app)

    response = client.post(
        "/api/query",
        json={"query": "What is the last maintenance date for PMP-204B?", "equipment_code": "PMP-204B"},
    )

    payload = response.json()
    assert response.status_code == 200
    assert "2026-05-18" in payload["answer"]
    assert payload["latency_ms"] < 3000


def test_speech_status_exposes_stt_tts_backends():
    client = TestClient(app)

    response = client.get("/api/speech/status")

    assert response.status_code == 200
    payload = response.json()
    assert "stt" in payload
    assert "tts" in payload
    assert "domain_prompt" in payload["stt"]


def test_ai_status_exposes_openai_mandatory_provider():
    client = TestClient(app)

    response = client.get("/api/ai/status")

    assert response.status_code == 200
    payload = response.json()
    assert payload["provider"] == "OpenAI"
    assert "structured_work_order_extraction" in payload["used_for"]


def test_create_work_order_command_uses_openai_extraction_when_available(monkeypatch):
    client = TestClient(app)

    def fake_orchestrate(transcript, client_uuid, worker_id):
        return OpenAIOrchestrationResult(
            intent="create_work_order",
            model="test-openai",
            missing_fields=[],
            work_order=WorkOrderCreate(
                client_uuid=client_uuid,
                equipment_code="TRF-330C",
                inspection_result="Oil seepage detected near transformer conservator tank",
                fault_code="F-21",
                location="Jaipur substation yard",
                severity=Severity.CRITICAL,
                action_taken="Isolated area and requested transformer oil top-up",
                parts_required=["transformer oil", "gasket kit"],
                created_by=worker_id,
                transcript=transcript,
            ),
        )

    monkeypatch.setattr(openai_orchestrator, "orchestrate", fake_orchestrate)

    response = client.post(
        "/api/ingest",
        json={
            "client_uuid": "openai-create-1",
            "worker_id": "tech-openai",
            "command_mode": "create_work_order",
            "transcript": "Transformer has critical oil seepage at Jaipur yard and needs transformer oil.",
        },
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["work_order"]["equipment_code"] == "TRF-330C"
    assert payload["work_order"]["severity"] == "CRITICAL"
    assert payload["work_order"]["location"] == "Jaipur substation yard"


def test_transcribe_endpoint_returns_fallback_when_whisper_missing():
    client = TestClient(app)

    response = client.post(
        "/api/speech/transcribe",
        files={"audio": ("test.webm", b"not-real-audio", "audio/webm")},
    )

    assert response.status_code == 200
    assert "transcript" in response.json()
    assert "engine" in response.json()


def test_sync_processes_batch_and_counts_duplicates():
    client = TestClient(app)
    item = {
        "client_uuid": "sync-1",
        "worker_id": "tech-1",
        "transcript": "Log CMP 118 Alpha pressure drop fault code F-07 action replaced filter need AF-118 severity medium",
    }

    response = client.post("/api/sync", json={"items": [item, item]})

    assert response.status_code == 200
    assert response.json()["processed"] == 2
    assert response.json()["duplicates"] == 1
    assert len(client.get("/api/work-orders").json()) == 1


def test_work_order_can_be_closed_without_deleting_audit_record():
    client = TestClient(app)
    created = client.post(
        "/api/ingest",
        json={
            "client_uuid": "close-1",
            "worker_id": "tech-1",
            "transcript": "Inspecting pump PMP 204 Bravo fault code F-12 action applied coolant need seal kit severity high",
        },
    ).json()["work_order"]

    response = client.patch(
        f"/api/work-orders/{created['id']}",
        json={"status": "CLOSED"},
    )

    assert response.status_code == 200
    assert response.json()["status"] == "CLOSED"
    stats = client.get("/api/dashboard/stats").json()
    assert stats["total_work_orders"] == 1
    assert stats["open_work_orders"] == 0
