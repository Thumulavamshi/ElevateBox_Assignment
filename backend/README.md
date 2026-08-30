# Backend — local skeleton

The server everything hangs off. Runs locally behind a tunnel today; `docs/deployment.md`
covers putting it on Render. The Vapi CLI in `agent/` places calls either way.

**Built:** webhook ingress, persistence, trigger endpoint, action bus, WhatsApp sending,
Hot/Warm/Cold classification with a labelled evaluation set, and slot extraction with a
quote-integrity eval over the real call transcripts.
**Not built:** the cold-lead brochure, and `callback_confirm` fires on booking rather than
on every classification (audit Finding H).

## Run it

```bash
python -m uvicorn app.main:app --app-dir backend --reload --port 8000
```

Then <http://127.0.0.1:8000/health> and <http://127.0.0.1:8000/docs>.

Credentials come from `experiments/voice-feasibility/.env` automatically — nothing to re-enter.
Override anything in `backend/.env` if you want them separate.

## Test it — no network, no phone calls, no spend

```bash
python backend/smoke_test.py
```

123 assertions replaying a realistic Vapi webhook sequence: trigger safety, transcript handling,
tool calls, idempotency, end-of-call reconciliation, webhook auth, IST conversion, callback
claiming, and classification firing the mid-call action end to end. It caught two real bugs (see
*Task lifetime* below).

## Routes

| Route | Purpose |
|---|---|
| `GET /health` | config, whether calls can be placed, and which actions are wired vs stubbed |
| `POST /calls` | place a call — **takes no parameters** |
| `GET /calls` | recent calls |
| `GET /calls/{id}` | call + turns + slots + coverage + classification history + actions |
| `GET /calls/{id}/transcript` | flat transcript |
| `POST /vapi/webhook` | single Vapi ingress |

## Three decisions worth defending

**The trigger endpoint takes no phone number.** `POST /calls` accepts no body and no query
parameter; the destination comes only from `ALLOWED_DESTINATION` (falling back to `TEST_NUMBER`).
This endpoint must be unusable to dial anything else — the strongest way to
guarantee that is to give it no parameter to abuse. `/health` shows the configured number and
flags whether it is the evaluator's, so a misconfiguration is visible *before* a call.

**The webhook acknowledges fast and works in the background.** Vapi is driving a live phone call.
Everything except `tool-calls` is persisted and handed to a background task. `tool-calls` must
answer synchronously, so it claims an action and returns a speakable confirmation string without
waiting for anything to send — that is the "fire an action mid-call without blocking the
conversation" requirement, in one function.

**Idempotency lives in the database, not in code.** `actions.idempotency_key` is UNIQUE. The
mid-call WhatsApp has two independent trigger paths — the LLM calling a tool, and an async
watchdog for when it does not — and both route through `dispatch()` with the same key. Whichever
loses the race becomes a no-op. Two WhatsApps would read worse than one.

The same pattern guards callbacks: `claim_due_callback()` does a guarded `pending -> claimed`
update, so two workers cannot both place the same call. Double-dialling the evaluator would be
worse than not calling at all.

## Task lifetime — the bug the smoke test caught

The first version used `asyncio.create_task()` for fire-and-forget sends. asyncio holds only a
**weak** reference to such a task, so it can be garbage-collected mid-flight and disappear with no
error. On the mid-call row that failure looks identical to "the WhatsApp never arrived."

Fixed two ways: inside a request, dispatch uses FastAPI's `BackgroundTasks`, which the framework
guarantees to run; outside one, tasks are kept in a module-level set until they complete.

## Data model

`calls · turns · events · slots · classifications · actions · callbacks`

SQLite via stdlib `sqlite3` — no ORM, no migration tool. The schema is small enough that the SQL
is easier to read than models would be, and it is written to stay Postgres-portable: plain SQL,
ISO-8601 UTC text timestamps, no SQLite-only types. Moving to Postgres means swapping the
connection helper and the placeholder style.

`classifications` is append-only on purpose — how the read of a lead evolved during a call is
worth being able to show, and it makes the mid-call trigger auditable after the fact.

Every timestamp is stored UTC. `db.to_ist()` is the only way a time becomes Asia/Kolkata, for
anything spoken or displayed.

## Wiring it to Vapi

`agent/agent.py deploy` does all of this from `SERVER_URL`:

1. Sets the assistant's `serverUrl` to `https://<host>/vapi/webhook`
2. Applies `VAPI_WEBHOOK_SECRET` as the `x-vapi-secret` header
3. Creates both tools as their own `/tool` resources and attaches them by id

`send_details_now` is **async** (audit R4) — measured: the watchdog had already sent the message
two minutes before the model called the tool, so waiting bought nothing and cost an audible pause.
`schedule_callback` stays synchronous because its return value is the time the agent says aloud.

## Classification (the 15-point row)

Two layers, in `app/classifier.py`:

**A model read** of the running transcript via the official Anthropic SDK
(`messages.parse` with a Pydantic schema), returning label, confidence, barrier, a verbatim
evidence quote, and one line of reasoning. The system prompt uses the assignment's own
Hot/Warm/Cold definitions and its four published example phrases as anchors, and tells the model
the transcript will be noisy so it reads through transcription errors instead of mistaking them
for hesitation.

