from __future__ import annotations

import json
import os
import urllib.error
import urllib.request
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from pydantic import BaseModel, Field, ValidationError

from backend.app.models import Severity, WorkOrderCreate
from backend.app.services.domain import DomainCatalog

OPENAI_RESPONSES_URL = "https://api.openai.com/v1/responses"
PROJECT_ROOT = Path(__file__).resolve().parents[3]
ENV_PATHS = (PROJECT_ROOT / ".env.local", PROJECT_ROOT / ".env")


class OpenAIExtraction(BaseModel):
    intent: str = Field(pattern="^(create_work_order|query|escalate|close)$")
    equipment_code: str = "UNKNOWN"
    inspection_result: str = "Inspection note captured for review"
    fault_code: str | None = None
    location: str = "Unknown field location"
    severity: Severity = Severity.MEDIUM
    action_taken: str = "Pending technician action"
    parts_required: list[str] = Field(default_factory=list)
    missing_fields: list[str] = Field(default_factory=list)


@dataclass(frozen=True)
class OpenAIOrchestrationResult:
    intent: str
    work_order: WorkOrderCreate | None
    missing_fields: list[str]
    model: str


class OpenAIOrchestrator:
    def __init__(self, catalog: DomainCatalog) -> None:
        load_local_env()
        self.catalog = catalog
        self.model = os.getenv("OPENAI_MODEL", "gpt-4.1-mini")

    @property
    def available(self) -> bool:
        return bool(os.getenv("OPENAI_API_KEY"))

    def status(self) -> dict[str, Any]:
        return {
            "provider": "OpenAI",
            "available": self.available,
            "model": self.model,
            "used_for": ["intent_routing", "structured_work_order_extraction"],
        }

    def orchestrate(self, transcript: str, client_uuid: str, worker_id: str) -> OpenAIOrchestrationResult | None:
        if not self.available:
            return None
        try:
            extraction = self._request_extraction(transcript)
        except (OSError, urllib.error.URLError, urllib.error.HTTPError, TimeoutError, KeyError, json.JSONDecodeError, ValidationError):
            return None

        work_order: WorkOrderCreate | None = None
        if extraction.intent == "create_work_order":
            work_order = WorkOrderCreate(
                client_uuid=client_uuid,
                equipment_code=extraction.equipment_code,
                inspection_result=extraction.inspection_result,
                fault_code=extraction.fault_code,
                location=extraction.location,
                severity=extraction.severity,
                action_taken=extraction.action_taken,
                parts_required=extraction.parts_required,
                created_by=worker_id,
                transcript=transcript,
            )
        return OpenAIOrchestrationResult(
            intent=extraction.intent,
            work_order=work_order,
            missing_fields=extraction.missing_fields,
            model=self.model,
        )

    def _request_extraction(self, transcript: str) -> OpenAIExtraction:
        payload = {
            "model": self.model,
            "input": [
                {
                    "role": "system",
                    "content": [
                        {
                            "type": "input_text",
                            "text": (
                                "You route Indian industrial field-worker voice transcripts and extract work-order data. "
                                "Use known equipment codes when possible. Return only valid JSON matching the schema. "
                                f"Known vocabulary: {self.catalog.vocabulary_prompt}. "
                                f"Known equipment: {', '.join(self.catalog.equipment_by_code)}."
                            ),
                        }
                    ],
                },
                {
                    "role": "user",
                    "content": [{"type": "input_text", "text": transcript}],
                },
            ],
            "text": {
                "format": {
                    "type": "json_schema",
                    "name": "fieldvoice_orchestration",
                    "strict": True,
                    "schema": openai_schema(),
                }
            },
        }
        request = urllib.request.Request(
            OPENAI_RESPONSES_URL,
            data=json.dumps(payload).encode("utf-8"),
            headers={
                "Authorization": f"Bearer {os.environ['OPENAI_API_KEY']}",
                "Content-Type": "application/json",
            },
            method="POST",
        )
        with urllib.request.urlopen(request, timeout=12) as response:
            body = json.loads(response.read().decode("utf-8"))
        return OpenAIExtraction(**json.loads(extract_response_text(body)))


def extract_response_text(body: dict[str, Any]) -> str:
    if "output_text" in body:
        return body["output_text"]
    for item in body.get("output", []):
        for content in item.get("content", []):
            if content.get("type") in {"output_text", "text"} and "text" in content:
                return content["text"]
    raise KeyError("output_text")


def load_local_env() -> None:
    for env_path in ENV_PATHS:
        if not env_path.exists():
            continue
        for line in env_path.read_text().splitlines():
            stripped = line.strip()
            if not stripped or stripped.startswith("#") or "=" not in stripped:
                continue
            key, value = stripped.split("=", 1)
            os.environ.setdefault(key.strip(), value.strip().strip('"').strip("'"))


def openai_schema() -> dict[str, Any]:
    return {
        "type": "object",
        "additionalProperties": False,
        "properties": {
            "intent": {"type": "string", "enum": ["create_work_order", "query", "escalate", "close"]},
            "equipment_code": {"type": "string"},
            "inspection_result": {"type": "string"},
            "fault_code": {"type": ["string", "null"]},
            "location": {"type": "string"},
            "severity": {"type": "string", "enum": [item.value for item in Severity]},
            "action_taken": {"type": "string"},
            "parts_required": {"type": "array", "items": {"type": "string"}},
            "missing_fields": {"type": "array", "items": {"type": "string"}},
        },
        "required": [
            "intent",
            "equipment_code",
            "inspection_result",
            "fault_code",
            "location",
            "severity",
            "action_taken",
            "parts_required",
            "missing_fields",
        ],
    }
