"""SQLite persistence.

Stdlib sqlite3, no ORM. The schema is small enough that an ORM plus migration
machinery would be more moving parts than it saves, and the SQL stays readable
for the "defend your choices" conversation.

Portability: everything here is plain SQL. Moving to Postgres means swapping
the connection helper and the `?` placeholders; no model rewrite.
"""

import json
import os
import sqlite3
import uuid
from contextlib import contextmanager
from datetime import datetime, timezone, timedelta

from .config import settings

IST = timezone(timedelta(hours=5, minutes=30))
SCHEMA_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "schema.sql")


def utc_now():
    """Every stored timestamp goes through here. UTC, ISO-8601, seconds."""
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def to_ist(iso_utc):
    """UTC string -> Asia/Kolkata datetime. Used for anything spoken or displayed."""
    if not iso_utc:
        return None
    return datetime.fromisoformat(iso_utc).astimezone(IST)


def new_id():
    return str(uuid.uuid4())


@contextmanager
def conn():
    """One connection per operation. WAL so reads never block the webhook path."""
    os.makedirs(os.path.dirname(settings.db_path), exist_ok=True)
    cx = sqlite3.connect(settings.db_path, timeout=10)
    cx.row_factory = sqlite3.Row
    cx.execute("PRAGMA journal_mode=WAL")
    cx.execute("PRAGMA foreign_keys=ON")
    try:
        yield cx
        cx.commit()
    except Exception:
        cx.rollback()
        raise
    finally:
        cx.close()


def init_db():
    with open(SCHEMA_PATH, encoding="utf-8") as fh:
        sql = fh.read()
    with conn() as cx:
        cx.executescript(sql)


# ----------------------------------------------------------------- calls

def create_call(destination, assistant_id=None, is_callback_of=None):
    call_id, now = new_id(), utc_now()
    with conn() as cx:
        cx.execute(
            "INSERT INTO calls (id, status, direction, destination, assistant_id,"
            " is_callback_of, created_at, updated_at)"
            " VALUES (?,?,?,?,?,?,?,?)",
            (call_id, "initiating", "outbound", destination, assistant_id,
             is_callback_of, now, now),
        )
    return call_id


def attach_provider_id(call_id, provider_call_id):
    """Link our call row to Vapi's id.

    provider_call_id is UNIQUE so two of our rows can never claim one Vapi call.
    Returns False if that id is already taken rather than raising - the caller
    turns it into a clean error instead of a 500 with a stack trace.
    """
    try:
        with conn() as cx:
            cx.execute("UPDATE calls SET provider_call_id=?, updated_at=? WHERE id=?",
                       (provider_call_id, utc_now(), call_id))
        return True
    except sqlite3.IntegrityError:
        return False


def update_call(call_id, **fields):
    """Update whitelisted columns only - field names come from webhook payloads."""
    allowed = {"status", "started_at", "answered_at", "ended_at", "ended_reason",
               "recording_url", "summary", "provider_call_id"}
    fields = {k: v for k, v in fields.items() if k in allowed and v is not None}
    if not fields:
        return
    sets = ", ".join(f"{k}=?" for k in fields)
    with conn() as cx:
        cx.execute(f"UPDATE calls SET {sets}, updated_at=? WHERE id=?",
                   (*fields.values(), utc_now(), call_id))


def get_call(call_id):
    with conn() as cx:
        row = cx.execute("SELECT * FROM calls WHERE id=?", (call_id,)).fetchone()
    return dict(row) if row else None


def call_id_for_provider(provider_call_id):
    """Map a Vapi call id back to ours. Webhooks only know theirs."""
    if not provider_call_id:
        return None
    with conn() as cx:
        row = cx.execute("SELECT id FROM calls WHERE provider_call_id=?",
                         (provider_call_id,)).fetchone()
    return row["id"] if row else None


