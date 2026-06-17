from __future__ import annotations

import re
from dataclasses import dataclass

from backend.app.models import Severity, WorkOrderCreate
from backend.app.services.domain import DomainCatalog


FAULT_RE = re.compile(r"\b(?:fault\s*code|fault|code)\s*[:#-]?\s*([a-z]\s*-?\s*\d{1,3})\b", re.I)
EQUIPMENT_RE = re.compile(r"\b([a-z]{2,4})[\s-]*(\d{2,4})[\s-]*(?:([a-z])|bravo|alpha|charlie|delta)?\b", re.I)
PARTS_RE = re.compile(r"\b(?:need|needs|required|requires|parts? required|replace with)\s+([^.;]+)", re.I)
ACTION_RE = re.compile(r"\b(?:action|action taken|applied|performed|did|completed)\s*[:\-]?\s*([^.;]+)", re.I)
LOCATION_RE = re.compile(r"\b(?:at|in|location)\s+([a-z0-9\- ]+(?:bay|plant|room|zone|line|station|unit)\s*[a-z0-9\-]*)", re.I)

CODE_WORDS = {
    "alpha": "A",
    "bravo": "B",
    "charlie": "C",
    "delta": "D",
}


@dataclass(frozen=True)
class ExtractionResult:
    work_order: WorkOrderCreate
    missing_fields: list[str]
    confidence: float


class VoiceExtractor:
    def __init__(self, catalog: DomainCatalog) -> None:
        self.catalog = catalog

    def extract_work_order(self, transcript: str, client_uuid: str, worker_id: str) -> ExtractionResult:
        text = clean_transcript(transcript)
        equipment_code = self._extract_equipment_code(text)
        equipment = self.catalog.equipment_by_code.get(equipment_code)

        fault_code = extract_fault_code(text)
        location = extract_location(text) or (equipment.location if equipment else "Unknown field location")
        severity = extract_severity(text)
        action_taken = extract_action(text)
        parts_required = extract_parts(text)
        inspection_result = extract_inspection_result(text, fault_code, action_taken)

        missing_fields = []
        if equipment_code == "UNKNOWN":
            missing_fields.append("equipment_code")
        if not inspection_result:
            missing_fields.append("inspection_result")
        if not action_taken:
            missing_fields.append("action_taken")

        work_order = WorkOrderCreate(
            client_uuid=client_uuid,
            equipment_code=equipment_code,
            inspection_result=inspection_result or "Inspection note captured for review",
            fault_code=fault_code,
            location=location,
            severity=severity,
            action_taken=action_taken or "Pending technician action",
            parts_required=parts_required,
            created_by=worker_id,
            transcript=transcript,
        )
        confidence = max(0.25, 1.0 - (len(missing_fields) * 0.22))
        return ExtractionResult(work_order=work_order, missing_fields=missing_fields, confidence=confidence)

    def _extract_equipment_code(self, text: str) -> str:
        compact = re.sub(r"[^a-z0-9]", "", text.lower())
        for code in self.catalog.equipment_by_code:
            if code.lower().replace("-", "") in compact:
                return code

        match = EQUIPMENT_RE.search(text)
        if not match:
            return "UNKNOWN"
        prefix, number, suffix = match.groups()
        normalized_suffix = (suffix or "").upper()
        for word, letter in CODE_WORDS.items():
            if word in match.group(0).lower():
                normalized_suffix = letter
        candidate = f"{prefix.upper()}-{number}{normalized_suffix}"
        return candidate if candidate in self.catalog.equipment_by_code else "UNKNOWN"


def clean_transcript(transcript: str) -> str:
    return re.sub(r"\s+", " ", transcript.strip())


def extract_fault_code(text: str) -> str | None:
    match = FAULT_RE.search(text)
    if not match:
        return None
    return re.sub(r"[^A-Z0-9]", "", match.group(1).upper())


def extract_severity(text: str) -> Severity:
    lower = text.lower()
    if any(term in lower for term in ("critical", "shutdown", "unsafe", "fire", "leak major")):
        return Severity.CRITICAL
    if any(term in lower for term in ("high", "hot", "overheat", "urgent", "severe", "bearing temperature")):
        return Severity.HIGH
    if any(term in lower for term in ("low", "minor", "observe", "watch")):
        return Severity.LOW
    return Severity.MEDIUM


def extract_parts(text: str) -> list[str]:
    match = PARTS_RE.search(text)
    if not match:
        return []
    parts_phrase = re.split(r"\b(?:severity|fault|action|location)\b", match.group(1), maxsplit=1, flags=re.I)[0]
    raw = re.split(r",| and ", parts_phrase)
    return [part.strip(" .") for part in raw if part.strip(" .")]


def extract_action(text: str) -> str:
    match = ACTION_RE.search(text)
    if match:
        return match.group(1).strip(" .")
    lower = text.lower()
    for verb in ("applied coolant", "replaced filter", "tightened coupling", "isolated unit"):
        if verb in lower:
            return verb
    return ""


def extract_location(text: str) -> str | None:
    match = LOCATION_RE.search(text)
    return match.group(1).strip(" .").title() if match else None


def extract_inspection_result(text: str, fault_code: str | None, action_taken: str) -> str:
    result = text
    for marker in ("action", "need", "needs", "parts required"):
        marker_index = result.lower().find(marker)
        if marker_index > 20:
            result = result[:marker_index]
            break
    result = re.sub(r"\b(inspecting|inspection for|create work order for|log|record)\b", "", result, flags=re.I)
    if fault_code:
        result = re.sub(FAULT_RE, "", result)
    return result.strip(" .,:-")
