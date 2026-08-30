"""Vapi client. Only what the backend needs: place a call, read a call."""

import json
import urllib.error
import urllib.request

from .config import settings

API = "https://api.vapi.ai"


class VapiError(RuntimeError):
    def __init__(self, status, detail):
        super().__init__(f"Vapi {status}: {detail}")
        self.status = status
        self.detail = detail


def _request(method, path, body=None, timeout=20):
    req = urllib.request.Request(
        API + path,
        method=method,
        data=json.dumps(body).encode() if body is not None else None,
        headers={
            "Authorization": f"Bearer {settings.vapi_api_key}",
            "Content-Type": "application/json",
            "User-Agent": "ElevateBox-backend/1.0",
        },
    )
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            text = resp.read().decode()
            return json.loads(text) if text else {}
    except urllib.error.HTTPError as exc:
        raise VapiError(exc.code, exc.read().decode()[:600]) from exc
    except urllib.error.URLError as exc:
        raise VapiError(0, str(exc.reason)) from exc


def place_call(destination, assistant_id=None, overrides=None):
    """Dial. `destination` is supplied by the caller, which is always
    settings.allowed_destination - see dialler.place for why nothing else
    can reach this function with a different number.

    `overrides` is Vapi's assistantOverrides: per-call values layered on top of
    the deployed assistant. Used to hand a callback the context of the call it
    came from, without a second assistant.
    """
    body = {
        "assistantId": assistant_id or settings.vapi_assistant_id,
        "phoneNumberId": settings.vapi_phone_number_id,
        "customer": {"number": destination},
    }
    if overrides:
        body["assistantOverrides"] = overrides
    return _request("POST", "/call", body)


def get_call(provider_call_id):
    return _request("GET", f"/call/{provider_call_id}")
