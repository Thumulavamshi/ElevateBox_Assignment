#!/usr/bin/env python3
"""Local end-to-end check. No network, no phone calls, no spend.

Replays a realistic Vapi webhook sequence against the app and asserts the
persistence, idempotency and safety properties hold.

    python backend/smoke_test.py
"""

import json
import os
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)

# Point at a throwaway DB before anything imports settings.
os.environ["DATABASE_PATH"] = os.path.join(tempfile.mkdtemp(), "smoke.db")
os.environ.setdefault("VAPI_API_KEY", "test-key")
os.environ.setdefault("VAPI_PHONE_NUMBER_ID", "test-phone")
os.environ.setdefault("VAPI_ASSISTANT_ID", "test-assistant")
os.environ["ALLOWED_DESTINATION"] = "+919876543210"
# Pinned: the real .env may point the mid-call action at hello_world (which
# takes no parameters), and the tests below assert on parameter composition.
os.environ["WHATSAPP_TEMPLATE_MIDCALL"] = "elevatebox_call_recap_now"
os.environ["WHATSAPP_MIDCALL_PARAMS"] = "1"
# Pinned so the provider in the real .env cannot change what these tests mean.
# The free-form path is exercised explicitly further down by flipping it.
os.environ["WHATSAPP_PROVIDER"] = "meta"
os.environ.setdefault("YOUR_NAME", "Test Sender")
os.environ.setdefault("YOUR_MOBILE_NUMBER", "+910000000000")

from fastapi.testclient import TestClient             # noqa: E402
from app import actions, classifier, db, extraction, vapi, whatsapp  # noqa: E402
from app.config import EVALUATOR_NUMBER, settings     # noqa: E402
from app.main import app                              # noqa: E402

# Stub the WhatsApp transport BEFORE anything can run a handler. Once real
# credentials exist in .env, the post-call follow-up handler would otherwise
# send a REAL message every time someone runs the smoke test - the same trap the
# Anthropic key sprang earlier. Nothing in this file may reach a live service.
WA_SENT = []
whatsapp._post = lambda payload: (WA_SENT.append(payload) or
                                  {"messages": [{"id": "wamid.TEST"}]})

# Second transport, same trap. UltraMsg sends to a REAL linked WhatsApp account
# with no template gate at all, so an unstubbed handler here would message a
# live handset on every smoke run - and unlike Meta there is no approval step to
# fail safe behind.
UM_SENT = []
from app import ultramsg                                  # noqa: E402
ultramsg._request = lambda method, path, fields, timeout=None: (
    UM_SENT.append({"path": path, **{k: v for k, v in fields.items() if k != "token"}})
    or {"sent": "true", "message": "ok", "id": "um.TEST"})
whatsapp.MIN_GAP_SECONDS = 0          # never sleep the 6s inter-message gap in tests
settings.wa_phone_number_id = "TEST_PNID"
settings.wa_access_token = "TEST_TOKEN"

# The smoke test must never reach a paid API: it has to stay free, fast and
# deterministic. Once ANTHROPIC_API_KEY existed this file silently started
# making real billed calls, so the model is stubbed. The RULES overlay is left
# real - it is the part these tests are actually asserting on.
classifier.available = lambda provider=None: (True, "stubbed for tests")
classifier.classify_transcript = lambda transcript, provider=None: classifier.apply_rules(
    classifier.LeadRead(label="cold", confidence=0.5, barrier="none",
                        evidence_quote="", reasoning="stub"),
    transcript,
)


# Same trap, second door. Extraction shares the classifier's transport, so
# stubbing classify_transcript alone would leave extract_slots making real billed
# calls on every smoke run. This is the choke point both go through.
def _no_model(*a, **kw):
    raise AssertionError("the smoke test must never reach a real model")


classifier.run_structured = _no_model

def slots(**kw):
    """An ExtractedSlots with everything empty except what is named."""
    empty = extraction.Slot(value="", quote="", confidence=0.0)
    fields = {n: empty for n in extraction.SLOT_NAMES}
    for name, (value, quote) in kw.items():
        fields[name] = extraction.Slot(value=value, quote=quote, confidence=0.9)
    return extraction.ExtractedSlots(**fields)


# What the extractor is pretending to have found. A one-element list so tests can
# swap it without rebinding a global. The merge, quote-verification and
# persistence logic underneath are all the real ones.
EXTRACTED = [slots()]
extraction.extract_from_transcript = lambda transcript, provider=None: EXTRACTED[0]

