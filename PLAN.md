# Voice-First AI Assistant for Field Workers — Project Plan

> Assignment 11 (Voice AI) · 5 students · 15 + 3 bonus marks
> Hands-free intelligence for workers who cannot look at a screen.

A field technician must complete a full inspection report, query equipment
history, and escalate a fault — **all by voice, in under 3 minutes**.

See [ARCHITECTURE.md](ARCHITECTURE.md) for system design, data flow, and the
work-order schema.

---

## 1. Success metrics = the grading rubric

Design backwards from these. Every phase below maps to one or more.

| # | Success metric | Forces us to build |
|---|----------------|--------------------|
| 1 | Acceptable transcription accuracy in *simulated noise* | Noise-robust STT + domain-vocabulary biasing |
| 2 | Correctly maps **all** required fields from a test voice note | Structured extraction → strict schema (LLM tool-calling) |
| 3 | Voice query returns correct answer **within 3 seconds** | RAG over a knowledge base + low-latency streaming TTS |
| 4 | Voice work-order creation → correctly structured backend record | Intent → tool-calling → DB write + verbal confirmation |
| 5 | Offline queue syncs & processes all queued notes on reconnect | Local queue, sync engine, idempotent processing |

---

## 2. Requirements

### Functional

- **FR1 — Domain-Aware Voice Capture**
  - Push-to-talk *and* continuous (VAD) capture
  - Noise robustness (rubric explicitly tests a noisy environment)
  - Domain vocabulary biasing: equipment codes (e.g. `PMP-204B`), technical terms, procedure names
  - Live partial-transcript feedback / audio cues
- **FR2 — Structured Data Extraction**
  - Voice note → work-order schema: `inspection_result`, `fault_code`, `location`, `severity`, `action_taken`, `parts_required`
  - Fill *all required fields*; confirm/flag missing ones by voice
  - Map noisy phrasing → canonical enum values ("running really hot" → `severity: HIGH`)
- **FR3 — Voice Query Answering**
  - Answer domain questions by voice (specs, maintenance history, procedure steps)
  - Retrieve from KB (RAG); respond in natural speech; **end-to-end < 3 s**
- **FR4 — Work Order Integration**
  - Create / update / close work orders by voice
  - Verbal confirmation before important writes
- **FR5 — Offline Capability**
  - Queue voice notes & commands offline; sync + process on reconnect
  - Idempotent, ordered, no data loss
- **FR6 — Supervisor Dashboard**
  - Web UI: real-time worker activity, WO status, voice-note transcripts, exception alerts

### Non-functional

- **Latency:** query round-trip < 3 s (hard); capture→extraction may be async
- **Hands-free:** every flow completable by voice alone
- **Robustness:** graceful under noise and intermittent connectivity
- **Auditability:** every note keeps raw audio + transcript + extracted record
- **Security:** auth per worker, scoped work orders

---

## 3. Tech stack (free / open-source)

Decision: **Python + FastAPI** backend, zero/near-zero API cost.

| Need | Choice | Notes |
|------|--------|-------|
| Field client | React + Vite **PWA**, Web Audio / MediaRecorder, IndexedDB | Offline-capable, installable, runs on a phone |
| STT | **faster-whisper** (`small`/`medium`), local | Free, offline, `initial_prompt` for domain biasing, noise-robust; doubles as offline-fallback STT |
| LLM (routing + extraction) | **Groq free tier** (Llama 3.3 70B) with tool-calling; **Ollama** (Llama 3.1 8B) local fallback | Fast → helps 3 s budget; real tool-calling/JSON for FR2; Ollama keeps demo alive with no API key |
| Embeddings / RAG | **sentence-transformers** (`all-MiniLM-L6-v2`) + **pgvector** | Free, CPU-friendly |
| TTS | **Piper** (local neural) + browser `SpeechSynthesis` fallback | Free, natural, offline |
| Backend | **FastAPI** + WebSockets | Async, great for streaming audio + LLM |
| Database | **PostgreSQL + pgvector** | One store: work orders + transcripts + audit + vectors |
| Dashboard | React + WebSocket client + chart lib | Real-time supervisor view |
| Offline queue | IndexedDB (client) + idempotent ingest (server) | Replay-safe via client UUIDs |
| Infra | Docker Compose (api + db + dashboard) | One-command demo, reproducible for grading |

> Fully-local alternative: swap Groq for Ollama everywhere → $0, fully offline,
> and showcases FR5. Slightly slower; profile against the 3 s budget.

---

## 4. Roadmap (4 phases)

### Phase 0 — Foundations (Day 1–2)
- Repo scaffold, Docker Compose, Postgres + pgvector schema
- Seed mock domain dataset (~10 equipment items: codes, specs, maintenance history, procedures) → becomes KB + grading fixtures
- Define canonical work-order JSON schema + severity/fault enums

### Phase 1 — Voice pipeline vertical slice (Day 3–6)
- Client mic capture (push-to-talk first) → backend
- STT + domain-prompt biasing → transcript
- LLM extraction → structured record → DB write
- ✅ Metrics **1 & 2**

### Phase 2 — Query + work-order actions (Day 7–10)
- RAG: embed KB, retrieval endpoint
- Intent router (tool-use): query vs. create/update/close
- Streaming TTS reply; tune the **3 s** budget
- Verbal confirmation flow for writes
- ✅ Metrics **3 & 4**

### Phase 3 — Offline + dashboard (Day 11–14)
- Client IndexedDB queue + sync engine; idempotent ingest
- Supervisor dashboard: live activity (WebSocket), WO status, transcripts, alerts
- ✅ Metric **5** + FR6

### Phase 4 — Hardening & demo (Day 15–16)
- Noise testing (background noise into mic), measure WER
- Latency profiling, end-to-end 3-min flow rehearsal
- **Bonus (3 marks):** one of — continuous VAD/wake-word, multilingual, on-device fallback STT, speaker ID
- Demo script + metrics evidence table

### Role split (5 people)
1. Voice/STT + client capture (FR1)
2. LLM extraction + intent/tool-calling (FR2, FR4)
3. RAG + KB + TTS query path (FR3)
4. Offline queue + sync + backend/DB (FR5, infra)
5. Supervisor dashboard + WebSockets + integration/testing (FR6)

---

## 5. End-to-end walkthrough (the 3-minute demo)

**Scenario: technician inspecting pump PMP-204B**

1. **Capture** — Push-to-talk: *"Inspecting pump P-M-P 204 Bravo. Bearing temperature high, fault code F-12, action: applied coolant, need replacement seal kit, severity high."*
2. **STT + biasing** — Whisper transcribes; equipment-code normalizer maps "P-M-P 204 Bravo" → `PMP-204B` against the registry.
3. **Extraction** — LLM tool-call returns:
   ```json
   { "equipment": "PMP-204B", "inspection_result": "bearing temp high",
     "fault_code": "F12", "location": "...", "severity": "HIGH",
     "action_taken": "applied coolant", "parts_required": ["seal kit"] }
   ```
4. **Confirm** — TTS: *"Logging fault F12 on PMP-204B, severity high, seal kit required. Create work order?"* → *"Yes."* → WO written.
5. **Query** — *"What's the last maintenance date for this pump?"* → RAG → TTS answers in **< 3 s**.
6. **Escalate** — *"Escalate this fault to supervisor."* → WO flagged, exception alert pushed to dashboard via WebSocket.
7. **Supervisor** sees the new high-severity WO, transcript, and alert live.
8. **Offline path** — Disable network mid-demo, record a note (queued in IndexedDB), reconnect → syncs and processes automatically.
