from __future__ import annotations

import re
import time
from dataclasses import dataclass
from pathlib import Path

from backend.app.models import QueryResponse
from backend.app.services.domain import DomainCatalog

ROOT = Path(__file__).resolve().parents[3]
FIELD_WORK_KB_PATH = ROOT / "data" / "field_work_india_kb.md"
GENERAL_EQUIPMENT = "GENERAL"


@dataclass(frozen=True)
class KnowledgeChunk:
    source: str
    equipment_code: str
    text: str


class KnowledgeBase:
    def __init__(self, catalog: DomainCatalog) -> None:
        self.catalog = catalog
        self.chunks = self._build_chunks()

    def answer(self, query: str, equipment_code: str | None = None) -> QueryResponse:
        start = time.perf_counter()
        matches = self.search(query, equipment_code)
        if not matches:
            answer = "I could not find that in the field knowledge base. I have flagged it for supervisor review."
            sources: list[str] = []
        else:
            answer = synthesize_answer(query, matches)
            sources = [match.source for match in matches[:3]]
        return QueryResponse(
            answer=answer,
            sources=sources,
            latency_ms=int((time.perf_counter() - start) * 1000),
        )

    def search(self, query: str, equipment_code: str | None = None, limit: int = 3) -> list[KnowledgeChunk]:
        query_tokens = tokens(query)
        scored: list[tuple[int, KnowledgeChunk]] = []
        for chunk in self.chunks:
            if equipment_code and chunk.equipment_code not in {equipment_code, GENERAL_EQUIPMENT}:
                continue
            score = len(query_tokens & tokens(chunk.text))
            if chunk.equipment_code.lower() in query.lower():
                score += 3
            if chunk.equipment_code == GENERAL_EQUIPMENT:
                score += len(query_tokens & tokens(chunk.source.replace("-", " ")))
            if "maintenance" in query_tokens and chunk.source.startswith("maintenance:"):
                score += 6
            if {"last", "maintenance"} <= query_tokens and chunk.source.startswith("field-kb:"):
                score -= 2
            if score:
                scored.append((score, chunk))
        scored.sort(key=lambda item: item[0], reverse=True)
        return [chunk for _, chunk in scored[:limit]]

    def _build_chunks(self) -> list[KnowledgeChunk]:
        chunks: list[KnowledgeChunk] = []
        for equipment in self.catalog.equipment:
            specs = ", ".join(f"{key}: {value}" for key, value in equipment.specs.items())
            chunks.append(
                KnowledgeChunk(
                    source=f"equipment:{equipment.code}",
                    equipment_code=equipment.code,
                    text=f"{equipment.code} {equipment.name} is located at {equipment.location}. Specifications: {specs}.",
                )
            )
        for record in self.catalog.maintenance:
            chunks.append(
                KnowledgeChunk(
                    source=f"maintenance:{record.equipment_code}:{record.date}",
                    equipment_code=record.equipment_code,
                    text=f"On {record.date}, {record.equipment_code} maintenance action was {record.action}. Notes: {record.notes}.",
                )
            )
        for procedure in self.catalog.procedures:
            chunks.append(
                KnowledgeChunk(
                    source=f"procedure:{procedure.name}",
                    equipment_code=procedure.equipment_code,
                    text=f"Procedure {procedure.name} for {procedure.equipment_code}: {' '.join(procedure.steps)}",
                )
            )
        chunks.extend(load_markdown_knowledge_chunks(FIELD_WORK_KB_PATH))
        return chunks


def tokens(text: str) -> set[str]:
    return {token for token in re.findall(r"[a-z0-9]+", text.lower()) if len(token) > 2}


def load_markdown_knowledge_chunks(path: Path) -> list[KnowledgeChunk]:
    if not path.exists():
        return []
    chunks: list[KnowledgeChunk] = []
    current_heading = "FieldVoice India Field Work Knowledge Base"
    current_lines: list[str] = []
    for line in path.read_text().splitlines():
        if line.startswith("## "):
            append_markdown_chunk(chunks, current_heading, current_lines)
            current_heading = line.removeprefix("## ").strip()
            current_lines = []
        elif line.startswith("# "):
            continue
        else:
            current_lines.append(line)
    append_markdown_chunk(chunks, current_heading, current_lines)
    return chunks


def append_markdown_chunk(chunks: list[KnowledgeChunk], heading: str, lines: list[str]) -> None:
    text = clean_markdown_text("\n".join(lines))
    if not text:
        return
    chunks.append(
        KnowledgeChunk(
            source=f"field-kb:{slugify(heading)}",
            equipment_code=detect_equipment_code(text),
            text=f"{heading}: {text}",
        )
    )


def clean_markdown_text(text: str) -> str:
    text = re.sub(r"```.*?```", " ", text, flags=re.S)
    text = re.sub(r"^[#>*-]+\s*", "", text, flags=re.M)
    text = re.sub(r"\n+", " ", text)
    return re.sub(r"\s+", " ", text).strip()


def slugify(value: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", value.lower()).strip("-")


def detect_equipment_code(text: str) -> str:
    match = re.search(r"\b[A-Z]{2,5}-[A-Z0-9-]{2,}\b", text)
    return match.group(0) if match else GENERAL_EQUIPMENT


def synthesize_answer(query: str, matches: list[KnowledgeChunk]) -> str:
    lower = query.lower()
    if "last" in lower and "maintenance" in lower:
        maintenance = [chunk for chunk in matches if chunk.source.startswith("maintenance:")]
        if maintenance:
            return maintenance[0].text
    if "procedure" in lower or "steps" in lower or "how" in lower:
        procedure = [chunk for chunk in matches if chunk.source.startswith("procedure:")]
        if procedure:
            return procedure[0].text
    if "spec" in lower or "pressure" in lower or "flow" in lower or "rating" in lower:
        equipment = [chunk for chunk in matches if chunk.source.startswith("equipment:")]
        if equipment:
            return equipment[0].text
    field_kb = [chunk for chunk in matches if chunk.source.startswith("field-kb:")]
    if field_kb:
        return field_kb[0].text
    supporting = " ".join(chunk.text for chunk in matches[:2])
    return supporting
