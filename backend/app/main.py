from __future__ import annotations

import asyncio
import os
import time
from pathlib import Path

from fastapi import FastAPI, File, HTTPException, Query, UploadFile, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
from starlette.background import BackgroundTask

from backend.app.models import (
    DashboardStats,
    Equipment,
    EventType,
    IngestRequest,
    IngestResponse,
    QueryRequest,
    QueryResponse,
    SyncRequest,
    SyncResponse,
    VoiceNote,
    WorkOrder,
    WorkOrderPatch,
    WorkOrderStatus,
)
from backend.app.repository import Repository
from backend.app.services.domain import load_domain_catalog
from backend.app.services.events import EventHub
from backend.app.services.extractor import VoiceExtractor
from backend.app.services.knowledge import KnowledgeBase
from backend.app.services.openai_ai import OpenAIOrchestrator
from backend.app.services.speech import SpeechService

ROOT = Path(__file__).resolve().parents[2]
FRONTEND_DIR = ROOT / "frontend"
TMP_DIR = ROOT / "data" / "tmp"

catalog = load_domain_catalog()
repository = Repository()
extractor = VoiceExtractor(catalog)
knowledge_base = KnowledgeBase(catalog)
event_hub = EventHub()
speech_service = SpeechService(catalog)
openai_orchestrator = OpenAIOrchestrator(catalog)


class TTSRequest(BaseModel):
    text: str

app = FastAPI(
    title="FieldVoice AI Assistant",
    summary="Voice-first field worker assistant with extraction, RAG, offline sync, and supervisor events.",
    version="1.0.0",
)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)
app.mount("/static", StaticFiles(directory=FRONTEND_DIR), name="static")


@app.get("/", include_in_schema=False)
async def index() -> FileResponse:
    return FileResponse(FRONTEND_DIR / "index.html")


@app.get("/manifest.webmanifest", include_in_schema=False)
async def manifest() -> FileResponse:
    return FileResponse(
        FRONTEND_DIR / "manifest.webmanifest",
        media_type="application/manifest+json",
    )


@app.get("/sw.js", include_in_schema=False)
async def service_worker() -> FileResponse:
    # Served from the root so the worker's scope covers the whole app.
    return FileResponse(
        FRONTEND_DIR / "sw.js",
        media_type="application/javascript",
        headers={"Service-Worker-Allowed": "/", "Cache-Control": "no-cache"},
    )


@app.get("/api/health")
async def health() -> dict[str, str]:
    return {
        "status": "ok",
        "stt_mode": str(speech_service.status()["stt"]["backend"]),
        "ai_provider": "OpenAI" if openai_orchestrator.available else "local-fallback",
        "domain_vocabulary": catalog.vocabulary_prompt,
    }


@app.get("/api/ai/status")
async def ai_status() -> dict[str, object]:
    return openai_orchestrator.status()


@app.get("/api/speech/status")
async def speech_status() -> dict[str, object]:
    return speech_service.status()


@app.post("/api/speech/transcribe")
async def transcribe_audio(audio: UploadFile = File(...)) -> dict[str, object]:
    TMP_DIR.mkdir(parents=True, exist_ok=True)
    suffix = Path(audio.filename or "audio.webm").suffix or ".webm"
    audio_path = TMP_DIR / f"capture-{time.time_ns()}{suffix}"
    audio_path.write_bytes(await audio.read())
    try:
        result = speech_service.transcribe(audio_path)
    finally:
        audio_path.unlink(missing_ok=True)
    return result


@app.post("/api/speech/synthesize", response_model=None)
async def synthesize_speech(request: TTSRequest):
    audio_path = speech_service.synthesize(request.text[:1200])
    if audio_path is None:
        return {"available": False, "engine": "browser-fallback"}
    return FileResponse(
        audio_path,
        media_type="audio/mp4",
        filename="fieldvoice-response.m4a",
        background=BackgroundTask(lambda: os.unlink(audio_path) if audio_path.exists() else None),
    )


@app.get("/api/equipment", response_model=list[Equipment])
async def equipment() -> list[Equipment]:
    return catalog.equipment


@app.post("/api/ingest", response_model=IngestResponse)
async def ingest(request: IngestRequest) -> IngestResponse:
    response = await process_ingest(request)
    await event_hub.publish(
        EventType.INGESTED,
        {"client_uuid": request.client_uuid, "intent": response.intent, "worker_id": request.worker_id},
    )
    return response


@app.post("/api/query", response_model=QueryResponse)
async def query(request: QueryRequest) -> QueryResponse:
    response = knowledge_base.answer(request.query, request.equipment_code)
    await event_hub.publish(EventType.QUERY_ANSWERED, response.model_dump())
    return response


@app.post("/api/sync", response_model=SyncResponse)
async def sync(request: SyncRequest) -> SyncResponse:
    results: list[IngestResponse] = []
    duplicates = 0
    for item in request.items:
        result = await process_ingest(item)
        duplicates += 1 if result.idempotent else 0
        results.append(result)
    response = SyncResponse(processed=len(results), duplicates=duplicates, results=results)
    await event_hub.publish(EventType.SYNC_COMPLETED, response.model_dump())
    return response


@app.get("/api/work-orders", response_model=list[WorkOrder])
async def list_work_orders(status: WorkOrderStatus | None = Query(default=None)) -> list[WorkOrder]:
    return repository.list_work_orders(status)


@app.post("/api/work-orders", response_model=WorkOrder)
async def create_work_order(order: WorkOrder) -> WorkOrder:
    created, duplicate = repository.create_work_order(order)
    if duplicate:
        return created
    await event_hub.publish(EventType.WORK_ORDER_CREATED, created.model_dump(mode="json"))
    return created


