"""Finalising a call, and catching the ones whose webhook never arrived.

`system-design.md` §7 and C18 specified this and it was never built. The 29 Aug
call is exactly why it is needed: the `end-of-call-report` webhook never reached
us, so the call sat at status `in-progress` for good, the final extraction pass
never ran, and **the post-call follow-up never fired** - silently. Nothing was
broken enough to raise an error; the work just did not happen.

A tunnel that dies, a redeploy, a dropped packet, or a laptop closed thirty
seconds early all produce the same hole. The fix is not to trust the webhook: it
is to notice a call that stopped talking and go ask the provider how it ended.

`finalize()` is shared by both paths, so a reconciled call and a webhooked call
end up in exactly the same state.
"""

import asyncio
import logging
import os
from datetime import datetime, timedelta, timezone

from . import db, understanding, vapi

log = logging.getLogger("elevatebox.reconcile")

POLL_SECONDS = int(os.environ.get("RECONCILE_POLL_SECONDS", "60"))

# How quiet a call must go before we suspect its webhook was lost. Long enough
# not to race a call that is simply between turns.
STALE_AFTER = timedelta(minutes=int(os.environ.get("RECONCILE_STALE_MINUTES", "3")))

LIVE_STATUSES = ("initiating", "queued", "ringing", "in-progress")


async def finalize(call_id, ended_reason=None, started_at=None, recording_url=None,
                   summary=None, messages=(), source="webhook"):
    """Mark a call ended, backfill its transcript, run the post-call lane.

    Idempotent by construction: `add_turn` de-duplicates, and the post-call
    action goes through the bus's idempotency key. Running it twice - once from
    a late webhook and once from the sweeper - produces one follow-up.
    """
    db.update_call(
        call_id,
        status="ended",
        ended_at=db.utc_now(),
        ended_reason=ended_reason,
        recording_url=recording_url,
        summary=summary,
        started_at=started_at,
    )
    backfill_turns(call_id, messages or ())
    db.add_event(call_id, "call.finalized", {"source": source,
                                             "ended_reason": ended_reason})
    await understanding.on_call_ended(call_id)


def backfill_turns(call_id, messages):
    """Reconcile the transcript against the final report.

    If live transcript webhooks were missed - a blip, a restart - the report
    still carries the whole conversation. add_turn() de-duplicates, so replaying
    it is safe and fills any holes.
    """
    for m in messages:
        role = m.get("role")
        if role not in ("user", "bot", "assistant"):
            continue
        text = (m.get("message") or "").strip()
        if not text:
            continue
        db.add_turn(call_id, "user" if role == "user" else "assistant", text,
                    seconds_from_start=m.get("secondsFromStart"))


async def sweep(now=None):
    """One pass: find quiet unfinished calls and ask Vapi how they ended.

    Returns the ids finalized. Never raises.
    """
    now = now or datetime.now(timezone.utc)
    cutoff = (now - STALE_AFTER).isoformat(timespec="seconds")
    finalized = []

    for call in await asyncio.to_thread(db.stale_calls, LIVE_STATUSES, cutoff):
        provider_id = call.get("provider_call_id")
        if not provider_id:
            # Never reached the provider at all - nothing to ask about.
            db.update_call(call["id"], status="failed",
                           ended_reason="abandoned: no provider call id")
            continue
        try:
            remote = await asyncio.to_thread(vapi.get_call, provider_id)
        except Exception as exc:
            log.warning("could not reconcile call %s: %s", call["id"], exc)
            continue

        status = remote.get("status")
        if status in LIVE_STATUSES:
            continue          # genuinely still running; leave it alone

        artifact = remote.get("artifact") or {}
        log.info("reconciling call %s - provider says %s, our webhook never arrived",
                 call["id"], status)
        await finalize(
            call["id"],
            ended_reason=remote.get("endedReason") or f"reconciled: {status}",
            started_at=remote.get("startedAt"),
            recording_url=artifact.get("recordingUrl") or remote.get("recordingUrl"),
            summary=remote.get("summary"),
            messages=artifact.get("messages") or remote.get("messages") or [],
            source="reconcile",
        )
        finalized.append(call["id"])

    return finalized


async def worker():
    """The loop. Started in the app lifespan, cancelled on shutdown."""
    log.info("reconcile worker started, polling every %ss (stale after %s)",
             POLL_SECONDS, STALE_AFTER)
    while True:
        try:
            await asyncio.sleep(POLL_SECONDS)
            await sweep()
        except asyncio.CancelledError:
            log.info("reconcile worker stopped")
            raise
        except Exception:
            log.exception("reconcile pass failed")