def stale_calls(live_statuses, updated_before):
    """Unfinished calls that have gone quiet. Feeds the reconciliation sweeper.

    Staleness is measured from the last EVENT, not from calls.updated_at.
    updated_at only moves when the call's status changes, so a five-minute
    conversation would look abandoned three minutes in and get reconciled while
    the person was still talking. Transcripts land as events, so the newest
    event is the true sign of life.
    """
    marks = ",".join("?" for _ in live_statuses)
    with conn() as cx:
        rows = cx.execute(
            f"SELECT c.* FROM calls c WHERE c.status IN ({marks})"
            " AND COALESCE((SELECT MAX(created_at) FROM events e WHERE e.call_id = c.id),"
            "              c.updated_at) < ?"
            " ORDER BY c.updated_at LIMIT 20",
            (*live_statuses, updated_before)).fetchall()
    return [dict(r) for r in rows]


def list_calls(limit=20):
    with conn() as cx:
        rows = cx.execute("SELECT * FROM calls ORDER BY created_at DESC LIMIT ?",
                          (limit,)).fetchall()
    return [dict(r) for r in rows]


# ----------------------------------------------------------------- turns

def add_turn(call_id, role, text, seconds_from_start=None, language=None):
    """Append a final transcript turn. Returns its seq, or None if duplicated.

    Vapi can resend a final transcript; the UNIQUE(call_id, seq) constraint plus
    a same-role/same-text check keeps the understanding lane from seeing doubles.
    """
    with conn() as cx:
        last = cx.execute(
            "SELECT seq, role, text FROM turns WHERE call_id=? ORDER BY seq DESC LIMIT 1",
            (call_id,)).fetchone()
        if last and last["role"] == role and last["text"] == text:
            return None
        seq = (last["seq"] + 1) if last else 0
        cx.execute(
            "INSERT INTO turns (call_id, seq, role, text, language, seconds_from_start,"
            " created_at) VALUES (?,?,?,?,?,?,?)",
            (call_id, seq, role, text, language, seconds_from_start, utc_now()),
        )
    return seq


def get_turns(call_id):
    with conn() as cx:
        rows = cx.execute("SELECT * FROM turns WHERE call_id=? ORDER BY seq", (call_id,)).fetchall()
    return [dict(r) for r in rows]


def transcript_text(call_id):
    """Flat transcript, the form the classifier and composer both consume."""
    return "\n".join(f"{t['role']}: {t['text']}" for t in get_turns(call_id))


# ----------------------------------------------------------------- events

def add_event(call_id, type_, payload):
    with conn() as cx:
        cx.execute("INSERT INTO events (call_id, type, payload, created_at) VALUES (?,?,?,?)",
                   (call_id, type_, json.dumps(payload)[:200000], utc_now()))


def get_events(call_id, limit=200):
    with conn() as cx:
        rows = cx.execute("SELECT id, type, created_at FROM events WHERE call_id=?"
                          " ORDER BY id LIMIT ?", (call_id, limit)).fetchall()
    return [dict(r) for r in rows]


# ----------------------------------------------------------------- slots

def upsert_slot(call_id, name, value, raw_quote=None, source_turn_seq=None, confidence=None):
    with conn() as cx:
        cx.execute(
            "INSERT INTO slots (call_id, name, value, raw_quote, source_turn_seq,"
            " confidence, updated_at) VALUES (?,?,?,?,?,?,?)"
            " ON CONFLICT(call_id, name) DO UPDATE SET"
            " value=excluded.value, raw_quote=excluded.raw_quote,"
            " source_turn_seq=excluded.source_turn_seq,"
            " confidence=excluded.confidence, updated_at=excluded.updated_at",
            (call_id, name, value, raw_quote, source_turn_seq, confidence, utc_now()),
        )


def get_slots(call_id):
    with conn() as cx:
        rows = cx.execute("SELECT * FROM slots WHERE call_id=?", (call_id,)).fetchall()
    return {r["name"]: dict(r) for r in rows}


# ----------------------------------------------------------------- classifications

def add_classification(call_id, label, confidence=None, barrier=None,
                       evidence_quote=None, at_turn_seq=None):
    with conn() as cx:
        cx.execute(
            "INSERT INTO classifications (call_id, label, confidence, barrier,"
            " evidence_quote, at_turn_seq, created_at) VALUES (?,?,?,?,?,?,?)",
            (call_id, label, confidence, barrier, evidence_quote, at_turn_seq, utc_now()),
        )


