#!/usr/bin/env python3
"""
Milestone 1 probe: place one automated English call to a test number we own.

Standard library only - nothing to pip install.

    python run_probe.py check       offline validation, no network, no spend
    python run_probe.py preflight   read-only API checks, no call placed, no spend
    python run_probe.py call --yes  places the call, then polls for the transcript

Safety: refuses to dial the evaluator's number under any circumstances.
"""

import json
import os
import re
import sys
import time
import urllib.error
import urllib.request

HERE = os.path.dirname(os.path.abspath(__file__))
ENV_PATH = os.path.join(HERE, ".env")
ASSISTANT_PATH = os.path.join(HERE, "assistant.json")
RESULTS_DIR = os.path.join(HERE, "results")
API = "https://api.vapi.ai"

# The evaluator's number. Never dialled by a probe - rehearsal happens on numbers we own.
EVALUATOR_NUMBER = "+918688664337"

OK, BAD, WARN, INFO = "  [ok]", "  [FAIL]", "  [warn]", "  [..]"


# ---------------------------------------------------------------- env + config

def load_env():
    """Parse .env into os.environ without printing any values."""
    if not os.path.exists(ENV_PATH):
        return
    with open(ENV_PATH, encoding="utf-8") as fh:
        for line in fh:
            line = line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            key, _, val = line.partition("=")
            os.environ.setdefault(key.strip(), val.strip().strip("'\""))


def load_assistant():
    """Load assistant.json and strip _comment keys (Vapi rejects unknown fields)."""
    with open(ASSISTANT_PATH, encoding="utf-8") as fh:
        raw = json.load(fh)
    cfg = {k: v for k, v in raw.items() if not k.startswith("_")}

    # .env overrides so the voice can be swapped without editing the config file.
    provider, voice_id = os.environ.get("VOICE_PROVIDER"), os.environ.get("VOICE_ID")
    if provider or voice_id:
        cfg.setdefault("voice", {})
        if provider:
            cfg["voice"]["provider"] = provider
        if voice_id:
            cfg["voice"]["voiceId"] = voice_id
    return cfg


# ---------------------------------------------------------------- http

def request(method, path, body=None, timeout=30):
    key = os.environ.get("VAPI_API_KEY", "")
    req = urllib.request.Request(
        API + path,
        method=method,
        data=json.dumps(body).encode() if body is not None else None,
        headers={
            "Authorization": "Bearer " + key,
            "Content-Type": "application/json",
            "User-Agent": "ElevateBox-voice-probe/1.0",
        },
    )
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            text = resp.read().decode()
            return json.loads(text) if text else {}
    except urllib.error.HTTPError as exc:
        detail = exc.read().decode()[:800]
        raise SystemExit(
            f"\n{BAD} Vapi API {exc.code} on {method} {path}\n  {detail}\n"
            + hint_for(exc.code, detail)
        )
    except urllib.error.URLError as exc:
        raise SystemExit(f"\n{BAD} Network error reaching Vapi: {exc.reason}")


def hint_for(code, detail):
    low = detail.lower()
    if code in (401, 403):
        return "  HINT: VAPI_API_KEY looks wrong. Use the PRIVATE key from Vapi -> API Keys.\n"
    if "voice" in low or "voiceid" in low:
        return ("  HINT: the voice ID was rejected. Pick a valid one in the Vapi dashboard\n"
                "        and set VOICE_PROVIDER / VOICE_ID in .env. See README.\n")
    if "phonenumber" in low:
        return ("  HINT: VAPI_PHONE_NUMBER_ID is wrong, or the Twilio number is not imported.\n"
                "        Run: python run_probe.py preflight\n")
    if code == 400 and "credential" in low:
        return "  HINT: that provider may need its own API key added in Vapi -> Provider Keys.\n"
    return ""


# ---------------------------------------------------------------- validation

def valid_e164(num):
    return bool(re.fullmatch(r"\+[1-9]\d{7,14}", num or ""))


def check_destination(num):
    """Hard safety gate. Returns list of failure strings."""
    problems = []
    if not num:
        return ["TEST_NUMBER is not set in .env"]

    # Compare on digits alone, so no formatting variant slips through:
    # 8688664337 / 08688664337 / +91-8688664337 / "+91 86886 64337" all match.
    digits = re.sub(r"\D", "", num)
    if digits.endswith(re.sub(r"\D", "", EVALUATOR_NUMBER)[-10:]):
        problems.append("TEST_NUMBER is the EVALUATOR'S number. Probes never dial it.")

    if not valid_e164(num):
        problems.append(f"TEST_NUMBER '{num}' is not E.164 (needs +91XXXXXXXXXX, no spaces or dashes)")
    elif not num.startswith("+91"):
        problems.append(f"TEST_NUMBER '{num}' is not an Indian (+91) number")
    return problems


