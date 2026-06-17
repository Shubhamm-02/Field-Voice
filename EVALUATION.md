# FieldVoice Evaluation Checklist

This file maps Assignment 11 requirements to implemented project evidence.

## Mandatory AI Integration

- Platform used: OpenAI
- Model default: `gpt-4.1-mini`
- Backend status endpoint: `GET /api/ai/status`
- Current use: intent routing and structured work-order extraction from field-worker voice transcripts
- Fallback: local rule-based extraction if the API key or network is unavailable

## Core Feature Coverage

| Requirement | Status | Evidence |
| --- | --- | --- |
| Domain-aware voice capture | Done | Push-to-talk mic, browser audio constraints, faster-whisper backend, domain vocabulary prompt in `/api/speech/status` |
| Structured data extraction | Done | `/api/ingest` maps transcript to inspection result, fault code, location, severity, action taken, parts required |
| Voice query answering | Done | `/api/query` retrieves equipment specs, maintenance history, and procedure steps; UI speaks answer back |
| Work order integration | Done | Voice commands create, escalate, and close work orders in SQLite |
| Offline capability | Done | UI queues commands offline and `/api/sync` processes them with idempotency |
| Supervisor dashboard | Done | Web dashboard shows metrics, activity, work orders, transcripts, status, and alerts |

## Success Metric Evidence

| Metric | How to test | Expected result |
| --- | --- | --- |
| Voice capture acceptable in simulated noise | Install `faster-whisper`, hold mic, speak a field note with equipment/fault terms | Transcript appears in the transcript box |
| Structured extraction maps required fields | Say or paste: `Inspecting pump PMP 204 Bravo. Bearing temperature high, fault code F-12. Action applied coolant. Need replacement seal kit, severity high.` | Work order includes equipment, fault, severity, action, parts, transcript |
| Voice query returns correct answer under 3 seconds | Ask: `What is the last maintenance date for PMP-204B?` | Answer includes `2026-05-18`; automated test asserts latency under 3000 ms |
| Work order creation by voice creates backend record | Click `Create work order` after voice/text input | New card appears in work orders and persists in SQLite |
| Offline queue syncs correctly | Toggle offline, create command, toggle back online/sync | Queued command is processed once; duplicate replay is ignored |

## Automated Test Coverage

Run:

```bash
python3 -m pytest
```

Current result:

```text
11 passed
```

Covered tests include API health, OpenAI status, OpenAI-backed extraction path, STT/TTS status, transcription fallback, RAG query latency, offline sync idempotency, and work-order closure.