PASS, FAIL = 0, 0


def check(label, cond, detail=""):
    global PASS, FAIL
    if cond:
        PASS += 1
        print(f"  [ok]   {label}")
    else:
        FAIL += 1
        print(f"  [FAIL] {label}  {detail}")


# Never let the smoke test reach the real Vapi API.
PLACED = []
_SEQ = [0]


OVERRIDES = []


def _fake_place_call(destination, assistant_id=None, overrides=None):
    PLACED.append(destination)
    OVERRIDES.append(overrides or {})
    _SEQ[0] += 1
    return {"id": f"prov-call-{_SEQ[0]}", "status": "queued"}


vapi.place_call = _fake_place_call

# What the provider would say if asked about a call. The reconciliation sweeper
# polls this when a webhook goes missing.
VAPI_CALLS = {}
vapi.get_call = lambda provider_call_id: VAPI_CALLS.get(
    provider_call_id, {"status": "in-progress"})

# A fake action handler, so the bus is exercised rather than just declared.
SENT = []


@actions.handler("whatsapp_hot")
async def _fake_send(call_id, payload):
    SENT.append((call_id, payload))
    return {"message_id": "wamid.TEST"}


def webhook(client, msg, secret=None):
    headers = {"x-vapi-secret": secret} if secret is not None else {}
    return client.post("/vapi/webhook", json={"message": msg}, headers=headers)