**A narrow deterministic overlay.** OQ-04 decided to bias the boundary toward firing: an explicit
request to be *sent* something, or to know when work can *start*, is hot regardless of the model.
Sending a message we did not strictly need costs nothing; not sending one costs 15 points.

The overlay is deliberately narrow — it fires on 18% of the labelled set. It does **not** trigger
on a bare "how much is it", which is equally idle curiosity; judging that is the model's job. A
rule that fired on everything would destroy the signal the row is testing. It also reads only the
*lead's* lines (the agent offering to send something is not intent) and is suppressed entirely by
an explicit refusal.

Two useful consequences: the rules run with **no API key**, so the logic protecting the 15-point
row is regression-tested on every change; and when they fire, `understanding.classify()` skips the
model call entirely — cheaper, and **faster**, which matters because the mid-call action is scored
on timing.

### Measuring it

```bash
python backend/eval_classifier.py          # rules only - no key, no cost
python backend/eval_classifier.py --llm    # full pipeline (needs a key, costs money)
```

59 labelled cases in `eval/classification_cases.json`, written with realistic transcription noise
because that is what the classifier will actually see. Four come from the assignment itself and are
a **must-pass gate**, not an average. Six are adversarial: a hot phrase spoken by the agent, a
send-me phrase next to a refusal, enthusiasm masking a real barrier, a lead who has barely spoken.

Thresholds (100% on the assignment's phrases, 85% overall, 80% on barriers) are **ours**, not the
evaluator's. At n≈44 the interval is roughly ±11 points, so treat a near miss as noise and the
must-pass gate as the real signal.

**Rules pass: 59/59.** Model pass on `claude-haiku-4-5`: **55/57 = 96%** at the last full
run, **4/4** on the assignment's own phrases, barriers 19/21. Two cases were added after that
run, so the set is now 59 and the model figure is quoted against the 57 it was measured on.

### To run the model pass

```bash
pip install anthropic
```

Then set `ANTHROPIC_API_KEY`. `CLASSIFIER_MODEL` selects the model — **`claude-haiku-4-5`**
is what we run: 96% against Opus 5's 98% at one fifth the price, and both clear every threshold.
Without a key `understanding.classify()` logs a warning and returns `None` rather than failing the
call — a broken understanding lane must never take down a live conversation.

## Slot extraction

`understanding.extract_slots()` reads the five discovery slots off the running transcript, in
parallel with classification. Two rules shape it, both in `app/extraction.py`:

- **Nothing is invented.** A slot the lead never spoke about stays empty and the handlers fall
  back to honest vague phrasing. On the real 28 Aug call the lead never named a budget — they
  asked *us* for a range — and the extractor correctly leaves it blank rather than attributing
  Maya's own "seventy thousand to one and a half lakh" back to them.
- **Every quote is verified.** `attach_quote()` checks the model's quote back against the lead's
  own turns and refuses anything it cannot find, because a model told to copy verbatim will tidy
  the wording instead.

```bash
python backend/eval_extraction.py          # verifier self-check, no key, no cost
python backend/eval_extraction.py --llm    # real extractor over agent/transcripts/
```

Measured over the 7 real Soniox calls: **30 slots filled, 29 with a verified verbatim quote,
0 integrity violations**, median 8.0 s per pass (off the speech path). The one slot with no
verifiable quote was also the one wrong value — so "no quote" doubles as a usable confidence
signal, not just a formatting outcome.

## Callback scheduling

`app/timeparse.py` resolves the spoken phrase; `app/callbacks.py` books it and later places it.

**The resolver is deterministic, not a model call.** It answers inside a *synchronous* tool call
while the agent is mid-sentence, so a four-second round trip there would be heard as dead air —
damaging the 25-point row to serve the 10-point one. Being deterministic also means "next Monday"
can be proven right against a frozen clock instead of hoped at.

```bash
python backend/eval_timeparse.py       # 57 phrasings, frozen clock, no key, no cost
python backend/eval_timeparse.py -v    # also prints what the agent says back
```

**57/57**, of which **26 are vague** — the case the scorecard names — plus 5 that must *not*
resolve, so the agent asks again rather than inventing a time. English, Hindi and Telugu, in both
native script and romanisation.

The conventions (morning → 10:00, afternoon → 15:00, evening → 18:00, "next week" → Monday,
"after six" → 18:30) are **ours, not the evaluator's**. What makes them safe is not choosing well:
it is that the tool returns the resolved time and the agent says it back, so a wrong guess gets
corrected by the person on the phone.

The worker polls `callbacks` and claims rows with a guarded `pending -> claimed` UPDATE, so two
instances cannot both place the same call. A callback more than `CALLBACK_MAX_LATENESS_MINUTES`
(default 30) overdue is marked `missed` rather than dialled — waking up hours late and ringing out
of the blue is worse than not ringing, and it stops a stale dev row from calling someone on the
next `uvicorn` start.

## Next

1. Dispatch `whatsapp_resume` — the handler exists but nothing calls it, so the résumé never sends
2. Deploy, so Vapi reaches a stable URL instead of a tunnel
3. `callback_confirm` is deliberately still a stub — audit Finding H warns that a WhatsApp firing
   on every classification undercuts "triggered by intent". The spoken confirmation is what the
   row actually scores.
