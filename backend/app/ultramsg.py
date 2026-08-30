"""UltraMsg transport - an unofficial WhatsApp gateway.

**Why this exists, stated plainly.** `system-design.md` §4.10 chose the official
Meta Cloud API and named this exact contingency: unofficial gateways are not the
default, but *"if approval stalls and this becomes the only path to a working
demo, it gets used and disclosed in the note, never silently."* Meta and Twilio
both dead-ended on KYC and business verification, which are external clocks we
do not control, so this is that path. **The disclosure obligation is real and
must go in the under-200-word note** - see docs/whatsapp-setup-guide.md.

The assignment itself lists WAPI, a gateway of the same kind, among the tools it
considers acceptable, so this is not off-menu.

What changes for the better: no templates, no approval queue, no 24-hour window,
and **real line breaks**. `system-design.md` §9 listed template constraints as a
known limitation shaping the copy - that limitation is gone, and the follow-up
can now carry the architecture image and its full context in ONE message, which
is the literal reading of Section 06's "the message that reaches me must contain
all four of these" (OQ-02).

What is worse, and worth saying out loud: this drives a real linked WhatsApp
account rather than a business API, so it can be disconnected, rate-limited or
banned by WhatsApp, and it has no delivery receipts of the kind the mid-call
timing evidence was designed around.

Two deliberate departures from UltraMsg's own sample code:

- **TLS is verified.** Their sample passes `ssl._create_unverified_context()`,
  which turns off certificate checking and hands the token to anyone able to
  intercept the connection. There is no reason to accept that.
- **stdlib urllib, not requests.** The rest of this backend has no HTTP
  dependency and does not need one for a form POST.
"""

import base64
import json
import logging
import mimetypes
import os
import urllib.error
import urllib.parse
import urllib.request

from .config import ROOT, settings

log = logging.getLogger("elevatebox.ultramsg")

BASE = "https://api.ultramsg.com"

# UltraMsg's own cap on a chat body.
MAX_BODY = 4096


class UltraMsgError(RuntimeError):
    def __init__(self, status, detail):
        super().__init__(f"UltraMsg {status}: {detail}")
        self.status = status
        self.detail = detail


def configured():
    """Whether we can send at all. Reported on /health so gaps stay visible."""
    missing = [k for k, v in {
        "ULTRAMSG_INSTANCE_ID": settings.um_instance,
        "ULTRAMSG_TOKEN": settings.um_token,
    }.items() if not v]
    if missing:
        return False, "missing: " + ", ".join(missing)
    return True, f"ready ({settings.um_instance})"


# A text message is a few hundred bytes; a base64 image is megabytes going UP a
# home broadband link. The follow-up failed with "write operation timed out"
# partway through a 1.8 MB upload on the old flat 30 s budget.
TEXT_TIMEOUT = 30
MEDIA_TIMEOUT = int(os.environ.get("ULTRAMSG_MEDIA_TIMEOUT", "180"))

# Base64 inflates by ~4/3, and WhatsApp recompresses images anyway, so a large
# original buys nothing but upload time and timeouts.
WARN_MEDIA_BYTES = 1_000_000


def _request(method, path, fields, timeout=TEXT_TIMEOUT):
    url = f"{BASE}/{settings.um_instance}/{path}"
    data = urllib.parse.urlencode(fields).encode("utf-8")
    if method == "GET":
        url = f"{url}?{data.decode()}"
        data = None

    # The User-Agent is required, not cosmetic. UltraMsg sits behind Cloudflare,
    # which rejects urllib's default "Python-urllib/3.x" with a 403 "error code:
    # 1010" browser-integrity block - an error that looks like a bad token.
    req = urllib.request.Request(
        url, method=method, data=data,
        headers={"Content-Type": "application/x-www-form-urlencoded",
                 "User-Agent": "ElevateBox-backend/1.0"},
    )
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            body = resp.read().decode("utf-8") or "{}"
    except urllib.error.HTTPError as exc:
        raise UltraMsgError(exc.code, exc.read().decode()[:600]) from exc
    except urllib.error.URLError as exc:
        raise UltraMsgError(0, str(exc.reason)) from exc

    try:
        result = json.loads(body)
    except ValueError:
        raise UltraMsgError(0, f"non-JSON response: {body[:200]}") from None

    # A 200 does NOT mean it sent. UltraMsg reports failures in the body, so
    # trusting the status code alone would log a send that never happened -
    # indistinguishable from "the WhatsApp never arrived".
    if isinstance(result, dict) and result.get("error"):
        raise UltraMsgError(200, str(result["error"])[:400])
    if isinstance(result, dict) and str(result.get("sent", "true")).lower() == "false":
        raise UltraMsgError(200, str(result.get("message") or result)[:400])
    return result


def _auth(extra):
    return {"token": settings.um_token, **extra}


def status():
    """Instance connection state. Free, sends nothing - the pre-flight check."""
    return _request("GET", "instance/status", _auth({}))


def _result(raw):
    return {"message_id": str(raw.get("id") or ""), "raw": raw}


def send_text(to, body):
    """Free-form text. No template, no approval, no 24-hour window."""
    if len(body) > MAX_BODY:
        log.warning("body of %d chars truncated to %d", len(body), MAX_BODY)
        body = body[:MAX_BODY]
    return _result(_request("POST", "messages/chat", _auth({"to": to, "body": body})))


def media_value(source):
    """A public URL passed through, or a local file inlined as base64.

    Inlining is what makes the architecture image and the resume sendable with
    **no media hosting at all**, which was blocker #4 in HANDOFF. The official
    API could never do this - Meta fetches header media by URL - so it is one
    place where the unofficial route is genuinely simpler.
    """
    if not source:
        return None
    if source.startswith(("http://", "https://")):
        return source

    # A path relative to the repo root, so the same .env works on a Windows
    # laptop and a Linux host. An absolute "C:\Users\..." would resolve to
    # nothing once deployed and the follow-up would lose its architecture image
    # - a required Section 06 element - with only a log line to show for it.
    if not os.path.isabs(source):
        source = os.path.join(ROOT, source)
    if not os.path.exists(source):
        raise UltraMsgError(0, f"media file not found: {source}")
    mime = mimetypes.guess_type(source)[0] or "application/octet-stream"
    with open(source, "rb") as fh:
        encoded = base64.b64encode(fh.read()).decode()
    size = len(encoded)
    log.info("inlining %s as base64 (%d KB)", os.path.basename(source), size // 1024)
    if size > WARN_MEDIA_BYTES:
        log.warning("%s is %d KB encoded - large uploads time out on a home link, "
                    "and WhatsApp recompresses anyway. Resize it under %d KB.",
                    os.path.basename(source), size // 1024, WARN_MEDIA_BYTES // 1024)
    return f"data:{mime};base64,{encoded}"


def send_media(to, kind, source, caption=None, filename=None):
    """Image or document, by URL or local path.

    `kind` is "image" or "document". An image carries its caption in the SAME
    message, which is how the follow-up satisfies all four Section 06 items at
    once instead of splitting across messages.
    """
    if kind not in ("image", "document"):
        raise UltraMsgError(0, f"unsupported media kind {kind!r}")

    fields = {"to": to, kind: media_value(source)}
    if caption:
        fields["caption"] = caption
    if kind == "document":
        fields["filename"] = filename or os.path.basename(str(source)) or "document.pdf"
    return _result(_request("POST", f"messages/{kind}", _auth(fields),
                            timeout=MEDIA_TIMEOUT))
