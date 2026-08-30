"""Action handlers. Importing this module registers them on the action bus.

Kept separate from `actions.py` so the bus stays generic - it knows about
claiming, idempotency and background execution, not about WhatsApp.
"""

import asyncio
import logging

from . import db, whatsapp
from .actions import handler
from .config import settings

log = logging.getLogger("elevatebox.handlers")

# Order matters: the recap reads best when it follows the shape of the call.
SLOT_ORDER = ("products", "catalogue_size", "timeline", "features", "budget")

FALLBACKS = {
    "products": "your business",
    "catalogue_size": "the catalogue you described",
    "timeline": "soon",
    "features": "the features we discussed",
    "budget": "the budget you mentioned",
}


def _slot(slots, name):
    """Best value for a slot, falling back to something that still reads naturally.

    A template parameter cannot be empty - Meta rejects the send - so every slot
    needs a usable value even when extraction found nothing. The fallbacks are
    deliberately vague rather than invented: saying "the budget you mentioned"
    is honest, saying "one lakh" when they never said it is not.
    """
    row = slots.get(name) or {}
    return (row.get("value") or "").strip() or FALLBACKS[name]


def _quote(slots, name):
    """The lead's own words, for the slot that has to be verbatim."""
    row = slots.get(name) or {}
    return (row.get("raw_quote") or row.get("value") or "").strip() or FALLBACKS[name]


# --- free-form composition (UltraMsg) --------------------------------------
#
# A template forces every parameter to be filled, which is why FALLBACKS exists.
# Free-form has no such rule, so a slot we never learned is simply LEFT OUT
# rather than papered over with "your business" - which reads better and claims
# less. The assignment's test is "specifics from the conversation, not a summary
# that could apply to anyone", and an omitted line beats a vague one.

# No leading hedge words here. The extractor already returns "around 200
# products", so a shape like "Around {}" produced "Around around 200 products".
RECAP_LABELS = (
    ("products", "You sell {}"),
    ("catalogue_size", "{} in the catalogue"),
    ("timeline", "You want it live {}"),
    ("features", "Must-haves: {}"),
)


def _bullets(slots):
    out = []
    for name, shape in RECAP_LABELS:
        value = ((slots.get(name) or {}).get("value") or "").strip()
        if value:
            out.append("• " + shape.format(value))
    return out


def _signature():
    lines = []
    if settings.your_name:
        lines.append(settings.your_name)
    if settings.your_mobile:
        # Its own line, because Section 06 asks for the number "clearly visible,
        # so I can call you back without hunting for it".
        lines.append(settings.your_mobile)
    return "\n".join(lines)


def _verbatim(slots):
    """One thing they actually said, quoted back. 'The follow up quotes
    something specific I said' is on the impress-us list."""
    for name in ("budget", "features", "timeline", "products"):
        row = slots.get(name) or {}
        quote = (row.get("raw_quote") or "").strip()
        if quote and len(quote.split()) >= 3:
            return quote
    return ""


@handler("whatsapp_hot")
async def send_mid_call(call_id, payload):
    """The 15-point row. Fires during the call, on high intent.

    Text-only on purpose: Meta fetches header media before delivering, and this
    message is scored on arriving while the call is still live. No header is the
    fastest thing we can send.
    """
    call = db.get_call(call_id) or {}
    slots = db.get_slots(call_id)
    to = call.get("destination") or settings.allowed_destination

    if whatsapp.supports_freeform():
        bullets = _bullets(slots)
        body = ["Hi - this is Maya, from the call we're on right now.",
                "",
                "Sending this across as promised. We build custom online stores "
                "for small businesses: payment gateway, cash on delivery, order "
                "tracking, and a catalogue that handles size and colour variants "
                "properly."]
        if bullets:
            body += ["", "From what you've told me so far:"] + bullets
        body += ["", "I'll follow up with the full details right after we hang up."]
        signature = _signature()
        if signature:
            body += ["", signature]
        result = await asyncio.to_thread(whatsapp.send_text, to, "\n".join(body))
        log.info("mid-call whatsapp sent for %s (free-form)", call_id)
        return result

    params = []
    if settings.wa_midcall_params:
        params = [_slot(slots, "products"),
                  _slot(slots, "budget"),
                  _slot(slots, "timeline")]
    else:
        # Parameterless template (hello_world) while ours is in review. The flow,
        # the trigger, the idempotency and the timing are all still exercised -
        # only the words differ.
        log.info("mid-call template %s takes no parameters", settings.wa_tpl_midcall)

    result = await asyncio.to_thread(whatsapp.send_template, 
        to,
        settings.wa_tpl_midcall,
        body_params=params,
        lang=settings.wa_midcall_lang,
    )
    log.info("mid-call whatsapp sent for %s", call_id)
    return result


def _followup_text(slots):
    """The post-call message. Carries Section 06 items 1, 2 and 3; the image it
    rides on is item 4."""
    body = ["Hi - Maya here, following up on our call just now.", ""]
    bullets = _bullets(slots)
    if bullets:
        body += ["Here's what I took away:"] + bullets + [""]

    quote = _verbatim(slots)
    if quote:
        body += [f'On budget you said: "{quote}"', ""]

    body += ["The image attached is how the system that just called you is "
             "built - the call itself, the live transcript, how it read your "
             "intent, and the WhatsApp you're reading now.",
             "",
             "My resume is in the next message. Happy to talk whenever suits you."]
    signature = _signature()
    if signature:
        body += ["", signature]
    return "\n".join(body)