def cmd_check():
    """Everything verifiable with no network and no spend."""
    print("\nOFFLINE CHECK  (no network, no spend)\n" + "-" * 46)
    fails = []

    # 1. assistant.json
    try:
        cfg = load_assistant()
        print(f"{OK} assistant.json parses")
    except Exception as exc:
        print(f"{BAD} assistant.json: {exc}")
        return 1

    for field in ("transcriber", "voice", "model", "firstMessage"):
        if field in cfg:
            print(f"{OK} {field} present")
        else:
            print(f"{BAD} {field} MISSING")
            fails.append(field)

    t = cfg.get("transcriber", {})
    if t.get("provider") == "soniox" and t.get("model") == "stt-rt-v5":
        print(f"{OK} transcriber is soniox/stt-rt-v5, languages={t.get('languages')}")
    else:
        print(f"{WARN} transcriber is {t.get('provider')}/{t.get('model')} - expected soniox/stt-rt-v5")

    v = cfg.get("voice", {})
    print(f"{OK} voice is {v.get('provider')} / {v.get('voiceId')}")
    if "<" in str(v.get("voiceId", "")):
        print(f"{BAD} voiceId is still a placeholder")
        fails.append("voiceId")

    if any(k.startswith("_") for k in cfg):
        print(f"{BAD} _comment keys leaked into the payload")
        fails.append("_comment")
    else:
        print(f"{OK} _comment keys stripped from payload")

    # 2. credentials present (never printed)
    print()
    if not os.path.exists(ENV_PATH):
        print(f"{BAD} .env does not exist - copy .env.example to .env")
        fails.append(".env")
    for var in ("VAPI_API_KEY", "VAPI_PHONE_NUMBER_ID", "TEST_NUMBER"):
        val = os.environ.get(var, "")
        if val:
            print(f"{OK} {var} is set ({len(val)} chars, value not shown)")
        else:
            print(f"{BAD} {var} is EMPTY  <-- you need to fill this in")
            fails.append(var)

    # 3. destination safety
    print()
    dest = os.environ.get("TEST_NUMBER", "")
    problems = check_destination(dest)
    if not problems:
        print(f"{OK} destination {dest} is a valid +91 number and is not the evaluator's")
    else:
        for p in problems:
            print(f"{BAD} {p}")
            fails.append("destination")

    # 4. the guard itself actually works, against every spelling of that number
    variants = [
        "+918688664337", "+91 8688664337", "+91-8688664337",
        "+91 86886 64337", "918688664337", "08688664337", "8688664337",
    ]
    leaked = [v for v in variants if not check_destination(v)]
    if leaked:
        print(f"{BAD} SAFETY GUARD IS BROKEN - these got through: {leaked}")
        fails.append("guard")
    else:
        print(f"{OK} safety guard rejects all {len(variants)} spellings of the "
              f"evaluator's number (self-tested)")

    print("\n" + "-" * 46)
    if fails:
        print(f"NOT READY - {len(fails)} item(s) outstanding: {', '.join(dict.fromkeys(fails))}")
        print("Fill in .env, then re-run:  python run_probe.py check")
        return 1
    print("READY. Next (needs Twilio active):  python run_probe.py preflight")
    return 0


# ---------------------------------------------------------------- online

def cmd_preflight():
    """Read-only API checks. Places no call. Costs nothing."""
    print("\nPREFLIGHT  (read-only, no call placed, no spend)\n" + "-" * 46)
    if cmd_check() != 0:
        return 1

    print(f"\n{INFO} verifying API key and phone number ...")
    numbers = request("GET", "/phone-number")
    if not isinstance(numbers, list):
        numbers = numbers.get("results", [])
    print(f"{OK} API key valid - {len(numbers)} phone number(s) on the account")

    want = os.environ.get("VAPI_PHONE_NUMBER_ID", "")
    match = next((n for n in numbers if n.get("id") == want), None)
    if match:
        print(f"{OK} VAPI_PHONE_NUMBER_ID matches: {match.get('number', '?')} "
              f"({match.get('provider', '?')})")
    else:
        print(f"{BAD} VAPI_PHONE_NUMBER_ID not found on this account.")
        if numbers:
            print("      Numbers available:")
            for n in numbers:
                print(f"        {n.get('id')}  {n.get('number', '?')}  ({n.get('provider', '?')})")
        else:
            print("      No numbers imported yet. Vapi -> Phone Numbers -> Import (Twilio).")
        return 1

    # Creating an assistant costs nothing, and it is the ONLY way to have Vapi
    # validate the voice / transcriber / model config. Doing it here means a bad
    # voiceId fails now, for free, instead of halfway through a real call attempt.
    print(f"\n{INFO} validating assistant config server-side (free, no call) ...")
    existing = os.environ.get("VAPI_ASSISTANT_ID", "").strip()
    if existing:
        info = request("GET", f"/assistant/{existing}")
        print(f"{OK} existing assistant {existing} is valid")
        print(f"      voice: {info.get('voice', {}).get('provider')} / "
              f"{info.get('voice', {}).get('voiceId')}")
    else:
        created = request("POST", "/assistant", load_assistant())
        print(f"{OK} config accepted - voice, transcriber and model are all valid")
        print("      Save this to .env so the call reuses it instead of making another:")
        print(f"        VAPI_ASSISTANT_ID={created['id']}")

    print("\n" + "-" * 46)
    print("PREFLIGHT PASSED. To place the real call:  python run_probe.py call --yes")
    return 0