def latest_classification(call_id):
    with conn() as cx:
        row = cx.execute("SELECT * FROM classifications WHERE call_id=?"
                         " ORDER BY id DESC LIMIT 1", (call_id,)).fetchone()
    return dict(row) if row else None


def classification_history(call_id):
    with conn() as cx:
        rows = cx.execute("SELECT * FROM classifications WHERE call_id=? ORDER BY id",
                          (call_id,)).fetchall()
    return [dict(r) for r in rows]


# ----------------------------------------------------------------- actions

def claim_action(call_id, type_, idempotency_key, trigger_source=None, payload=None):
    """Reserve an action. Returns its row id, or None if already claimed.

    The UNIQUE index on idempotency_key does the work: whichever trigger path
    gets there first wins and the other becomes a no-op. This is what stops the
    LLM tool call and the async watchdog from sending two WhatsApps.
    """
    with conn() as cx:
        try:
            cur = cx.execute(
                "INSERT INTO actions (call_id, type, idempotency_key, status,"
                " trigger_source, payload, requested_at) VALUES (?,?,?,?,?,?,?)",
                (call_id, type_, idempotency_key, "pending", trigger_source,
                 json.dumps(payload or {}), utc_now()),
            )
            return cur.lastrowid
        except sqlite3.IntegrityError:
            return None


def update_action(action_id, **fields):
    allowed = {"status", "provider_message_id", "error", "sent_at", "delivered_at", "attempts"}
    fields = {k: v for k, v in fields.items() if k in allowed}
    if not fields:
        return
    sets = ", ".join(f"{k}=?" for k in fields)
    with conn() as cx:
        cx.execute(f"UPDATE actions SET {sets} WHERE id=?", (*fields.values(), action_id))


def get_actions(call_id):
    with conn() as cx:
        rows = cx.execute("SELECT * FROM actions WHERE call_id=? ORDER BY id", (call_id,)).fetchall()
    return [dict(r) for r in rows]


# ----------------------------------------------------------------- callbacks

def add_callback(call_id, resolved_at_utc, spoken_phrase=None, resolution_rule=None):
    now = utc_now()
    with conn() as cx:
        cur = cx.execute(
            "INSERT INTO callbacks (call_id, spoken_phrase, resolved_at_utc,"
            " resolution_rule, status, created_at, updated_at) VALUES (?,?,?,?,?,?,?)",
            (call_id, spoken_phrase, resolved_at_utc, resolution_rule, "pending", now, now),
        )
        return cur.lastrowid


def claim_due_callback(now_utc=None):
    """Atomically take one due callback. Returns the row, or None.

    pending -> claimed in a single guarded UPDATE. Two workers racing cannot both
    win, so a callback cannot be placed twice (audit R3 - double-dialling the
    evaluator would be worse than not calling at all).
    """
    now_utc = now_utc or utc_now()
    with conn() as cx:
        row = cx.execute(
            "SELECT * FROM callbacks WHERE status='pending' AND resolved_at_utc<=?"
            " ORDER BY resolved_at_utc LIMIT 1", (now_utc,)).fetchone()
        if not row:
            return None
        changed = cx.execute(
            "UPDATE callbacks SET status='claimed', updated_at=?"
            " WHERE id=? AND status='pending'", (utc_now(), row["id"])).rowcount
        return dict(row) if changed else None


def update_callback(callback_id, **fields):
    allowed = {"status", "placed_call_id", "confirmed_aloud"}
    fields = {k: v for k, v in fields.items() if k in allowed}
    if not fields:
        return
    sets = ", ".join(f"{k}=?" for k in fields)
    with conn() as cx:
        cx.execute(f"UPDATE callbacks SET {sets}, updated_at=? WHERE id=?",
                   (*fields.values(), utc_now(), callback_id))


def get_callbacks(call_id):
    with conn() as cx:
        rows = cx.execute("SELECT * FROM callbacks WHERE call_id=? ORDER BY id",
                          (call_id,)).fetchall()
    return [dict(r) for r in rows]
