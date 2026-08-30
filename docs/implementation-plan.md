# Implementation Plan

Companion to [`requirements-analysis.md`](requirements-analysis.md) and [`system-design.md`](system-design.md).

**Governing principle:** the assignment says twice that a working call this week beats a perfect one next month, and that honest partial work is accepted. So the plan is ordered so that **the system is submittable at the end of every phase from Phase 5 onward** — each later phase adds points to an already-shippable product rather than being required to make it work at all.

**Second principle:** external clocks start first. WhatsApp template approval and any telephony KYC have lead times we do not control. They are kicked off in Phase 0 hour one, before a line of product code.

---

## Dependency map

```
P0 Spikes ───────────────┬──► P1 Skeleton ──► P2 Conversation ──► P3 Understanding ──► P4 Classification
 (telephony, te bake-off) │                          │                    │                    │
 (WhatsApp onboarding) ───┤                          │                    └────────┬───────────┘
        │                 │                          │                             ▼
        │                 │                          │                    P5 Mid-call action  ◄── SUBMITTABLE
        │                 │                          │                             │
        │                 │                          └──► P6 Callback scheduling ◄──┘
        │                 │                                        │
        └─────────────────┴──────────────────────► P7 Follow-up + media
                                                             │
                                                   P8 Failure handling + observability
                                                             │
                                                   P9 Rehearsal (adversarial)
                                                             │
                                                   P10 Artifacts + the live call
```

**Hard blockers:** P1 needs a chosen voice vendor from P0. P5 and P7 need WhatsApp sending to work at all. P4 needs P3's extraction. Everything needs P1's public URL.

**Parallelisable:** the architecture diagram, the resume, the Cold-lead brochure, and the classification eval set need no code and can be produced any time — do them during P0 waiting periods.

---

## Phase 0 — De-risk the externals

> **Revised by [`audit.md`](audit.md).** P0.0 is new (Finding A); P0.2 was measuring the wrong quantity (Finding B) and is split; a regulatory gate was missing entirely (Finding C). Full gate definitions with pass bars and fallbacks are in [`cost-and-feasibility.md`](cost-and-feasibility.md) Part 1.

**Why first:** three things can sink this project and none of them are code we write. Find out now, while there is still time to switch, rather than in Phase 7.

### P0.0 — Provider-composability inventory (new; free; runs before everything else)
Desk research only. For each candidate orchestrator, list which STT and TTS providers it supports **natively** for `te-IN`. Without this, the bake-off in P0.3 can select a winner we cannot actually use, and the "just swap in the best provider" premise of the design collapses.
- **Cost:** $0. **Time:** ~45 min.
- **DoD:** a written table of natively-supported `te-IN` options per orchestrator. If fewer than two exist for either STT or TTS, escalate to the R5 speech-to-speech fallback before spending anything.

### P0.1 — Start the external clocks (hour one, before anything else)
- Create the Meta Business account, add and verify the WhatsApp sender number, submit all three message templates (`mid_call_hot`, `post_call_context`, `resume_delivery`).
- Start Indian-CPaaS KYC in parallel as telephony insurance, in case the international route disappoints.
- **DoD:** templates submitted with timestamps recorded; KYC application in flight.

