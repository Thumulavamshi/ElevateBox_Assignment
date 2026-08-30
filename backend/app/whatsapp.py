"""WhatsApp Cloud API sender.

Two send paths, and the distinction matters:

- **Template** - the design. Works cold, to someone who has never messaged us.
  Every scored requirement is satisfied by this path alone.
- **Free-form** - only legal inside a 24-hour customer-service window, which
  opens when the recipient messages US. Richer (any length, real line breaks,
  media with captions), but we never ask for it and never depend on it. A system
  that needs a human to warm up each lead before it can message them is not the
  autonomous system the assignment asks for.

`send_context_message` tries free-form when a window is known to be open and
falls back to template otherwise, so the better content is used when it is
genuinely available without the design resting on it.
"""

import json
import logging
import re
import time
import urllib.error
import urllib.request

from . import ultramsg
from .config import EVALUATOR_NUMBER, settings

log = logging.getLogger("elevatebox.whatsapp")

GRAPH = "https://graph.facebook.com"

# Meta throttles messages to the same recipient. We send a mid-call message and
# a post-call message to one number, so they have to be spaced.
MIN_GAP_SECONDS = 6.0
_last_send_at = {}


class WhatsAppError(RuntimeError):
    def __init__(self, status, detail):
        super().__init__(f"WhatsApp API {status}: {detail}")
        self.status = status
        self.detail = detail


def provider():
    return settings.wa_provider


def supports_freeform():
    """Whether we can send prose and media without a pre-approved template.

    This is not a detail - it decides how the handlers COMPOSE. With templates,
    the context is a flat parameter list with no line breaks. Without them, the
    follow-up can be written the way a person writes one, and the architecture
    image can carry it as a caption in a single message.
    """
    return provider() == "ultramsg"


def configured():
    """Whether we can send at all. Reported on /health so gaps stay visible."""
    if provider() == "ultramsg":
        ok, detail = ultramsg.configured()
        return ok, f"ultramsg: {detail}"
    missing = [k for k, v in {
        "WHATSAPP_PHONE_NUMBER_ID": settings.wa_phone_number_id,
        "WHATSAPP_ACCESS_TOKEN": settings.wa_access_token,
    }.items() if not v]
    if missing:
        return False, "meta: missing " + ", ".join(missing)
    return True, "meta: ready"


def normalize(number):
    """Meta wants digits with country code and no punctuation."""
    return re.sub(r"\D", "", number or "")


def _check_destination(number):
    """Same guard as the dialler: we only ever message the configured number.

    Without this, a bug in message composition could send a half-built recap to
    the evaluator during development. The number is not a parameter callers can
    choose freely.
    """
    allowed = normalize(settings.allowed_destination)
    target = normalize(number)
    if not target:
        raise WhatsAppError(0, "no destination number")
    if allowed and target[-10:] != allowed[-10:]:
        raise WhatsAppError(0, f"destination {target[-10:]} is not the allowed "
                               f"destination {allowed[-10:]}")
    if target[-10:] == normalize(EVALUATOR_NUMBER)[-10:] and not settings.allow_evaluator:
        raise WhatsAppError(0, "refusing to message the evaluator: set "
                               "ALLOW_EVALUATOR=1 deliberately for the real run")


def _throttle(number):
    key = normalize(number)
    wait = MIN_GAP_SECONDS - (time.time() - _last_send_at.get(key, 0.0))
    if wait > 0:
        log.info("spacing sends to %s by %.1fs", key[-4:], wait)
        time.sleep(wait)
    _last_send_at[key] = time.time()


def _post(payload):
    url = f"{GRAPH}/{settings.wa_api_version}/{settings.wa_phone_number_id}/messages"
    req = urllib.request.Request(
        url,
        method="POST",
        data=json.dumps(payload).encode(),
        headers={
            "Authorization": f"Bearer {settings.wa_access_token}",
            "Content-Type": "application/json",
        },
    )
    try:
        with urllib.request.urlopen(req, timeout=25) as resp:
            return json.loads(resp.read().decode() or "{}")
    except urllib.error.HTTPError as exc:
        detail = exc.read().decode()[:800]
        raise WhatsAppError(exc.code, detail) from exc
    except urllib.error.URLError as exc:
        raise WhatsAppError(0, str(exc.reason)) from exc


def _guard(to):
    """Every send goes through here, whichever provider is behind it.

    Changing provider must never quietly drop the destination and evaluator
    guards - those are the reason a half-built recap cannot reach 8688664337
    during development.
    """
    ok, why = configured()
    if not ok:
        raise WhatsAppError(0, why)
    _check_destination(to)
    _throttle(to)


def _meta_send(payload, to):
    result = _post(payload)
    message_id = ((result.get("messages") or [{}])[0]).get("id")
    log.info("whatsapp sent, id=%s", message_id)
    return {"message_id": message_id, "raw": result}


# ----------------------------------------------------------------- template

def send_template(to, name, body_params=(), header=None, lang="en"):
    """Send an approved template. The path that works cold.

    header, when given:
        {"type": "image",    "link": "https://..."}
        {"type": "document", "link": "https://...", "filename": "resume.pdf"}
    """
    components = []
    if header:
        kind = header["type"]
        media = {"link": header["link"]}
        if kind == "document" and header.get("filename"):
            media["filename"] = header["filename"]
        components.append({"type": "header",
                           "parameters": [{"type": kind, kind: media}]})
    if body_params:
        components.append({
            "type": "body",
            "parameters": [{"type": "text", "text": _clean_param(p)} for p in body_params],
        })

    payload = {
        "messaging_product": "whatsapp",
        "to": normalize(to),
        "type": "template",
        "template": {"name": name, "language": {"code": lang}},
    }
    if components:
        payload["template"]["components"] = components
    _guard(to)
    if supports_freeform():
        raise WhatsAppError(0, f"provider {provider()} has no templates - "
                               f"the handlers should compose free-form instead")
    return _meta_send(payload, to)


def _clean_param(value):
    """Template parameters may not contain newlines, tabs, or 4+ spaces.

    Meta rejects the send outright if they do, so a stray line break in an
    extracted quote would fail the mid-call message. Normalising here means the
    composer never has to remember.
    """
    return re.sub(r"\s{4,}", " ", re.sub(r"[\r\n\t]+", " ", str(value))).strip()


# ----------------------------------------------------------------- free-form

def send_text(to, body):
    """Free-form text.

    On UltraMsg this always works. On Meta it is only legal inside an open
    24-hour window, which we never rely on - see the module docstring.
    """
    _guard(to)
    if supports_freeform():
        return ultramsg.send_text(normalize(to), body)
    return _meta_send({
        "messaging_product": "whatsapp",
        "to": normalize(to),
        "type": "text",
        "text": {"body": body, "preview_url": True},
    }, to)


def send_media(to, kind, link, caption=None, filename=None):
    """Free-form image/document. `link` may be a URL or, on UltraMsg, a local path."""
    _guard(to)
    if supports_freeform():
        return ultramsg.send_media(normalize(to), kind, link, caption, filename)
    media = {"link": link}
    if caption:
        media["caption"] = caption
    if kind == "document" and filename:
        media["filename"] = filename
    return _meta_send({
        "messaging_product": "whatsapp",
        "to": normalize(to),
        "type": kind,
        kind: media,
    }, to)
