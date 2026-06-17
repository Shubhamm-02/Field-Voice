# Database Design

FieldVoice uses SQLite for local demo persistence. The database file is created automatically at:

```text
data/fieldvoice.db
```

SQLite was chosen because it requires no external setup and still demonstrates real backend persistence, table design, uniqueness constraints, indexes, and idempotent offline replay.

## Tables

### work_orders

Stores structured inspection records created from voice transcripts.

Important columns:

- `id`: primary key UUID
- `client_uuid`: unique idempotency key from the browser/offline queue
- `equipment_code`: normalized equipment code such as `PMP-204B`
- `inspection_result`: extracted inspection summary
- `fault_code`: normalized fault code such as `F12`
- `location`: equipment or spoken field location
- `severity`: `LOW`, `MEDIUM`, `HIGH`, or `CRITICAL`
- `action_taken`: technician action extracted from speech
- `parts_required`: JSON array stored as text
- `status`: `OPEN`, `IN_PROGRESS`, `ESCALATED`, or `CLOSED`
- `created_by`: worker id
- `created_at`, `updated_at`: audit timestamps
- `transcript`: original transcript for auditability

Indexes:

- `idx_work_orders_status`
- `idx_work_orders_created_at`

### voice_notes

Stores an audit record for each processed voice command or queued offline item.

Important columns:

- `client_uuid`: primary key and replay guard
- `worker_id`: field worker id
- `transcript`: raw transcript
- `status`: processing outcome
- `processed_at`: audit timestamp
- `result_ref`: linked work order id when applicable

Indexes:

- `idx_voice_notes_processed_at`

## Backend Layer

The database access layer is implemented in:

```text
backend/app/repository.py
```

The repository exposes methods used by the FastAPI routes:

- `create_work_order`
- `update_work_order`
- `list_work_orders`
- `latest_open_work_order`
- `add_voice_note`
- `stats`
- `reset` for tests

## Idempotent Offline Sync

Offline sync uses `client_uuid` as a unique key. If the browser replays the same queued command twice, SQLite prevents duplicate work-order creation because `work_orders.client_uuid` is unique.