### P0.2a — Telephony *termination* spike
- Place real outbound calls to **two +91 mobiles we own** through each candidate route, playing a fixed TTS sentence.
- Measure: connect rate over 10 attempts, audio quality, one-way delay, whether the call is silently filtered.
- **DoD:** a route with ≥8/10 connects and clean audio (*bar is ours, not the evaluator's*), recorded with its numbers. If no route clears it, escalate — nothing downstream matters.

### P0.2b — *Answerability* spike (the thing that actually gates the 25-point row)
P0.2a proves the call arrives at a phone we are holding and expecting it on. That is not the question. The question is whether a stranger picks up an unknown, probably non-Indian number.
- Ask two people **not expecting a call** what caller ID appeared and whether they would have answered it cold. Piggybacks on P0.2a's calls; marginal cost zero.
- **Adopt regardless of outcome:** send the WhatsApp *first*, naming the exact number that will call. This converts an unknown number into an expected one and is free. It is now a design requirement.
- **DoD:** caller-ID presentation recorded; the announce-the-number step written into the submission sequence.

### P0.2c — Indian regulatory routing (new)
Indian CPaaS providers — the route that best fixes P0.2b — scrub promotional traffic against DND and require sender registration, and an automated outbound sales call is promotional on its face. Ask two Indian providers directly, in pre-sales, **before** starting KYC.
- **Cost:** $0. **Time:** 20 min to send, 1–3 days for answers — hence day one.
- **DoD:** a clear yes/no with registration path and lead time, or a decision to stay international and rely on P0.2b's mitigation.

### P0.3 — Telugu bake-off (decides the 10-point language row)
> **Constrained by P0.0:** the field is limited to providers the chosen orchestrator natively supports, unless we have explicitly costed a custom-provider integration *and* re-measured latency with the extra hop included.
>
> **Unstaffed dependency:** this phase requires a native Telugu speaker to judge naturalness, and we have not confirmed access to one. **Resolve that before starting, or the 10-point row has no acceptance test.**

- Record ~30 utterances per language **over a real phone call** (8 kHz telephony audio, not a clean laptop mic — studio-quality samples flatter every vendor and will mislead the decision): 30 Telugu, 30 Hindi, 30 English, plus 15 deliberately code-mixed ("Budget ante around one lakh anukuntunna").
- Run each candidate STT over them; compute WER and streaming latency; note whether per-utterance language ID is available.
- Synthesise the same sentence set through each candidate TTS; get a native Telugu speaker to rate naturalness 1–5; measure TTFB; check behaviour on a mixed sentence.
- **DoD:** STT and TTS chosen on a recorded score table, not a preference. Table pasted into `system-design.md` §4.3/§4.4.

### P0.4 — Voice orchestrator spike
- One throwaway assistant on the chosen platform: dials, greets, listens, replies, **and calls one dummy server-side tool** to prove the mid-call mechanism works end to end.
- **Verify the tool can be non-blocking.** A synchronous tool call stalls the agent's turn by the full round trip no matter how fast our handler is — which attacks the 3-second ceiling while trying to satisfy the mid-call row. Confirm the agent keeps talking while the tool runs.
- Verify barge-in actually interrupts and measure end-of-speech → first-audio latency.
- **DoD:** a real call where we interrupt the bot mid-sentence and it stops; a tool call observed hitting our endpoint *without an audible pause*; p50 turn latency recorded.

### P0.5 — Mid-call WhatsApp delivery check (cheap, high-value, easy to overlook)
Once P0.1's templates approve: while on a live call to our own handset, send a template message to that same handset. Repeat on a second handset, ideally a different carrier.
This tests something no amount of application code can fix — **the recipient's phone must have data during a voice call.** On VoLTE/5G it does; on a circuit-switched fallback it does not, and the message will not arrive until the call ends.
- **DoD:** message observed arriving *during* the call on both handsets, with the delay recorded. If it fails, fire as early in the call as possible, have the agent say aloud that it has been sent, and disclose it in the 200-word note.

**Phase 0 exit criteria:** composability table written (P0.0) · telephony route chosen with termination *and* answerability evidence · regulatory route question answered · STT + TTS chosen with evidence · non-blocking tool calls proven mid-call · WhatsApp templates submitted, and delivery-during-call verified. **Do not start Phase 1 until these hold.**

---

## Phase 1 — Skeleton and trigger surface

**Build:** FastAPI app · Postgres schema (§5 of the design doc) + migrations · `POST /calls` (destination hard-pinned to the one allowed number) · webhook ingress with correlation IDs · `GET /calls/{id}` · a single HTML page with a "Call me now" button and live status · structured JSON logging · deploy to the always-on host with a stable HTTPS URL.

**Depends on:** P0.2, P0.4.

**Test:**
- Click the button on a phone, on mobile data, with nothing installed → our own number rings.
- Every provider webhook lands and is persisted verbatim in `events`.
- Restart the service mid-call → the app recovers and the `call` row is consistent.
- Page loads in under 2 s after 30 minutes idle (proves no cold start).

**DoD:** a public URL exists where anyone can press one button and a phone rings, and the whole call is recorded in the database. **This is the moment the project becomes real.**

---

## Phase 2 — The conversation (the 25-point row)

> **Sequencing correction from the audit.** Build and prove this phase **in English only** first, then return for Telugu/Hindi after Phase 5. The language row is 10 points but is the hardest and most externally-constrained work in the project; the original plan put all three languages ahead of classification and the mid-call action (30 points), which inverts the value order. Ship English to T2, then add languages.

**Build:** system prompt covering persona, the e-commerce pitch, the discovery order, turn-length caps, and the language policy (detect from the lead's first turn, mirror it, stay in it, accept code-switching) · female Indian voice configured · subtle room ambience (NFR-06) · barge-in tuned · silence and off-script recovery.

**Depends on:** P1, P0.3.

**Test:**
- Three calls, one per language, each held for 2+ minutes.
- One code-mixed call.
- Adversarial suite: interrupt mid-sentence · stay silent 5 s · "who is this?" · "are you a bot?" · "how much exactly?" · talk over the greeting · hang up abruptly.
- Latency measured from logs across all of them.

**DoD:** p50 turn latency < 1.2 s and p95 < 2.0 s · barge-in works on every attempt · a disinterested listener reads the transcript and says it sounds like a person · language is correctly locked in all three languages.

---

## Phase 3 — The understanding lane

**Build:** async per-turn structured extractor (budget, products, product_count, timeline, features, barrier, quotable phrases) with a strict Pydantic schema · slot tracker persisted and injected into each LLM turn · the prompt rule that a filled slot is never re-asked and a missing slot is always asked before closing.

**Depends on:** P2.

**Test:**
- Replay 5 recorded rehearsal transcripts through the extractor offline and check field-by-field against hand labels.
- Live: volunteer three slots unprompted in the opening sentence → assert the agent never asks for those and does ask for the other two.
- Assert extraction adds zero latency to the speech lane (compare turn latencies with the lane on and off).

**DoD:** all five slots extracted correctly on ≥4 of 5 rehearsal transcripts · no re-asking observed · no measurable latency impact.

---

## Phase 4 — Classification engine (15 points)

**Build:** async classifier over the running transcript producing `label` / `confidence` / `barrier` / `evidence_quote`, append-only into `classifications` · few-shot anchored on the four phrases the PDF publishes · rules overlay forcing at least Hot on any explicit request for details, pricing, or a start date (per OQ-04) · re-runs on every meaningful turn.

**Depends on:** P3.

**Test:** this is the phase with the most offline testing, because it is the phase most likely to be wrong.
- **Labelled eval set of 40+ indirect utterances** across Telugu / Hindi / English, built to include the four published phrases and their Telugu and Hindi equivalents.
- Target: **100% on the four published phrases**, ≥85% overall, and the Warm barrier correctly identified on ≥80% of Warm cases.
- Live: play a scripted Warm lead and confirm the barrier is captured verbatim.
- Confirm the classification correctly *changes* mid-call when the lead's position shifts.

**DoD:** eval thresholds met and the results table committed to the repo · classification visible with its evidence quote on the call page.

---

## Phase 5 — Mid-call action (15 points) — **first submittable state**

**Build:** action bus (idempotency keys, retries, ledger) · WhatsApp sender against the approved templates · Path A `send_details_now` tool that acknowledges in <300 ms and enqueues · Path B watchdog firing on Hot if Path A has not · the LLM's verbal acknowledgement ("just sent it to your WhatsApp") · full instrumentation of `intent_detected_at` / `whatsapp_sent_at` / `whatsapp_delivered_at` / `call_ended_at`.

**Depends on:** P4, and P0.1 templates being **approved** (this is the phase that can be blocked by something outside our control — if approval has not landed, activate the BSP fallback from design §4.10).

**Test:**
- Rehearsal call: say "send me the details", keep talking for 60 more seconds, confirm the phone buzzes **while still on the call**.
- Assert from the DB that `whatsapp_delivered_at < call_ended_at` on every rehearsal.
- Force Path A to fail; confirm Path B still fires exactly once.
- Fire both paths simultaneously; confirm exactly one message is sent.

**DoD:** WhatsApp delivered mid-call on 5 of 5 rehearsals · never double-sent · agent verbally acknowledges it · the timing proof is visible on the call page.

> **At the end of P5 the system satisfies the core of the assignment.** If everything stopped here, it would be worth submitting with an honest note.

---

## Phase 6 — Callback scheduling (10 points)

**Build:** time resolver (spoken phrase → `Asia/Kolkata` datetime) with stated conventions for vague phrasing — morning → 10:00, afternoon → 15:00, evening → 18:00, "next week" → next Monday 10:00 · `schedule_callback` tool that resolves synchronously and returns the human-readable result so the LLM can confirm it aloud · **a DB-polling worker** (`SELECT ... FOR UPDATE SKIP LOCKED`) that re-enters `POST /calls` — *not* APScheduler: an in-process scheduler on a shared job store can double-fire during a rolling deploy, which would call the evaluator twice (audit Finding E).

**Depends on:** P2 (tool plumbing), P1 (persistence).

**Test:**
- **Unit tests over 30+ phrasings** in all three languages with a frozen clock: "tomorrow morning", "call me Monday", "after 6", "sometime next week", "day after tomorrow evening", "రేపు ఉదయం", "कल सुबह", plus ambiguous cases.
- Live: say "call me back tomorrow morning" and hear the agent say the resolved date and time back.
- **End-to-end:** schedule a callback 5 minutes out and confirm our own phone actually rings.
- Restart the service between booking and firing → the callback still fires.

**DoD:** all unit tests green · one real callback observed firing after a restart · the resolved time is spoken aloud for confirmation on every booking.

---

## Phase 7 — Follow-up and media (10 points)

**Build:** message composer producing human-sounding copy from real extracted slots with at least one near-verbatim quote · the pre-send quality gate (≥3 extracted values, ≥1 quote, mobile number present, within template limits; regenerate once on failure) · media hosting for the architecture image, resume PDF, and Cold brochure · the send sequence (primary message with image + context + number, then the resume document) · Cold-lead brochure path.

**Depends on:** P3 (extraction), P5 (sender).

**Test:**
- Generate follow-ups from 5 different rehearsal transcripts and read them side by side — if any two could be swapped between leads, the composer has failed and gets rewritten.
- Verify on a real phone that the image renders, the PDF opens, and the number is tappable.
- Check the four Section-06 items against the PDF's own checklist, one by one.
- Force the quality gate to fail and confirm it regenerates rather than sending something generic.

**DoD:** every one of the four required elements verifiably present and rendering on a real handset · the copy quotes the lead · no two follow-ups are interchangeable.

---

## Phase 8 — Failure handling and observability (5 points, and the reason the first call works)

**Build:** every row of the failure table in design §7 · reconciliation sweeper · answer-machine handling and retry policy · the per-call timeline view showing every turn, extraction, classification transition, and action with timestamps.

**Depends on:** P5, P6, P7.

**Test — deliberate failure injection:**
- Kill the WhatsApp API mid-call (bad token) → retries, then SMS fallback, logged.
- Kill the LLM (bad key) → filler line, retry, graceful close; never dead air.
- Hang up abruptly at 10 seconds → the follow-up is still composed and sent from partial context.
- Drop a `call.ended` webhook → the sweeper sends the follow-up.
- Restart mid-call → state is consistent afterwards.
- Point at a number that does not answer → retry policy behaves and stops.

**DoD:** every injected failure produces a graceful, logged, correct outcome · the timeline view is good enough to debug a call from alone.

---

## Phase 9 — Rehearsal

No new features. This phase exists because "it works on the first attempt, live, without you babysitting it" is on the impress-us list, and the only way to earn that is to have already done it several times.

- **Five full end-to-end rehearsals** on numbers we own, one per persona: Hot / Warm-budget / Warm-decision-maker / Cold / hostile-and-interrupting.
- One rehearsal per language, plus one code-mixed.
- One rehearsal conducted by someone else entirely, with no coaching, to catch what familiarity hides.
- Score each rehearsal against the actual scorecard, honestly, row by row. Fix the lowest-scoring row and repeat.

**DoD:** three consecutive clean runs with no intervention · self-scored ≥75/100 · every open bug either fixed or written into the note.

---

## Phase 10 — Artifacts and the live call

**Build (mostly not code):**
- One-page architecture diagram, image or PDF, showing the flow from call to action. The PDF says hand-drawn on paper is fine and that they want to see how we think — a clear hand-drawn or simply-drawn diagram is fully compliant and should not become a project of its own (O-06).
- The note, **under 200 words**: what works, what does not, what we would build next. Honest. The design doc's §9 limitations feed this directly.
- Resume PDF, mobile number, repository link (secrets scrubbed, `.env.example` present, README with the live URL).
- Final check against the send / do-not-send lists in requirements §13 — including confirming we are sending no deck, no plan, no estimate, no video-instead-of-system, and nothing requiring installation.

**Then, and only then:** the live call to 8688664337, following the OQ-05 approach — submit the WhatsApp with the link first so the call is expected, then trigger it.

**DoD:** all six send-list items delivered · zero do-not-send items included · the call placed and observed working.

---

## Cut lines, if time runs short

The assignment explicitly accepts honest partial work. Drop in this order, and say so in the note:

1. Cold-lead brochure path (OQ-03 — invented requirement, lowest cost of omission).
2. Callback job *execution* — keep the resolution, the verbal confirmation, and the booking record, drop the automatic re-dial. Most of the 10 points survive.
3. SMS fallback for WhatsApp failure.
4. Two of the three languages in *rehearsal* — never in capability. Ship all three; rehearse the one the evaluator is most likely to use.
5. The transcript timeline UI — keep the logs.

**Never cut:** the call connecting, barge-in, classification, the mid-call WhatsApp, or the four Section-06 elements. Those are 65 of the 100 points.

---

## Testing strategy summary

| Layer | How | When |
|-------|-----|------|
| Time resolver | Unit tests, frozen clock, 30+ phrasings, 3 languages | P6, on every change |
| Classification | Labelled eval set, 40+ utterances, thresholds enforced | P4, re-run before submission |
| Extraction | Replay recorded transcripts against hand labels | P3 |
| Composer | Cross-transcript interchangeability check (5 transcripts) | P7 |
| Conversation | Adversarial call suite (10 scenarios) | P2, repeated at P9 |
| Actions | Timestamp assertions (`delivered < ended`), idempotency tests | P5 |
| Failure | Deliberate injection, one per row of the failure table | P8 |
| End-to-end | Full rehearsals scored against the real scorecard | P9 |

**Testing rule that matters most:** the evaluator's number is not a test environment. Every one of the above runs against numbers we own. The live call happens once, after three consecutive clean rehearsals.
