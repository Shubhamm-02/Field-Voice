# FieldVoice AI Assistant

Voice-first field worker assistant for Assignment 11. The project demonstrates a backend-heavy implementation: push-to-talk capture, STT/TTS adapters, spoken confirmations, OpenAI-backed intent and structured extraction, RAG-style knowledge lookup, idempotent offline sync, SQLite persistence, and live supervisor events.

## Run

```bash
python3 -m uvicorn backend.app.main:app --port 8000
```

Open `http://127.0.0.1:8000` for the supervisor dashboard.

## Test

```bash
python3 -m pytest
```

## Backend Highlights

- `POST /api/ingest` accepts transcript or future audio payloads, infers intent, extracts a canonical work-order schema, and stores an audit voice note.
- OpenAI is integrated for intent routing and structured work-order extraction when `OPENAI_API_KEY` is set, with local fallback if unavailable.
- `GET /api/ai/status` reports whether the OpenAI path is active.
- `POST /api/query` answers equipment specs, maintenance history, and procedure questions from the seeded backend knowledge catalog.
- `GET /api/speech/status` reports the active STT/TTS engines.
- `POST /api/speech/transcribe` accepts recorded push-to-talk audio and uses `faster-whisper` when installed.
- `POST /api/speech/synthesize` returns spoken confirmation audio using macOS `say` when available, with browser TTS fallback.
- `POST /api/sync` replays offline commands with client UUID idempotency, so repeated syncs do not create duplicate work orders.
- `PATCH /api/work-orders/{id}` supports status changes such as escalation and closure.
- `WS /api/events` pushes live activity and alerts to the dashboard.
- SQLite stores work orders and voice-note audit records in `data/fieldvoice.db`.

## STT/TTS

Current local behavior:

- STT: browser Web Speech fallback unless `faster-whisper` is installed.
- TTS: backend macOS `say` audio when available, otherwise browser `SpeechSynthesis`.
- Push-to-talk: hold the voice button, speak, and release to stop recording.

To enable backend Whisper STT:

```bash
python3 -m pip install faster-whisper
```

## OpenAI Integration

The assignment requires at least one of OpenAI, Claude, or Gemini. This project uses OpenAI for:

- intent routing: create/query/escalate/close
- structured extraction: transcript to work-order JSON

Set your API key in `.env.local`, `.env`, or export it before starting the server:

```bash
cp .env.example .env.local
# edit .env.local and paste your key
python3 -m uvicorn backend.app.main:app --port 8000
```

```bash
export OPENAI_API_KEY="your_key_here"
python3 -m uvicorn backend.app.main:app --port 8000
```

Optional model override:

```bash
export OPENAI_MODEL="gpt-4.1-mini"
```

Verify:

```bash
curl http://127.0.0.1:8000/api/ai/status
```

## Demo Script

1. Hold the orange mic and speak an inspection note, or use the default transcript and click **Create work order**.
2. Ask: `What is the last maintenance date for PMP-204B?`
3. Click **Escalate** and watch the latest open order update.
4. Use **Go offline** to queue commands, then the same button becomes the online/sync control.
