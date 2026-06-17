from __future__ import annotations

import json
import os
import sqlite3
from pathlib import Path
from typing import Any

from backend.app.models import DashboardStats, VoiceNote, WorkOrder, WorkOrderPatch, WorkOrderStatus, utc_now

ROOT = Path(__file__).resolve().parents[2]
DB_PATH = Path(os.getenv("FIELDVOICE_DB_PATH", ROOT / "data" / "fieldvoice.db"))


class Repository:
    def __init__(self, db_path: Path = DB_PATH) -> None:
        self.db_path = db_path
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self.initialize()

    def connect(self) -> sqlite3.Connection:
        connection = sqlite3.connect(self.db_path)
        connection.row_factory = sqlite3.Row
        connection.execute("PRAGMA foreign_keys = ON")
        return connection

    def initialize(self) -> None:
        with self.connect() as connection:
            connection.executescript(
                """
                CREATE TABLE IF NOT EXISTS work_orders (
                    id TEXT PRIMARY KEY,
                    client_uuid TEXT NOT NULL UNIQUE,
                    equipment_code TEXT NOT NULL,
                    inspection_result TEXT NOT NULL,
                    fault_code TEXT,
                    location TEXT NOT NULL,
                    severity TEXT NOT NULL,
                    action_taken TEXT NOT NULL,
                    parts_required TEXT NOT NULL DEFAULT '[]',
                    status TEXT NOT NULL,
                    created_by TEXT NOT NULL,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL,
                    raw_audio_ref TEXT,
                    transcript TEXT NOT NULL
                );

                CREATE INDEX IF NOT EXISTS idx_work_orders_status
                    ON work_orders(status);

                CREATE INDEX IF NOT EXISTS idx_work_orders_created_at
                    ON work_orders(created_at DESC);

                CREATE TABLE IF NOT EXISTS voice_notes (
                    client_uuid TEXT PRIMARY KEY,
                    worker_id TEXT NOT NULL,
                    transcript TEXT NOT NULL,
                    status TEXT NOT NULL,
                    processed_at TEXT NOT NULL,
                    raw_audio_ref TEXT,
                    result_ref TEXT,
                    FOREIGN KEY(result_ref) REFERENCES work_orders(id)
                        ON DELETE SET NULL
                );

                CREATE INDEX IF NOT EXISTS idx_voice_notes_processed_at
                    ON voice_notes(processed_at DESC);
                """
            )

    def reset(self) -> None:
        with self.connect() as connection:
            connection.execute("DELETE FROM voice_notes")
            connection.execute("DELETE FROM work_orders")

    def work_order_exists(self, order_id: str) -> bool:
        with self.connect() as connection:
            row = connection.execute(
                "SELECT 1 FROM work_orders WHERE id = ?",
                (order_id,),
            ).fetchone()
        return row is not None

    def create_work_order(self, order: WorkOrder) -> tuple[WorkOrder, bool]:
        existing = self.get_work_order_by_client_uuid(order.client_uuid)
        if existing:
            return existing, True

        with self.connect() as connection:
            connection.execute(
                """
                INSERT INTO work_orders (
                    id, client_uuid, equipment_code, inspection_result,
                    fault_code, location, severity, action_taken, parts_required,
                    status, created_by, created_at, updated_at, raw_audio_ref,
                    transcript
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                work_order_to_row(order),
            )
        return order, False

    def get_work_order_by_client_uuid(self, client_uuid: str) -> WorkOrder | None:
        with self.connect() as connection:
            row = connection.execute(
                "SELECT * FROM work_orders WHERE client_uuid = ?",
                (client_uuid,),
            ).fetchone()
        return row_to_work_order(row) if row else None

    def update_work_order(self, order_id: str, patch: WorkOrderPatch) -> WorkOrder:
        current = self.get_work_order(order_id)
        if not current:
            raise KeyError(order_id)

        updates = patch.model_dump(exclude_unset=True)
        updated = current.model_copy(update={**updates, "updated_at": utc_now()})
        with self.connect() as connection:
            connection.execute(
                """
                UPDATE work_orders
                SET inspection_result = ?,
                    fault_code = ?,
                    location = ?,
                    severity = ?,
                    action_taken = ?,
                    parts_required = ?,
                    status = ?,
                    updated_at = ?,
                    raw_audio_ref = ?,
                    transcript = ?
                WHERE id = ?
                """,
                (
                    updated.inspection_result,
                    updated.fault_code,
                    updated.location,
                    updated.severity,
                    updated.action_taken,
                    json.dumps(updated.parts_required),
                    updated.status,
                    updated.updated_at.isoformat(),
                    updated.raw_audio_ref,
                    updated.transcript,
                    updated.id,
                ),
            )
        return updated

    def get_work_order(self, order_id: str) -> WorkOrder | None:
        with self.connect() as connection:
            row = connection.execute(
                "SELECT * FROM work_orders WHERE id = ?",
                (order_id,),
            ).fetchone()
        return row_to_work_order(row) if row else None

    def list_work_orders(self, status: WorkOrderStatus | None = None) -> list[WorkOrder]:
        query = "SELECT * FROM work_orders"
        params: tuple[Any, ...] = ()
        if status is not None:
            query += " WHERE status = ?"
            params = (status,)
        query += " ORDER BY created_at DESC"
        with self.connect() as connection:
            rows = connection.execute(query, params).fetchall()
        return [row_to_work_order(row) for row in rows]

    def latest_open_work_order(self) -> WorkOrder | None:
        with self.connect() as connection:
            row = connection.execute(
                """
                SELECT * FROM work_orders
                WHERE status != ?
                ORDER BY created_at DESC
                LIMIT 1
                """,
                (WorkOrderStatus.CLOSED,),
            ).fetchone()
        return row_to_work_order(row) if row else None

    def add_voice_note(self, note: VoiceNote) -> bool:
        with self.connect() as connection:
            existing = connection.execute(
                "SELECT 1 FROM voice_notes WHERE client_uuid = ?",
                (note.client_uuid,),
            ).fetchone()
            if existing:
                return True
            connection.execute(
                """
                INSERT INTO voice_notes (
                    client_uuid, worker_id, transcript, status, processed_at,
                    raw_audio_ref, result_ref
                )
                VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    note.client_uuid,
                    note.worker_id,
                    note.transcript,
                    note.status,
                    note.processed_at.isoformat(),
                    note.raw_audio_ref,
                    note.result_ref,
                ),
            )
        return False

    def stats(self) -> DashboardStats:
        with self.connect() as connection:
            total = connection.execute("SELECT COUNT(*) FROM work_orders").fetchone()[0]
            open_count = connection.execute(
                "SELECT COUNT(*) FROM work_orders WHERE status = ?",
                (WorkOrderStatus.OPEN,),
            ).fetchone()[0]
            escalated = connection.execute(
                "SELECT COUNT(*) FROM work_orders WHERE status = ?",
                (WorkOrderStatus.ESCALATED,),
            ).fetchone()[0]
            critical_or_high = connection.execute(
                "SELECT COUNT(*) FROM work_orders WHERE severity IN (?, ?)",
                ("HIGH", "CRITICAL"),
            ).fetchone()[0]
            voice_notes = connection.execute("SELECT COUNT(*) FROM voice_notes").fetchone()[0]

        return DashboardStats(
            total_work_orders=total,
            open_work_orders=open_count,
            escalated_work_orders=escalated,
            critical_or_high=critical_or_high,
            voice_notes=voice_notes,
        )


def work_order_to_row(order: WorkOrder) -> tuple[Any, ...]:
    return (
        order.id,
        order.client_uuid,
        order.equipment_code,
        order.inspection_result,
        order.fault_code,
        order.location,
        order.severity,
        order.action_taken,
        json.dumps(order.parts_required),
        order.status,
        order.created_by,
        order.created_at.isoformat(),
        order.updated_at.isoformat(),
        order.raw_audio_ref,
        order.transcript,
    )


def row_to_work_order(row: sqlite3.Row) -> WorkOrder:
    payload = dict(row)
    payload["parts_required"] = json.loads(payload["parts_required"])
    return WorkOrder(**payload)