def main():
    with TestClient(app) as client:
        print("\nHEALTH + CONFIG")
        h = client.get("/health").json()
        check("health ok", h["status"] == "ok")
        check("db initialised", os.path.exists(settings.db_path))
        check("allowed destination is our test number",
              h["allowed_destination"] == "+919876543210")
        check("health flags evaluator number (currently false)",
              h["destination_is_evaluator"] is False)
        check("action registry shows the whatsapp handlers as wired",
              h["actions"]["whatsapp_hot"] == "wired"
              and h["actions"]["whatsapp_followup"] == "wired", h["actions"])
        check("and still reports genuinely unbuilt actions as stubs",
              h["actions"]["callback_confirm"] == "stub", h["actions"])

        print("\nTRIGGER SAFETY")
        check("endpoint accepts no destination parameter",
              "requestBody" not in (client.get("/openapi.json").json()
                                    ["paths"]["/calls"]["post"]))
        r = client.post("/calls", json={"number": EVALUATOR_NUMBER})
        check("a number in the body is ignored", r.status_code == 200)
        check("dialled ONLY the configured destination", PLACED == ["+919876543210"], PLACED)
        call_id = r.json()["call_id"]

        print("\nWEBHOOK INGRESS")
        # A call placed outside the backend (agent.py dials Vapi directly) must
        # still be tracked, or its transcripts are never classified and its tool
        # calls are answered with nothing. This exact gap silently killed a live
        # mid-call test: 648 webhooks arrived, every one with a NULL call_id.
        before = len(db.list_calls(50))
        webhook(client, {"type": "status-update", "status": "ringing",
                         "call": {"id": "adopt-me",
                                  "customer": {"number": "+919876543210"}}})
        adopted = db.call_id_for_provider("adopt-me")
        check("a call we did not place is adopted, not dropped", adopted is not None)
        check("adoption creates exactly one row", len(db.list_calls(50)) == before + 1)

        webhook(client, {"type": "status-update", "status": "in-progress",
                         "call": {"id": "adopt-me"}})
        check("a second webhook reuses the adopted row",
              len(db.list_calls(50)) == before + 1
              and db.get_call(adopted)["status"] == "in-progress")

        r = webhook(client, {"type": "tool-calls", "call": {"id": "adopt-me"},
                             "toolCallList": [{"id": "tc-a", "function":
                                               {"name": "send_details_now",
                                                "arguments": {}}}]})
        check("a tool call on an adopted call is answered AND acted on",
              r.json()["results"][0]["toolCallId"] == "tc-a"
              and any(a["type"] == "whatsapp_hot" for a in db.get_actions(adopted)),
              r.json())

        webhook(client, {"type": "status-update", "status": "in-progress",
                         "call": {"id": "prov-call-1"}})
        check("status update mapped to our call",
              db.get_call(call_id)["status"] == "in-progress")

        webhook(client, {"type": "transcript", "transcriptType": "partial",
                         "role": "user", "transcript": "umm",
                         "call": {"id": "prov-call-1"}})
        check("partial transcripts are not persisted", len(db.get_turns(call_id)) == 0)

        for role, text in [("assistant", "Hi, this is Maya."),
                           ("user", "I sell custom t-shirts."),
                           ("user", "I sell custom t-shirts.")]:      # duplicate
            webhook(client, {"type": "transcript", "transcriptType": "final",
                             "role": role, "transcript": text,
                             "call": {"id": "prov-call-1"}})
        turns = db.get_turns(call_id)
        check("final transcripts persisted, duplicate dropped", len(turns) == 2,
              [t["text"] for t in turns])
        check("turn order preserved", [t["seq"] for t in turns] == [0, 1])

        print("\nTOOL CALLS  (the mid-call action path)")
        r = webhook(client, {"type": "tool-calls", "call": {"id": "prov-call-1"},
                             "toolCallList": [{"id": "tc-1", "function":
                                               {"name": "send_details_now", "arguments": {}}}]})
        body = r.json()
        check("tool call answered synchronously", r.status_code == 200)
        check("result string is speakable", "WhatsApp" in body["results"][0]["result"], body)
        sent_before = len(SENT) - 1   # adoption fired one already
        check("handler actually ran", len(SENT) == sent_before + 1, SENT)
        acts = db.get_actions(call_id)
        check("action recorded as sent", len(acts) == 1 and acts[0]["status"] == "sent",
              [(a["type"], a["status"]) for a in acts])
        check("trigger source recorded", acts[0]["trigger_source"] == "tool_call")

        print("\nIDEMPOTENCY  (two trigger paths, one message)")
        webhook(client, {"type": "tool-calls", "call": {"id": "prov-call-1"},
                         "toolCallList": [{"id": "tc-2", "function":
                                           {"name": "send_details_now", "arguments": {}}}]})
        check("second identical trigger is a no-op",
              len(db.get_actions(call_id)) == 1 and len(SENT) == sent_before + 1,
              f"actions={len(db.get_actions(call_id))} sent={len(SENT)}")
        check("watchdog path shares the key",
              actions.dispatch(call_id, "whatsapp_hot", trigger_source="watchdog") is None)

        print("\nUNKNOWN TOOL")
        r = webhook(client, {"type": "tool-calls", "call": {"id": "prov-call-1"},
                             "toolCallList": [{"id": "tc-3", "function":
                                               {"name": "nope", "arguments": {}}}]})
        check("unknown tool answered, not crashed",
              r.status_code == 200 and "Unknown" in r.json()["results"][0]["result"])

        print("\nEND OF CALL")
        webhook(client, {"type": "end-of-call-report", "endedReason": "customer-ended-call",
                         "call": {"id": "prov-call-1", "startedAt": "2026-08-28T10:00:00Z"},
                         "summary": "Sells t-shirts.",
                         "artifact": {"recordingUrl": "https://example/rec.wav",
                                      "messages": [
                                          {"role": "user", "message": "I sell custom t-shirts."},
                                          {"role": "bot", "message": "How many designs?"},
                                          {"role": "user", "message": "About fifty."}]}})
        call = db.get_call(call_id)
        check("call marked ended", call["status"] == "ended")
        check("ended reason stored", call["ended_reason"] == "customer-ended-call")
        check("recording url stored", call["recording_url"] == "https://example/rec.wav")
        texts = [t["text"] for t in db.get_turns(call_id)]
        check("backfill added only missing turns, no duplicates",
              texts.count("I sell custom t-shirts.") == 1 and "About fifty." in texts, texts)
        followup = [a for a in db.get_actions(call_id) if a["type"] == "whatsapp_followup"]
        check("post-call follow-up was claimed exactly once", len(followup) == 1)
        # It runs for real here (credentials are absent in tests), so it fails on
        # config rather than on a missing handler. Either way the ledger records
        # that something WANTED to fire - that visibility is the point.
        check("follow-up attempt recorded in the ledger",
              followup[0]["status"] in ("pending", "sending", "sent", "failed"),
              followup[0])

        print("\nCLASSIFICATION  (rules path - works with no API key)")
        # Fresh call, so the earlier idempotency key cannot mask the result.
        PLACED.clear()
        call2 = client.post("/calls").json()["call_id"]
        for role, text in [("assistant", "What do you sell?"),
                           ("user", "We do custom t-shirts. Send me the details.")]:
            webhook(client, {"type": "transcript", "transcriptType": "final",
                             "role": role, "transcript": text,
                             "call": {"id": "prov-call-2"}})
        cls = db.latest_classification(call2)
        check("lead classified hot by the rules overlay",
              cls is not None and cls["label"] == "hot", cls)
        check("evidence quote captured",
              bool(cls) and "Send me the details" in (cls["evidence_quote"] or ""))
        hot = [a for a in db.get_actions(call2) if a["type"] == "whatsapp_hot"]
        check("watchdog fired the mid-call action", len(hot) == 1, db.get_actions(call2))
        check("attributed to the watchdog, not a tool call",
              bool(hot) and hot[0]["trigger_source"] == "watchdog", hot)

        print("\nCLASSIFICATION  (a refusal must NOT fire anything)")
        PLACED.clear()
        call3 = client.post("/calls").json()["call_id"]
        webhook(client, {"type": "transcript", "transcriptType": "final", "role": "user",
                         "transcript": "Not interested. Send me the details if you want.",
                         "call": {"id": "prov-call-3"}})
        # The invariant is about the ACTION, not the label. An earlier version
        # asserted "no classification stored", which only held because no API key
        # existed - it passed for the wrong reason and broke the moment one did.
        cls3 = db.latest_classification(call3)
        check("refusal is not read as hot",
              cls3 is None or cls3["label"] != "hot", cls3)
        check("and no mid-call action fired", db.get_actions(call3) == [], db.get_actions(call3))

        print("\nQUOTE VERIFICATION  (pure functions - no key, no labels)")
        # The one part of extraction quality that can be checked without grading
        # our own homework: did the lead actually say this?
        vturns = [
            {"seq": 0, "role": "assistant",
             "text": "You're looking at seventy thousand to one and a half lakh."},
            {"seq": 1, "role": "user", "text": "Uh, I sold a. Custom-made T-shirts�"},
            {"seq": 2, "role": "user", "text": "In our catalog we try to maintain around 3 to 2. 100."},
        ]
        q, seq = extraction.attach_quote("Custom-made T-shirts", "custom t-shirts", vturns)
        check("a real quote is kept, with its turn", q == "Custom-made T-shirts" and seq == 1,
              (q, seq))
        q, seq = extraction.attach_quote("I sell custom made t-shirts online",
                                         "custom-made T-shirts", vturns)
        check("a tidied-up quote is replaced by the lead's actual turn",
              q == vturns[1]["text"].strip() and seq == 1, (q, seq))
        q, seq = extraction.attach_quote("we can do it for one lakh", "one lakh", vturns)
        check("a quote the lead never said is dropped entirely", q is None and seq is None,
              (q, seq))
        # The live call had Maya quoting prices the lead never named. Attributing
        # that back to the lead would be a fabricated quote in the follow-up.
        q, seq = extraction.attach_quote("seventy thousand to one and a half lakh",
                                         "70,000 to 1.5 lakh", vturns)
        check("the AGENT's words are never accepted as the lead's quote",
              q is None and seq is None, (q, seq))
        check("punctuation and STT noise do not break a match",
              extraction.attach_quote("around 3 to 2 100", "", vturns)[1] == 2)

        print("\nEXTRACTION  (model stubbed - merge and persistence are real)")
        PLACED.clear()
        call4 = client.post("/calls").json()["call_id"]
        for role, text in [("assistant", "What do you sell?"),
                           ("user", "We make custom-made T-shirts."),
                           ("assistant", "How many designs?"),
                           ("user", "Around three hundred items, and I need it in a month.")]:
            EXTRACTED[0] = slots(
                products=("custom-made t-shirts", "We make custom-made T-shirts."),
                # Quote paraphrased, value still verbatim -> falls back to the turn.
                timeline=("in a month", "I want the store live in a month"),
                # Neither quote nor value appears -> value kept, quote refused.
                catalogue_size=("300 designs", "we carry 300 designs"),
            )
            webhook(client, {"type": "transcript", "transcriptType": "final",
                             "role": role, "transcript": text,
                             "call": {"id": "prov-call-4"}})
        got = db.get_slots(call4)
        check("extracted value persisted", got.get("products", {}).get("value")
              == "custom-made t-shirts", got.get("products"))
        check("verbatim quote stored against its turn",
              got["products"]["raw_quote"] == "We make custom-made T-shirts."
              and got["products"]["source_turn_seq"] == 1, got.get("products"))
        check("a paraphrase falls back to the lead's real words",
              got.get("timeline", {}).get("raw_quote") == "Around three hundred items, "
              "and I need it in a month.", got.get("timeline"))
        check("an unverifiable quote is dropped but the value survives",
              got.get("catalogue_size", {}).get("value") == "300 designs"
              and got["catalogue_size"]["raw_quote"] is None, got.get("catalogue_size"))
        check("slots the lead never mentioned stay empty",
              "budget" not in got and "features" not in got, list(got))
        check("coverage reflects what was actually extracted",
              client.get(f"/calls/{call4}").json()["coverage"]
              == {"products": True, "catalogue_size": True, "timeline": True,
                  "features": False, "budget": False},
              client.get(f"/calls/{call4}").json()["coverage"])

        # A later pass that finds nothing means "not mentioned again", never
        # "retract it". Forgetting what the lead said would be worse than stale.
        EXTRACTED[0] = slots(budget=("one lakh", "about one lakh"))
        webhook(client, {"type": "transcript", "transcriptType": "final",
                         "role": "user", "transcript": "Budget is about one lakh.",
                         "call": {"id": "prov-call-4"}})
        got = db.get_slots(call4)
        check("a later empty pass does not erase an earlier fact",
              got["products"]["value"] == "custom-made t-shirts", got.get("products"))
        check("and new facts still land", got.get("budget", {}).get("value") == "one lakh",
              got.get("budget"))

        print("\nWHATSAPP PAYLOADS  (transport stubbed - no real send, no cost)")
        sent = WA_SENT          # stubbed at import time, see top of file
        dest = settings.allowed_destination

        whatsapp.send_template(dest, "tpl_x", body_params=["a", "b"],
                               lang=settings.wa_template_lang)
        p = sent[-1]
        check("template payload shape", p["type"] == "template"
              and p["template"]["name"] == "tpl_x", p)
        check("destination normalised to digits only", p["to"].isdigit(), p["to"])
        check("body params sent in order",
              [x["text"] for x in p["template"]["components"][0]["parameters"]] == ["a", "b"], p)

        # Meta rejects the whole send if a parameter contains a newline, so an
        # extracted quote with a line break would kill the mid-call message.
        whatsapp.send_template(dest, "tpl_x", body_params=["one\ntwo\tthree     four"])
        cleaned = sent[-1]["template"]["components"][0]["parameters"][0]["text"]
        check("newlines/tabs/4+ spaces stripped from params",
              "\n" not in cleaned and "\t" not in cleaned and "    " not in cleaned,
              repr(cleaned))

        whatsapp.send_template(dest, "tpl_img", body_params=["a"],
                               header={"type": "image", "link": "https://x/a.png"})
        hdr = sent[-1]["template"]["components"][0]
        check("image header shape",
              hdr["type"] == "header" and hdr["parameters"][0]["image"]["link"] == "https://x/a.png",
              hdr)

        whatsapp.send_template(dest, "tpl_doc", body_params=["a"],
                               header={"type": "document", "link": "https://x/cv.pdf",
                                       "filename": "cv.pdf"})
        doc = sent[-1]["template"]["components"][0]["parameters"][0]["document"]
        check("document header carries filename", doc["filename"] == "cv.pdf", doc)

        print("\nWHATSAPP SAFETY")
        before = len(sent)
        try:
            whatsapp.send_template("+919999999999", "tpl_x", body_params=["a"])
            check("a non-allowed destination is refused", False, "it sent!")
        except whatsapp.WhatsAppError:
            check("a non-allowed destination is refused", len(sent) == before)
        try:
            whatsapp.send_template(EVALUATOR_NUMBER, "tpl_x", body_params=["a"])
            check("the evaluator's number is refused", False, "it sent!")
        except whatsapp.WhatsAppError:
            check("the evaluator's number is refused", len(sent) == before)

        print("\nWHATSAPP HANDLERS  (composition from real slots)")
        from app import handlers
        # Written to call2, not call_id, so this cannot pollute the coverage
        # assertion made against call_id further down.
        db.upsert_slot(call2, "products", "custom t-shirts", raw_quote="we do custom tees")
        db.upsert_slot(call2, "budget", "1000 USD", raw_quote="around\n1,000 US dollars")
        before = len(sent)
        await_res = handlers.send_mid_call.__wrapped__ if hasattr(
            handlers.send_mid_call, "__wrapped__") else handlers.send_mid_call
        import asyncio
        asyncio.get_event_loop_policy().new_event_loop().run_until_complete(
            await_res(call2, {}))
        params = [x["text"] for x in sent[-1]["template"]["components"][0]["parameters"]]
        check("mid-call uses extracted slot values", "custom t-shirts" in params[0], params)
        check("missing slots get an honest fallback, never an invented value",
              params[2] == handlers.FALLBACKS["timeline"], params)
        check("mid-call has no media header (fastest delivery)",
              all(c["type"] != "header" for c in sent[-1]["template"]["components"]))

        print("\nFREE-FORM PROVIDER  (UltraMsg - no templates, no approval)")
        settings.wa_provider = "ultramsg"
        settings.um_instance, settings.um_token = "instanceTEST", "tokenTEST"
        settings.wa_architecture_url = "https://example/arch.png"
        settings.wa_resume_url = "https://example/cv.pdf"
        try:
            check("provider reports free-form support", whatsapp.supports_freeform())
            check("config check passes on the ultramsg credentials",
                  whatsapp.configured()[0], whatsapp.configured())

            UM_SENT.clear()
            run = asyncio.get_event_loop_policy().new_event_loop().run_until_complete
            run(handlers.send_mid_call(call2, {}))
            body = UM_SENT[-1]["body"]
            check("mid-call goes out as free-form chat",
                  UM_SENT[-1]["path"] == "messages/chat", UM_SENT[-1]["path"])
            check("mid-call quotes real extracted values", "custom t-shirts" in body, body)
            check("mid-call carries the mobile number",
                  "+910000000000" in body, body)
            check("free-form keeps real line breaks (templates could not)",
                  "\n" in body)
            check("a slot we never learned is OMITTED, not padded with a fallback",
                  handlers.FALLBACKS["timeline"] not in body, body)

            UM_SENT.clear()
            run(handlers.send_followup(call2, {}))
            sent = UM_SENT[-1]
            check("follow-up rides on the architecture image",
                  sent["path"] == "messages/image"
                  and sent["image"] == "https://example/arch.png", sent["path"])
            cap = sent["caption"]
            # Section 06 wants all four in the message that reaches them.
            check("caption carries the call context", "custom t-shirts" in cap, cap[:120])
            check("caption quotes something they actually said",
                  '"' in cap and "1,000 US dollars" in cap, cap[:200])
            check("caption carries the mobile number", "+910000000000" in cap)
            check("so one message holds all four Section 06 items",
                  all(x in cap for x in ("custom t-shirts", "+910000000000"))
                  and sent["image"], sent["path"])

            UM_SENT.clear()
            run(handlers.send_resume(call2, {"demo_url": "https://demo"}))
            check("resume goes as a document, separately",
                  UM_SENT[-1]["path"] == "messages/document"
                  and UM_SENT[-1]["document"] == "https://example/cv.pdf", UM_SENT[-1])

            # The guards must survive a provider swap - that is the whole point
            # of routing both transports through one _guard().
            before = len(UM_SENT)
            try:
                whatsapp.send_text(EVALUATOR_NUMBER, "nope")
                check("evaluator still refused on the new provider", False, "it sent!")
            except whatsapp.WhatsAppError:
                check("evaluator still refused on the new provider", len(UM_SENT) == before)
            try:
                whatsapp.send_text("+919999999999", "nope")
                check("non-allowed destination still refused", False, "it sent!")
            except whatsapp.WhatsAppError:
                check("non-allowed destination still refused", len(UM_SENT) == before)
            try:
                whatsapp.send_template(dest, "any_template")
                check("templates are refused on a provider that has none", False, "sent!")
            except whatsapp.WhatsAppError as exc:
                check("templates are refused on a provider that has none",
                      "no templates" in str(exc), str(exc))
        finally:
            settings.wa_provider = "meta"

        print("\nWEBHOOK SECRET")
        settings.webhook_secret = "s3cret"
        check("wrong secret rejected",
              webhook(client, {"type": "status-update", "call": {"id": "prov-call-1"}},
                      secret="wrong").status_code == 401)
        check("right secret accepted",
              webhook(client, {"type": "status-update", "call": {"id": "prov-call-1"}},
                      secret="s3cret").status_code == 200)
        settings.webhook_secret = ""

        print("\nREAD ROUTES")
        detail = client.get(f"/calls/{call_id}").json()
        check("detail returns turns", len(detail["turns"]) >= 3)
        check("detail returns coverage for all five slots",
              set(detail["coverage"]) == {"products", "catalogue_size", "timeline",
                                          "features", "budget"})
        check("coverage claims nothing when extraction found nothing",
              not any(detail["coverage"].values()))
        check("events captured", len(db.get_events(call_id)) > 5)
        check("404 on unknown call", client.get("/calls/nope").status_code == 404)

        print("\nTIME HANDLING")
        ist = db.to_ist("2026-08-28T10:00:00+00:00")
        check("UTC -> IST is +5:30", ist.hour == 15 and ist.minute == 30, str(ist))

        print("\nCALLBACK BOOKING  (from the tool call, as the agent would)")
        from app import callbacks as cb
        PLACED.clear()
        call5 = client.post("/calls").json()["call_id"]
        r = webhook(client, {"type": "tool-calls", "call": {"id": "prov-call-5"},
                             "toolCallList": [{"id": "cb-1", "function":
                                               {"name": "schedule_callback",
                                                "arguments": {"when": "tomorrow morning"}}}]})
        said = r.json()["results"][0]["result"]
        booked = db.get_callbacks(call5)
        check("spoken time booked from a tool call", len(booked) == 1
              and booked[0]["status"] == "pending", booked)
        # The agent has to be able to SAY the resolved time - that sentence is
        # the only part of this row the evaluator can actually hear.
        check("the result tells the agent a real time to say back",
              "tomorrow morning" in said and "at 10" in said, said)
        check("the resolving rule is recorded, so a vague phrase is defensible",
              "morning=10:00" in (booked[0]["resolution_rule"] or ""), booked[0])

        # Vapi's arguments arrive as an object from some providers and a JSON
        # string from others. Losing a booking to that would be a silly way to
        # drop ten points.
        webhook(client, {"type": "tool-calls", "call": {"id": "prov-call-5"},
                         "toolCallList": [{"id": "cb-2", "function":
                                           {"name": "schedule_callback",
                                            "arguments": '{"when": "next monday"}'}}]})
        booked = db.get_callbacks(call5)
        check("arguments as a JSON string still book", len(booked) == 2, booked)
        check("restating the time replaces the booking, never adds a second",
              [b["status"] for b in booked] == ["cancelled", "pending"],
              [b["status"] for b in booked])

        r = webhook(client, {"type": "tool-calls", "call": {"id": "prov-call-5"},
                             "toolCallList": [{"id": "cb-3", "function":
                                               {"name": "schedule_callback",
                                                "arguments": {"when": "whenever"}}}]})
        check("an unparseable time books nothing and says so",
              len(db.get_callbacks(call5)) == 2
              and "Could not work out" in r.json()["results"][0]["result"],
              r.json()["results"][0]["result"])

        print("\nCALLBACK EXECUTION  (the worker actually dials)")
        from datetime import datetime, timedelta, timezone as _tzone
        now = datetime.now(_tzone.utc)
        pending = [b for b in db.get_callbacks(call5) if b["status"] == "pending"][0]

        PLACED.clear()
        asyncio.get_event_loop_policy().new_event_loop().run_until_complete(cb.tick(now))
        check("a callback that is not due yet is left alone", PLACED == [], PLACED)

        # Due now: the worker should place exactly one call, linked to its origin.
        db.update_callback(pending["id"], status="pending")
        with db.conn() as cx:
            cx.execute("UPDATE callbacks SET resolved_at_utc=? WHERE id=?",
                       ((now - timedelta(minutes=1)).isoformat(timespec="seconds"),
                        pending["id"]))
        placed = asyncio.get_event_loop_policy().new_event_loop().run_until_complete(
            cb.tick(now))
        check("a due callback places exactly one call", len(placed) == 1
              and PLACED == ["+919876543210"], (placed, PLACED))
        check("the new call records what it is a callback of",
              db.get_call(placed[0])["is_callback_of"] == call5,
              db.get_call(placed[0]))
        row = [b for b in db.get_callbacks(call5) if b["id"] == pending["id"]][0]
        check("the callback is marked placed, so it cannot fire twice",
              row["status"] == "placed" and row["placed_call_id"] == placed[0], row)

        PLACED.clear()
        asyncio.get_event_loop_policy().new_event_loop().run_until_complete(cb.tick(now))
        check("a second pass does not re-dial it", PLACED == [], PLACED)

        # Misfire: the process was down when it came due. Ringing someone hours
        # late is worse than not ringing - and this is what stops a stale row in
        # a dev database from dialling on the next server start.
        db.add_callback(call5, (now - timedelta(hours=6)).isoformat(timespec="seconds"),
                        spoken_phrase="ages ago", resolution_rule="test")
        PLACED.clear()
        asyncio.get_event_loop_policy().new_event_loop().run_until_complete(cb.tick(now))
        check("a badly overdue callback is marked missed, not dialled",
              PLACED == [] and any(b["status"] == "missed" for b in db.get_callbacks(call5)),
              [(b["status"], b["spoken_phrase"]) for b in db.get_callbacks(call5)])

        print("\nCALLBACK CONTEXT  (a callback is not a cold call)")
        ctx = cb.build_context(call4)
        check("context carries what they already told us",
              "custom-made t-shirts" in ctx and "300 designs" in ctx, ctx)
        check("and forbids re-asking it", "Do NOT ask any of the above again" in ctx)
        check("opening line references the last conversation",
              "again" in (cb.opening_line(call4) or ""), cb.opening_line(call4))
        check("no context when nothing was extracted", cb.build_context(call3) == "",
              cb.build_context(call3))
        check("and then no opening override, so the normal greeting stands",
              cb.opening_line(call3) is None)

        # The context has to actually reach Vapi, not just be computed.
        PLACED.clear()
        OVERRIDES.clear()
        db.add_callback(call4, (datetime.now(_tzone.utc) - timedelta(minutes=1))
                        .isoformat(timespec="seconds"), spoken_phrase="tomorrow")
        asyncio.get_event_loop_policy().new_event_loop().run_until_complete(
            cb.tick(datetime.now(_tzone.utc)))
        ov = OVERRIDES[-1] if OVERRIDES else {}
        check("callback_context is sent to the provider",
              "t-shirts" in ov.get("variableValues", {}).get("callback_context", ""), ov)
        check("and the first message is overridden",
              "again" in ov.get("firstMessage", ""), ov)

        print("\nRECONCILIATION  (the webhook that never arrived)")
        from app import reconcile
        # A live call must NOT be swept mid-conversation.
        PLACED.clear()
        call6 = client.post("/calls").json()["call_id"]
        # The provider id comes from the fake dialler's counter, which has moved
        # on since call1 - read it back rather than guessing "prov-call-6".
        prov6 = db.get_call(call6)["provider_call_id"]
        webhook(client, {"type": "status-update", "status": "in-progress",
                         "call": {"id": prov6}})
        now = datetime.now(_tzone.utc)
        swept = asyncio.get_event_loop_policy().new_event_loop().run_until_complete(
            reconcile.sweep(now))
        check("a call that is still talking is left alone", call6 not in swept, swept)

        # Now age it past the stale window, with the provider reporting ended.
        VAPI_CALLS[prov6] = {
            "status": "ended", "endedReason": "customer-ended-call",
            "artifact": {"messages": [
                {"role": "user", "message": "We sell sarees."},
                {"role": "bot", "message": "How many designs?"}]}}
        swept = asyncio.get_event_loop_policy().new_event_loop().run_until_complete(
            reconcile.sweep(now + timedelta(minutes=10)))
        check("a call whose webhook was lost gets reconciled", call6 in swept, swept)
        call = db.get_call(call6)
        check("reconciled call is marked ended", call["status"] == "ended", call["status"])
        check("its transcript is backfilled from the provider",
              any("sarees" in t["text"] for t in db.get_turns(call6)),
              [t["text"] for t in db.get_turns(call6)])
        check("and the post-call follow-up finally fires",
              any(a["type"] == "whatsapp_followup" for a in db.get_actions(call6)),
              db.get_actions(call6))

        again = asyncio.get_event_loop_policy().new_event_loop().run_until_complete(
            reconcile.sweep(now + timedelta(minutes=20)))
        check("an already-finalized call is not swept twice", call6 not in again, again)
        check("and still only one follow-up exists",
              sum(1 for a in db.get_actions(call6)
                  if a["type"] == "whatsapp_followup") == 1, db.get_actions(call6))

        print("\nCALLBACK CLAIM  (cannot double-fire)")
        cb = db.add_callback(call_id, "2020-01-01T00:00:00+00:00", "tomorrow morning", "morning->10:00")
        first = db.claim_due_callback()
        second = db.claim_due_callback()
        check("due callback claimed once", first is not None and first["id"] == cb)
        check("second claim gets nothing", second is None)

    print("\n" + "=" * 46)
    print(f"{PASS} passed, {FAIL} failed")
    return 1 if FAIL else 0


if __name__ == "__main__":
    sys.exit(main())
