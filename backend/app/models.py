from __future__ import annotations

from datetime import datetime, timezone
from enum import StrEnum
from typing import Any
from uuid import uuid4

from pydantic import BaseModel, Field


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


class Severity(StrEnum):
    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"
    CRITICAL = "CRITICAL"


class WorkOrderStatus(StrEnum):
    OPEN = "OPEN"
    IN_PROGRESS = "IN_PROGRESS"
    ESCALATED = "ESCALATED"
    CLOSED = "CLOSED"


class EventType(StrEnum):
    INGESTED = "INGESTED"
    WORK_ORDER_CREATED = "WORK_ORDER_CREATED"
    WORK_ORDER_UPDATED = "WORK_ORDER_UPDATED"
    WORK_ORDER_ESCALATED = "WORK_ORDER_ESCALATED"
    WORK_ORDER_CLOSED = "WORK_ORDER_CLOSED"
    QUERY_ANSWERED = "QUERY_ANSWERED"
    SYNC_COMPLETED = "SYNC_COMPLETED"


class WorkOrderCreate(BaseModel):
    client_uuid: str = Field(default_factory=lambda: str(uuid4()))
    equipment_code: str
    inspection_result: str
    fault_code: str | None = None
    location: str
    severity: Severity = Severity.MEDIUM
    action_taken: str
    parts_required: list[str] = Field(default_factory=list)
    created_by: str = "worker-demo"
    raw_audio_ref: str | None = None
    transcript: str


class WorkOrderPatch(BaseModel):
    inspection_result: str | None = None
    fault_code: str | None = None
    location: str | None = None
    severity: Severity | None = None
    action_taken: str | None = None
    parts_required: list[str] | None = None
    status: WorkOrderStatus | None = None


class WorkOrder(WorkOrderCreate):
    id: str = Field(default_factory=lambda: str(uuid4()))
    status: WorkOrderStatus = WorkOrderStatus.OPEN
    created_at: datetime = Field(default_factory=utc_now)
    updated_at: datetime = Field(default_factory=utc_now)


class VoiceNote(BaseModel):
    client_uuid: str
    worker_id: str
    transcript: str
    status: str
    processed_at: datetime = Field(default_factory=utc_now)
    raw_audio_ref: str | None = None
    result_ref: str | None = None


class IngestRequest(BaseModel):
    client_uuid: str = Field(default_factory=lambda: str(uuid4()))
    worker_id: str = "worker-demo"
    transcript: str | None = None
    audio_base64: str | None = None
    command_mode: str | None = None


class IngestResponse(BaseModel):
    intent: str
    transcript: str
    spoken_confirmation: str
    work_order: WorkOrder | None = None
    answer: str | None = None
    idempotent: bool = False
    latency_ms: int


class QueryRequest(BaseModel):
    query: str
    equipment_code: str | None = None


class QueryResponse(BaseModel):
    answer: str
    sources: list[str]
    latency_ms: int


class SyncRequest(BaseModel):
    items: list[IngestRequest]


class SyncResponse(BaseModel):
    processed: int
    duplicates: int
    results: list[IngestResponse]


class Equipment(BaseModel):
    code: str
    name: str
    location: str
    specs: dict[str, Any]
    vocabulary: list[str] = Field(default_factory=list)


class MaintenanceRecord(BaseModel):
    equipment_code: str
    date: str
    action: str
    notes: str


class Procedure(BaseModel):
    name: str
    equipment_code: str
    steps: list[str]


class DashboardStats(BaseModel):
    total_work_orders: int
    open_work_orders: int
    escalated_work_orders: int
    critical_or_high: int
    voice_notes: int

