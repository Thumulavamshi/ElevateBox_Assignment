"""Placing an outbound call, with the tracking and the safety guard attached.

Two things dial: the trigger endpoint, and the callback worker. They share this
so the guard cannot end up on one path and not the other - which is exactly the
kind of drift that would let a scheduled job reach a number the endpoint refuses.

**The destination is never a parameter.** It comes from ALLOWED_DESTINATION and
nowhere else, so neither a leaked URL nor a poisoned database row can point a
call somewhere new.
"""

import logging

from . import db, vapi
from .config import settings

log = logging.getLogger("elevatebox.dialler")


class DialError(RuntimeError):
    def __init__(self, status, detail):
        super().__init__(detail)
        self.status = status
        self.detail = detail


def place(is_callback_of=None, context="", first_message=None):
    """Dial the one allowed destination. Returns the call row's fields.

    `context` and `first_message` exist for callbacks. A callback that opens
    "Hi, this is Maya, I help small businesses..." to someone we spoke to
    yesterday is not a callback, it is a cold call with a timer on it. Both are
    passed as Vapi assistantOverrides so the deployed assistant is untouched.

    `variableValues` is ALWAYS sent, even empty, because an unset variable can
    leave the literal "{{callback_context}}" sitting in the system prompt.

    Raises DialError on a configuration problem or a provider rejection; the
    `calls` row is still written and marked failed either way, because a call we
    tried and could not place is something we want to be able to see afterwards.
    """
    if settings.missing():
        raise DialError(503, f"not configured: {', '.join(settings.missing())}")

    destination = settings.allowed_destination

    # The SAME guard the WhatsApp sender uses. This check was missing here while
    # the sender had it, which meant a run pointed at the evaluator without
    # ALLOW_EVALUATOR=1 dialled happily and then refused every message. Refusing
    # the call too makes that state loud instead of silent.
    ok, why = settings.permits(destination)
    if not ok:
        raise DialError(403, why)
    call_id = db.create_call(destination, assistant_id=settings.vapi_assistant_id,
                             is_callback_of=is_callback_of)
    db.add_event(call_id, "trigger.requested",
                 {"destination": destination, "is_callback_of": is_callback_of,
                  "context": context, "first_message": first_message})

    overrides = {"variableValues": {"callback_context": context or ""}}
    if first_message:
        overrides["firstMessage"] = first_message

    try:
        result = vapi.place_call(destination, overrides=overrides)
    except vapi.VapiError as exc:
        db.update_call(call_id, status="failed",
                       ended_reason=f"provider-error: {exc.detail[:200]}")
        db.add_event(call_id, "trigger.failed", {"status": exc.status, "detail": exc.detail})
        raise DialError(502, f"provider rejected the call: {exc.detail[:200]}") from exc

    if not db.attach_provider_id(call_id, result.get("id")):
        db.update_call(call_id, status="failed",
                       ended_reason="provider call id already linked to another call")
        raise DialError(409, "that provider call id is already tracked")

    db.update_call(call_id, status=result.get("status") or "queued")
    db.add_event(call_id, "trigger.accepted", result)
    return {"call_id": call_id, "provider_call_id": result.get("id"),
            "status": result.get("status"), "destination": destination}