@handler("whatsapp_followup")
async def send_followup(call_id, payload):
    """Post-call message carrying all four Section 06 elements.

    Image header = "an image of how you built it". Body = the context, framed as
    a person would write it, with the mobile number baked into the template's
    static text so it cannot be broken by a bad parameter.
    """
    call = db.get_call(call_id) or {}
    slots = db.get_slots(call_id)
    to = call.get("destination") or settings.allowed_destination

    if whatsapp.supports_freeform():
        body = _followup_text(slots)
        if settings.wa_architecture_url:
            # Image + caption in ONE message, which satisfies all four Section 06
            # items together - the literal reading of "the message that reaches
            # me must contain all four of these" (OQ-02). The template path had
            # to split them.
            result = await asyncio.to_thread(whatsapp.send_media, to, "image", settings.wa_architecture_url,
                                         caption=body)
        else:
            log.warning("no WHATSAPP_ARCHITECTURE_IMAGE_URL - sending text only, "
                        "which drops a required Section 06 element")
            result = await asyncio.to_thread(whatsapp.send_text, to, body)
        log.info("follow-up whatsapp sent for %s (free-form)", call_id)
        return result

    header = None
    if settings.wa_architecture_url:
        header = {"type": "image", "link": settings.wa_architecture_url}
    else:
        log.warning("no WHATSAPP_ARCHITECTURE_IMAGE_URL - sending without the image, "
                    "which drops a required Section 06 element")

    result = await asyncio.to_thread(whatsapp.send_template, 
        to,
        settings.wa_tpl_followup,
        body_params=[
            _slot(slots, "products"),
            _slot(slots, "catalogue_size"),
            _slot(slots, "timeline"),
            _slot(slots, "features"),
            _quote(slots, "budget"),
        ],
        header=header,
        lang=settings.wa_template_lang,
    )
    log.info("follow-up whatsapp sent for %s", call_id)
    return result


@handler("callback_confirm")
async def send_callback_confirm(call_id, payload):
    """Written proof, in their hand, that the callback was actually booked.

    Fires on the BOOKING, not on call end - so it is intent-triggered in the
    same sense the mid-call message is, and it is a different message with a
    different purpose (audit Finding H's condition for keeping it).

    Without this the callback is invisible: the agent says a time, and the lead
    has nothing but memory until the phone rings a day later.
    """
    call = db.get_call(call_id) or {}
    to = call.get("destination") or settings.allowed_destination

    pending = [c for c in db.get_callbacks(call_id) if c["status"] == "pending"]
    if not pending:
        raise RuntimeError("no pending callback to confirm")
    when = db.to_ist(pending[-1]["resolved_at_utc"])

    body = [f"Confirming our call: {when:%A %d %B} at {when:%I:%M %p}".replace(" 0", " "),
            ""]
    slots = db.get_slots(call_id)
    bullets = _bullets(slots)
    if bullets:
        body += ["We'll pick up from where we left off:"] + bullets + [""]
    body += ["If that time no longer suits, just reply here and I'll move it."]
    signature = _signature()
    if signature:
        body += ["", signature]

    result = await asyncio.to_thread(whatsapp.send_text, to, "\n".join(body))
    log.info("callback confirmation sent for %s (%s)", call_id, when)
    return result


@handler("whatsapp_resume")
async def send_resume(call_id, payload):
    """Résumé as a document header. Separate message because WhatsApp allows
    only one media header per message and the follow-up already carries the
    architecture image."""
    call = db.get_call(call_id) or {}
    to = call.get("destination") or settings.allowed_destination

    if not settings.wa_resume_url:
        raise RuntimeError("WHATSAPP_RESUME_URL not set - cannot attach the resume")

    if whatsapp.supports_freeform():
        # Built by appending rather than filtering a flat list: `filter(None, ...)`
        # strips the "" separators along with the absent links, which collapsed
        # the whole message into one unreadable block.
        lines = ["My resume, as promised."]
        links = [
            ("Live prototype (press the button and it calls you back)", "demo_url"),
            ("Code", "repo_url"),
            ("What works, what doesn't", "note_url"),
        ]
        shown = [f"{label}:\n{payload[key]}" for label, key in links if payload.get(key)]
        if shown:
            lines += [""] + shown
        signature = _signature()
        if signature:
            lines += ["", signature]
        caption = "\n".join(lines)
        return await asyncio.to_thread(whatsapp.send_media, to, "document", settings.wa_resume_url,
                                   caption=caption,
                                   filename=settings.wa_resume_filename)

    return await asyncio.to_thread(whatsapp.send_template, 
        to,
        settings.wa_tpl_resume,
        body_params=[
            payload.get("demo_url") or "(link to follow)",
            payload.get("repo_url") or "(link to follow)",
            payload.get("note_url") or "(link to follow)",
        ],
        header={"type": "document", "link": settings.wa_resume_url,
                "filename": settings.wa_resume_filename},
        lang=settings.wa_template_lang,
    )