def cmd_call():
    """Create the assistant if needed, place the call, poll for the transcript."""
    print("\nPLACING CALL  (this spends money and rings a real phone)\n" + "-" * 46)

    # Explicit opt-in. This is the only command in the file that costs money or
    # dials anything, so it must never run by accident or by tab-completion.
    if "--yes" not in sys.argv:
        print(f"{BAD} refusing to dial without an explicit confirmation.")
        print("      Re-run:  python run_probe.py call --yes")
        return 1

    if cmd_check() != 0:
        return 1

    dest = os.environ["TEST_NUMBER"]
    assistant_id = os.environ.get("VAPI_ASSISTANT_ID", "").strip()

    if assistant_id:
        print(f"\n{OK} reusing assistant {assistant_id}")
    else:
        print(f"\n{INFO} creating assistant ...")
        created = request("POST", "/assistant", load_assistant())
        assistant_id = created["id"]
        print(f"{OK} assistant created: {assistant_id}")
        print("      Add this to .env to reuse it:")
        print(f"        VAPI_ASSISTANT_ID={assistant_id}")

    print(f"\n{INFO} dialling {dest} ...")
    call = request("POST", "/call", {
        "assistantId": assistant_id,
        "phoneNumberId": os.environ["VAPI_PHONE_NUMBER_ID"],
        "customer": {"number": dest},
    })
    call_id = call.get("id")
    print(f"{OK} call queued: {call_id}")
    print("\n  >>> ANSWER THE PHONE. Talk for ~90 seconds, then say goodbye. <<<\n")

    # Poll until the call ends (max ~6 min).
    last = None
    for _ in range(72):
        time.sleep(5)
        info = request("GET", f"/call/{call_id}")
        status = info.get("status")
        if status != last:
            print(f"{INFO} status: {status}")
            last = status
        if status == "ended":
            return report(info, call_id)
    print(f"{WARN} still running after 6 minutes - check the Vapi dashboard for {call_id}")
    return 0


def report(info, call_id):
    print("\n" + "=" * 46)
    print("RESULT")
    print("=" * 46)
    print(f"  ended reason : {info.get('endedReason')}")
    started, ended = info.get("startedAt"), info.get("endedAt")
    print(f"  started      : {started}")
    print(f"  ended        : {ended}")
    if info.get("cost") is not None:
        print(f"  cost         : ${info['cost']}")
    if info.get("recordingUrl"):
        print(f"  recording    : {info['recordingUrl']}")

    transcript = info.get("transcript")
    if transcript:
        print("\n--- TRANSCRIPT ---")
        print(transcript)
    else:
        print(f"\n{WARN} no transcript. If the call never connected, check Twilio error 21215")
        print("      (India not enabled in Voice Geographic Permissions).")

    os.makedirs(RESULTS_DIR, exist_ok=True)
    path = os.path.join(RESULTS_DIR, f"{call_id}.json")
    with open(path, "w", encoding="utf-8") as fh:
        json.dump(info, fh, indent=2)
    print(f"\n  full payload saved: {os.path.relpath(path, HERE)}")

    reason = (info.get("endedReason") or "").lower()
    if "customer-ended" in reason or "assistant-ended" in reason or transcript:
        print("\n  MILESTONE 1: a two-way English call happened. Fill in test-script.md.")
    else:
        print("\n  MILESTONE 1 NOT met - see endedReason above.")
    return 0


COMMANDS = {"check": cmd_check, "preflight": cmd_preflight, "call": cmd_call}

if __name__ == "__main__":
    load_env()
    cmd = sys.argv[1] if len(sys.argv) > 1 else "check"
    if cmd not in COMMANDS:
        print(__doc__)
        sys.exit(2)
    sys.exit(COMMANDS[cmd]())