@app.patch("/api/work-orders/{order_id}", response_model=WorkOrder)
async def update_work_order(order_id: str, patch: WorkOrderPatch) -> WorkOrder:
    if not repository.work_order_exists(order_id):
        raise HTTPException(status_code=404, detail="Work order not found")
    updated = repository.update_work_order(order_id, patch)
    event_type = {
        WorkOrderStatus.ESCALATED: EventType.WORK_ORDER_ESCALATED,
        WorkOrderStatus.CLOSED: EventType.WORK_ORDER_CLOSED,
    }.get(updated.status, EventType.WORK_ORDER_UPDATED)
    await event_hub.publish(event_type, updated.model_dump(mode="json"))
    return updated


@app.get("/api/dashboard/stats", response_model=DashboardStats)
async def dashboard_stats() -> DashboardStats:
    return repository.stats()


@app.websocket("/api/events")
async def events(websocket: WebSocket) -> None:
    await websocket.accept()
    queue = await event_hub.subscribe()
    try:
        await websocket.send_json({"type": "CONNECTED", "payload": {"message": "Live supervisor channel ready"}})
        while True:
            message = await queue.get()
            await websocket.send_json(message)
    except WebSocketDisconnect:
        event_hub.unsubscribe(queue)
    except asyncio.CancelledError:
        event_hub.unsubscribe(queue)
        raise


async def process_ingest(request: IngestRequest) -> IngestResponse:
    start = time.perf_counter()
    transcript = request.transcript or simulate_transcription(request.audio_base64)
    should_use_openai = request.command_mode in {None, "create_work_order"}
    ai_result = (
        openai_orchestrator.orchestrate(transcript, request.client_uuid, request.worker_id)
        if should_use_openai
        else None
    )
    intent = request.command_mode or (ai_result.intent if ai_result else infer_intent(transcript, None))

    if intent == "query":
        answer = knowledge_base.answer(transcript)
        note = VoiceNote(
            client_uuid=request.client_uuid,
            worker_id=request.worker_id,
            transcript=transcript,
            status="QUERY_ANSWERED",
        )
        repository.add_voice_note(note)
        return IngestResponse(
            intent=intent,
            transcript=transcript,
            spoken_confirmation=answer.answer,
            answer=answer.answer,
            latency_ms=int((time.perf_counter() - start) * 1000),
        )

    if intent in {"escalate", "close"}:
        order = repository.latest_open_work_order()
        if not order:
            raise HTTPException(status_code=404, detail="No open work order found for voice command")
        status = WorkOrderStatus.ESCALATED if intent == "escalate" else WorkOrderStatus.CLOSED
        updated = repository.update_work_order(order.id, WorkOrderPatch(status=status))
        event_type = EventType.WORK_ORDER_ESCALATED if intent == "escalate" else EventType.WORK_ORDER_CLOSED
        await event_hub.publish(event_type, updated.model_dump(mode="json"))
        spoken = f"Work order {updated.id[:8]} is now {updated.status.lower()} for {updated.equipment_code}."
        repository.add_voice_note(
            VoiceNote(
                client_uuid=request.client_uuid,
                worker_id=request.worker_id,
                transcript=transcript,
                status=updated.status,
                result_ref=updated.id,
            )
        )
        return IngestResponse(
            intent=intent,
            transcript=transcript,
            spoken_confirmation=spoken,
            work_order=updated,
            latency_ms=int((time.perf_counter() - start) * 1000),
        )

    if ai_result and ai_result.work_order:
        extracted_order = ai_result.work_order
        missing_fields = ai_result.missing_fields
    else:
        extraction = extractor.extract_work_order(transcript, request.client_uuid, request.worker_id)
        extracted_order = extraction.work_order
        missing_fields = extraction.missing_fields
    created, duplicate = repository.create_work_order(WorkOrder(**extracted_order.model_dump()))
    note_duplicate = repository.add_voice_note(
        VoiceNote(
            client_uuid=request.client_uuid,
            worker_id=request.worker_id,
            transcript=transcript,
            status="DUPLICATE" if duplicate else "WORK_ORDER_CREATED",
            result_ref=created.id,
        )
    )
    if not duplicate:
        await event_hub.publish(EventType.WORK_ORDER_CREATED, created.model_dump(mode="json"))

    missing = f" Missing fields: {', '.join(missing_fields)}." if missing_fields else ""
    spoken = (
        f"Logged {created.severity.lower()} work order for {created.equipment_code}. "
        f"Fault {created.fault_code or 'not specified'}. "
        f"Parts required: {', '.join(created.parts_required) if created.parts_required else 'none'}."
        f"{missing}"
    )
    return IngestResponse(
        intent="create_work_order",
        transcript=transcript,
        spoken_confirmation=spoken,
        work_order=created,
        idempotent=duplicate or note_duplicate,
        latency_ms=int((time.perf_counter() - start) * 1000),
    )


def infer_intent(transcript: str, command_mode: str | None) -> str:
    if command_mode in {"query", "create_work_order", "escalate", "close"}:
        return command_mode
    lower = transcript.lower()
    if any(phrase in lower for phrase in ("escalate", "alert supervisor", "notify supervisor")):
        return "escalate"
    if any(phrase in lower for phrase in ("close work order", "mark closed", "resolved")):
        return "close"
    if lower.startswith(("what", "when", "how", "show", "tell")) or "maintenance history" in lower or "procedure" in lower:
        return "query"
    return "create_work_order"


def simulate_transcription(audio_base64: str | None) -> str:
    if audio_base64:
        return "Audio received. Transcript adapter placeholder used for local demo."
    return "No transcript supplied. Please provide voice text for the local demo."
