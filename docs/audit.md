# Planning Audit

A critical review of [`requirements-analysis.md`](requirements-analysis.md), [`system-design.md`](system-design.md) and [`implementation-plan.md`](implementation-plan.md), treating the PDF as authoritative and those documents as a proposal.

**Headline result:** the requirement extraction holds up. The architecture holds up in shape but has **one severe internal contradiction** (§2 Finding A) and **two severe risks that were mis-ranked** (Findings B and C). Roughly 30 numeric thresholds in the planning docs are mine, not the evaluator's, and several vendor capabilities were stated as fact when they are unverified.

---

## 0. What the assignment actually quantifies

Before auditing anything, here is the complete set of numbers the PDF states. Everything numeric outside this list originated with me.

| Number | Where | Meaning |
|---|---|---|
| 8688664337 | throughout | the number to call and send to |
| 25 / 10 / 10 / 15 / 15 / 10 / 10 / 5 = 100 | p4 scorecard | point allocation |
| 60 | p4 | "Anything at 60 or above gets a call back" |
| **three seconds** | p3 | "If the reply takes three seconds, the conversation is dead" |
| 200 words | p4 | maximum length of the note |
| four | p4 | required elements in the WhatsApp message |
| eight | p2 | steps in the flow |
| one page | p4 | architecture diagram |
| Rs 30,000 | p1/p5 | stipend |

**Notably absent from the PDF:** any target latency other than the 3-second failure point, any accuracy threshold, any connect-rate expectation, any calling-hours window, any retry policy, any definition of "morning", any test-set size, and any statement about what technology can or cannot do.

---

## 1. Requirement vs assumption audit

Legend: **EXP** explicit requirement · **IMP** implied requirement · **ASM** our interpretation · **REC** our engineering choice · **EXT** unverified external dependency.

### 1.1 Functional requirements

| Claim in our docs | Class | Note |
|---|---|---|
| Autonomously dial +91 8688664337, no human on the line (FR-01) | **EXP** | p2 R1, verbatim |
| Speak Telugu / Hindi / English, stay in the answered language (FR-03) | **EXP** | p2 R2, verbatim |
| Handle code-switched sentences (FR-04) | **EXP** | p3 hard parts + scorecard "including mixed sentences" |
| Pitch e-commerce website development conversationally (FR-05) | **EXP** | p2 R3 |
| Discovery on budget / products / count / timeline / features (FR-06) | **EXP** | p2 R4 lists all five |
| Parse vague answers (FR-07), classify Hot/Warm/Cold (FR-08) | **EXP** | p2 R5 |
| Hot → WhatsApp before call ends, intent-triggered (FR-09) | **EXP** | p2 R6 + scorecard |
| Warm → capture barrier, schedule callback (FR-10) | **EXP** | p3 WARM card |
| Cold → log, send brochure, move on (FR-11) | **EXP** | p3 COLD card |
| Spoken time → booked callback incl. vague phrasing (FR-12) | **EXP** | p2 R7 + scorecard |
| Follow-up references what they actually said (FR-13) | **EXP** | p2 R8 |
| Post-call WhatsApp with the four elements (FR-14) | **EXP** | p4 §06 |
| Resume sent, auto-attach "better" (FR-15) | **EXP** | p4 — note "better", not required |
| Survives interruption / two-way conversation (FR-16) | **EXP** | scorecard 25-pt row + p3 |
| Prototype live, callable on demand, nothing to install (FR-02) | **EXP** | p4 send list + p5 do-not-send list |
| **A hosted web page with a "Call me now" button is how FR-02 is satisfied** | **ASM** | The PDF requires "live, on demand" and forbids installs. A URL is *a* solution, not *the* stated solution. A pre-agreed WhatsApp keyword trigger, or simply placing the call ourselves, would also satisfy it. **See Finding G.** |
| "Lead discovery" means in-call questioning, not lead sourcing | **ASM** | Very high confidence (one lead, number printed on the cover), but still our reading. |
| Cold-lead "brochure" is a one-page PDF we create | **ASM** | The PDF names a brochure and never defines it. Entirely invented artifact. |
| The four elements may span a primary message + a resume message | **ASM** | PDF says "the message ... must contain all four". Singular. Our split is a workaround for a platform constraint (which is itself **EXT** — see §1.4). |
| Warm leads also get a mid-call WhatsApp (callback confirmation) | **ASM** | Invented as insurance. **See Finding H — this may actively harm the 15-pt row.** |
| Callbacks must actually execute a real re-dial | **ASM** | PDF says "books the callback itself". "Books" ≠ "executes". We chose the stronger reading. |
| Agent discloses it is an AI if asked; represents the candidate | **ASM** | PDF is silent on persona entirely. |
| Zero test calls to the evaluator's number | **ASM** | Pure self-imposed discipline. Defensible, but ours. |

### 1.2 Non-functional targets — **almost entirely ours**

| Claim | Class | Provenance |
|---|---|---|
| 3 seconds is fatal | **EXP** | p3, verbatim |
| **< 1.2 s p50 / < 2.0 s p95 turn latency** | **REC** | Mine. No basis in the PDF. Reasonable industry targets, but presented in the project rules and the design doc as if authoritative. |
| **Barge-in stops audio within ~200 ms** | **REC** | Mine. |
| **Tool-call handler acknowledges in < 300 ms** | **REC** | Mine — and **partly wrong**, see Finding D. |
| **Agent monologue capped at ~15 s** | **REC** | Mine. |
| **≥ 8/10 telephony connect rate** as the go/no-go bar | **REC** | Mine — and **measuring the wrong quantity**, see Finding B. |
| **≥ 85% overall / 100% on the four published phrases** classification accuracy | **REC** | Mine, and **self-graded on a set I write myself** — circular. See Finding I. |
| **≥ 80% barrier identification** on Warm cases | **REC** | Mine. |
| **40+ utterance eval set, 30+ time phrasings, ~30 utterances/language for the bake-off** | **REC** | Mine. Sizes chosen for feel, not for statistical power. At n=40, a 85% threshold has a confidence interval of roughly ±11 points — the eval can pass or fail on luck. |
| **Self-score ≥ 75/100 before submitting** | **REC** | Mine. |
| **Retry policy: 2 attempts, 10 min apart** | **REC** | Mine. |
| **Calling window 10:00–19:00 IST** | **ASM** | Mine. The PDF gives no window. |
| **Morning → 10:00, afternoon → 15:00, evening → 18:00, next week → Mon 10:00** | **ASM** | Mine. Entirely invented convention. Defensible *because we say it aloud for confirmation*, which is the actual mitigation. |
| **Reconciliation sweeper threshold of 2 minutes** | **REC** | Mine. |
| **Page must load in < 2 s after 30 min idle** | **REC** | Mine. |
| "40 of 100 points sit downstream of extraction + classification" | **REC** | The arithmetic (15+15+10) is right; "downstream" **overstates it**. The mid-call row also depends on WhatsApp delivery and the follow-up row on media rendering — neither is downstream of classification. It is an argument, not a fact, and the design doc presents it as a fact. |
| "65 of the 100 points" must never be cut | **REC** | Arithmetic correct (25+15+15+10). |

### 1.3 Architectural decisions

| Decision | Class | Note |
|---|---|---|
| Split speech lane from understanding lane | **REC** | Our core idea. Genuinely requirement-driven: it is the only clean way to satisfy "act mid call without blocking the conversation" (**EXP**) alongside the 3-second ceiling (**EXP**). Audit verdict: **keep**. |
| Two independent mid-call trigger paths (tool call + watchdog) | **REC** | Defensible redundancy on a 15-point row. Keep. |
| Vapi as managed orchestrator | **REC** + **EXT** | See §2. The "provider-agnostic, just swap in the Telugu winner" premise is **unverified and probably the weakest claim in the design** — Finding A. |
| Claude Haiku 4.5 speech lane / Sonnet 5 understanding lane | **REC** + **EXT** | Sound reasoning. But whether the orchestrator natively supports Anthropic — and at what added hop cost — is unverified. |
| FastAPI + Postgres | **REC** | Safe, reversible, low-stakes. Postgres is mildly over-specified (Finding F). |
| APScheduler with Postgres job store | **REC** | **Revise.** Finding E. |
| WhatsApp Cloud API official over unofficial libraries | **REC** | Ethically and professionally right. Schedule risk is real and was correctly flagged. Keep. |
| Paid always-on hosting | **REC** | Keep, but see Finding J on what "cost is not the filter" actually means. |

### 1.4 Vendor/platform capabilities asserted as fact — all **EXT**, none verified

These are the most dangerous items in the planning docs, because they read like statements of fact:

| Assertion in our docs | Reality |
|---|---|
| "Vapi ... provider-agnostic STT/TTS slots (so we can swap in whatever wins the Telugu bake-off)" | **EXT.** True only for its *native* provider list. Anything outside it needs a custom transcriber/voice integration. This claim underpins the entire Phase 0.3 plan. **Finding A.** |
| "It also supports a background-ambience setting" | **EXT.** Plausible, unverified. |
| Sarvam supports Telugu STT + single-speaker multilingual TTS | **EXT.** Plausible (Indic-native vendor) but unverified — *and* its availability inside the orchestrator is separately unverified. |
| Soniox is a viable Telugu candidate | **EXT.** The PDF recommends Soniox for *live transcription*; it never claims Telugu. I inferred Telugu candidacy. |
| ElevenLabs Telugu quality "is the open question" | Correctly hedged. Still **EXT**. |
| Deepgram Indic coverage "is the question" | Correctly hedged. **EXT**. |
| "A template variable cannot contain newlines, so the context is one flowing paragraph" | **EXT.** Asserted as a hard platform rule and used to justify a copy decision. If wrong, the copy design changes. |
| WhatsApp supports image header and document header messages | **EXT.** High confidence, still unverified for our account tier. |
| WhatsApp gives delivery receipts we can timestamp | **EXT.** And the whole "prove it landed mid-call" evidence plan rests on it. |
| Twilio can place outbound calls to +91 mobiles with India geo-permissions enabled | **EXT.** |
| Indian CPaaS gives better termination and Indian caller ID | **EXT** — and **partly contradicted** by a regulatory factor I omitted entirely. **Finding C.** |
| APScheduler Postgres job store survives restarts | Near-certain, but see Finding E for the failure mode I missed. |

---

## 2. Findings — what the audit actually caught

### Finding A — SEVERE: the orchestrator/provider composability gap
`system-design.md` §4.1 sells Vapi on being "provider-agnostic ... so we can swap in whatever wins the Telugu bake-off", then §4.3–4.4 nominate **Sarvam** as the strongest Telugu candidate. These two statements may be incompatible. If Sarvam is not in the orchestrator's native provider list, using it means a custom transcriber/voice websocket integration — which destroys the "it's just configuration" premise, adds a network hop to the latency budget, and is a materially different project.

**The plan as written can produce a bake-off winner we cannot use.** Phase 0.3 measures quality in isolation and never checks integrability.

**Fix:** insert a **P0.0 provider-inventory gate** before the bake-off. Enumerate what the candidate orchestrators natively support for `te-IN`. Then either constrain the bake-off to that list, or explicitly budget the custom-provider integration and re-test latency with the hop included.

### Finding B — SEVERE: we planned to measure the wrong telephony number
P0.2 measures **connect rate to our own handsets** — phones we are holding, expecting the call. That measures *termination*, which is necessary but not the thing that decides the 25-point row.

The thing that decides it is: **will the evaluator answer an unknown, probably non-Indian number?** An Indian recipient seeing a `+1` caller ID has a materially lower answer rate than one seeing a local number, and the plan relegated Indian DID provisioning to "insurance". It is not insurance; it is top-of-funnel for the largest scoring row.

**Fix:** (1) split the gate into *termination* (our phones) and *answerability* (caller-ID presentation, tested by calling a phone belonging to someone not expecting it); (2) promote the mitigation buried in OQ-05 — **send the WhatsApp first, stating the number that will call** — from a footnote to a design requirement, because it converts an unknown number into an expected one and is free.

### Finding C — SEVERE: Indian regulatory routing was omitted entirely
The planning docs never mention India's DND / commercial-communication regime. This matters in a specific and counterintuitive way: **Indian CPaaS providers — the very route that gives us good caller ID — enforce DND scrubbing and sender registration on promotional traffic.** An automated outbound sales call is promotional on its face. So the route that best solves Finding B may be the route most likely to refuse or scrub the call, while the international route that has the caller-ID problem is not subject to the same domestic registration.

This is a genuine tension the plan did not surface, and it can only be resolved experimentally.

**Fix:** treat it as its own gate (G3 in the feasibility doc). Ask each candidate Indian provider directly whether a single AI-voice outbound sales call to a possibly-DND-registered mobile is permitted on their route, *before* starting KYC.

### Finding D — MODERATE: "acknowledge in < 300 ms" solves the wrong problem
The design says tool handlers acknowledge fast and enqueue. That is right, but incomplete: a **synchronous** tool call still stalls the agent's turn by the full round trip, however fast the handler is. The correct mechanism is a **non-blocking / background tool** where the orchestrator supports one — the model fires it and keeps talking, with no round trip in the turn at all.

**Fix:** specify async tools as the primary mechanism and the <300 ms synchronous ack as the fallback. Verify async tool support in P0.4 — it is a direct input to the 15-point row.

### Finding E — MODERATE: APScheduler has a duplicate-fire hazard we never mentioned
If the host ever runs more than one instance (a rolling deploy briefly does), an in-process scheduler on a shared job store can double-fire — meaning **two callback calls to the evaluator**. That is a worse failure than not calling at all.

Also unaddressed: misfire handling if the process is down at fire time.

**Fix:** for a system with approximately one scheduled job, a **10-line DB-polling worker** with a `SELECT ... FOR UPDATE SKIP LOCKED` claim is simpler, fully understood, has no library semantics to learn, and cannot double-fire. **Revise the design away from APScheduler.** This is a case where the audit found we reached for a library out of habit.

### Finding F — MINOR: Postgres is mildly over-specified
Postgres is correct *if* the host has an ephemeral filesystem — which was the stated reason and is sound. But it should be recorded that **SQLite on a persistent volume** is entirely adequate for one lead and one scheduled job, and is simpler. The choice should be driven by whether the chosen host offers a volume, not by default preference. Also: managed Postgres free tiers auto-suspend, which adds first-query latency to a waking scheduled job.

### Finding G — MODERATE: the demo has a single point of failure that is a human
The whole trigger design assumes the evaluator clicks a button. If they do not click it — because they are busy, or expect the system to just call, or the link goes to spam — **nothing happens at all**, and every other point becomes unreachable.

`FR-01` in the PDF actually says the system "dials 8688664337 by itself." A button-triggered call satisfies "on demand" but arguably under-delivers on "by itself".

**Fix:** support both, and sequence them. Send the WhatsApp with the link *and* place the call ourselves shortly after, so the demo happens whether or not they click. The button remains for repeat/on-demand runs, which is what the send-list line actually asks for.

### Finding H — MODERATE: the Warm mid-call WhatsApp may undercut the row it protects
`OQ-04` decided Warm leads also get a mid-call WhatsApp as insurance. But the scorecard says the mid-call action must be **"triggered by intent, not by call end"**. If a message fires for every classification, an evaluator can reasonably read it as *not* intent-triggered — which is the exact failure the row is testing for.

**Fix:** keep the insurance but make the distinction visible and auditable: the Warm message must be a *different* message, tied explicitly to the callback commitment ("locked in Thursday 10am"), and the call page must show which classification triggered which action and when. If we cannot make the difference obvious, drop the Warm message and accept the risk.

### Finding I — MINOR: the classification eval is circular and underpowered
We write the eval set, we set the threshold, we grade ourselves. And at n≈40, the ±11-point confidence interval means the 85% bar can be passed or failed by luck.

**Fix:** have someone else write half the set without seeing the prompt; include deliberately adversarial and ambiguous cases; report per-class results rather than one aggregate; and treat the four PDF-published phrases as a separate must-pass gate rather than averaging them in.

### Finding J — MINOR but financially material: "cost is not the filter" was read too generously
The PDF says spend what you need and *"if you make it through and join us, we reimburse"*. **Reimbursement is conditional on being hired.** Every rupee is genuinely at personal risk until then. The planning docs recommended paid tiers a little blithely on the strength of that sentence.

**Fix:** spend where it buys score (call quality, answer rate, always-on hosting) and not where it buys comfort. This reframes the cost doc from "budget" to "at-risk spend".

### Finding K — corrections to specific claims
- The "40 of 100 points downstream of classification" claim is an argument stated as a fact; softened above.
- The project rules present "< 1.2 s p50" as fixed without marking it as ours. It should carry provenance.
- `implementation-plan.md` P0.3 says "get a native Telugu speaker to rate naturalness" — we have not confirmed we have access to one. That is an unstaffed dependency on the 10-point row.

---

## 3. Challenging the proposed stack

Each entry: why proposed · requirement served · major risk · cost · latency · integration complexity · simpler alternative · test before committing.

### Vapi (realtime voice orchestrator)
- **Why** Collapses barge-in, endpointing, and streaming STT→LLM→TTS into configuration; provides server-side tool calls and call webhooks.
- **Serves** The 25-pt conversation row; the mechanism for the 15-pt mid-call row; NFR-01/02.
- **Risk** **High.** Finding A (provider composability). Opaque debugging when a call goes wrong. Platform outage is unfixable by us. Vendor-managed endpointing may not tune well for Telugu speech rhythm.
- **Cost** Per-minute platform fee **on top of** underlying provider costs. `VERIFY`.
- **Latency** Good by design; adds one orchestration hop versus owning the media stream.
- **Integration** Low *if* native providers suffice; **high** if we need a custom transcriber/voice.
- **Simpler alternative** Retell (same class, same risks). **Twilio ConversationRelay** — worth naming, since it collapses telephony and the voice-AI loop into one vendor and removes a whole integration seam. Direct media streams: cheapest per minute, far more work.
- **Test first?** **Yes — mandatory.** P0.4, plus the new P0.0 inventory gate.

### Twilio (telephony)
- **Why** Mature, documented, BYO-able into an orchestrator.
- **Serves** FR-01.
- **Risk** **High.** India geo-permissions must be explicitly enabled; caller ID will present as non-Indian → Finding B answer-rate risk; Indian DID provisioning involves KYC and possibly an Indian entity.
- **Cost** Per-minute to India mobile; India termination is not among the cheap destinations. `VERIFY`.
- **Latency** Fine.
- **Integration** Low.
- **Simpler alternative** Vapi-native numbers (fewer moving parts); **Plivo** (India-founded, often better India routing/pricing); Exotel/Ozonetel/Knowlarity (true Indian caller ID, but KYC lead time and Finding C's DND exposure).
- **Test first?** **Yes — this is the single highest-risk gate in the project.**

### Soniox (STT)
- **Why** Named in the assignment for live transcription; the PDF explicitly ties it to the mid-call-WhatsApp use case.
- **Serves** FR-03/04.
- **Risk** **Telugu support is unverified** — the PDF recommends it but never claims Telugu. I promoted a general recommendation into a Telugu candidate without evidence. Orchestrator support also unverified.
- **Cost** `VERIFY`.
- **Latency** Streaming; expected fine.
- **Integration** Depends entirely on orchestrator support.
- **Simpler alternative** Google STT `te-IN` (mature, streaming, boring, likely to just work); Sarvam; Deepgram for hi/en only.
- **Test first?** **Yes** — it is a bake-off entrant, not a decision.

### Sarvam (STT + TTS)
- **Why** Indic-native; best a-priori fit for Telugu and code-mixed Indian speech; single-speaker multilingual TTS would keep the voice constant across a code-switched sentence.
- **Serves** The 10-pt language row; NFR-05/06.
- **Risk** **Highest integration risk in the stack.** Very likely *not* a native orchestrator provider (Finding A). Smaller vendor: less battle-tested at our latency budget, less certain uptime. All capability claims `VERIFY`.
- **Cost** Likely low and INR-denominated. `VERIFY`.
- **Latency** `VERIFY` — and if reached via a custom-provider hop, measure *with* the hop.
- **Integration** **High.**
- **Simpler alternative** Google or Azure `te-IN` — less natural, but natively supported nearly everywhere and trivially integrated. **If Sarvam's integration cost is real, Azure/Google is the rational trade: a few points of naturalness against days of work on a 10-point row.**
- **Test first?** **Yes — and test the integration path, not just the audio quality.** This is the correction Finding A demands.

### ElevenLabs (TTS)
- **Why** Best-in-class naturalness; very low latency on the Flash tier; natively supported almost everywhere.
- **Serves** NFR-05 ("sounds like a person"), NFR-06.
- **Risk** **Telugu coverage and quality unverified.** Strong English/Hindi is not evidence about Telugu.
- **Cost** Character-based; accumulates across many rehearsal calls, and rehearsals are where most of our TTS volume will be. `VERIFY`.
- **Latency** Excellent.
- **Integration** Low.
- **Simpler alternative** Azure `te-IN` neural voices — safe floor, cheap, natively supported.
- **Test first?** **Yes**, on Telugu specifically, and on a code-switched sentence.

### Claude models (Haiku 4.5 speech lane, Sonnet 5 understanding lane)
- **Why** Haiku for time-to-first-token and reliable tool-calling under a long behavioural prompt; Sonnet off the speech path where latency is free and 40 points of reasoning live.
- **Serves** FR-05/06 (pitch, discovery); the 15-pt classification row; the 10-pt follow-up row.
- **Risk** The real question is not general model quality but **classification from noisy, possibly transliterated Telugu STT output** — which is a different task from classifying clean English. Also: orchestrator support for Anthropic as the speech-lane provider is `VERIFY`; if absent, we route through a custom-LLM endpoint and add a hop.
- **Cost** Token-based. The understanding lane **multiplies** this — re-classifying on every turn with a growing transcript is quadratic in turns if not debounced. This was not modelled in the original plan.
- **Latency** Haiku: good. Sonnet: off-path, irrelevant by design.
- **Integration** Low to medium.
- **Simpler alternative** Use the orchestrator's default/native model in the speech lane to remove a hop, and keep the strong model only in the async lane where the points actually are.
- **Test first?** **Yes** — specifically classification accuracy on *Telugu-derived transcripts*, not on English.

### FastAPI
- **Why** Async webhooks, Pydantic schemas, best-in-class Python AI SDK ecosystem.
- **Serves** NFR-03 (non-blocking side effects).
- **Risk** Negligible. The only real hazard is blocking the event loop with a synchronous SDK call inside an async handler — a discipline problem, not a technology problem.
- **Cost** Zero. **Latency** Negligible. **Integration** Trivial.
- **Simpler alternative** Node/Express is equally fine.
- **Test first?** **No.** Safe and reversible. Honest note: **this is the least consequential decision in the entire plan and deserves no further thought.**

### PostgreSQL
- **Why** Durable state across restarts, which the scheduler and follow-up both depend on.
- **Serves** I-03, I-06.
- **Risk** Low. Managed free tiers auto-suspend → cold first query, which matters when a scheduled job wakes.
- **Cost** Free tier likely sufficient. `VERIFY`.
- **Latency** Negligible if co-located.
- **Integration** Trivial.
- **Simpler alternative** **SQLite on a persistent volume** — genuinely adequate for one lead. See Finding F: pick based on whether the host offers a volume.
- **Test first?** **No.**

### APScheduler
- **Why** Durable scheduling without extra infrastructure.
- **Serves** FR-12 (10 pts).
- **Risk** **Duplicate firing across instances (Finding E) — which would call the evaluator twice.** Plus misfire semantics to learn.
- **Cost** Zero. **Latency** N/A. **Integration** Low.
- **Simpler alternative** A DB-polling worker with `FOR UPDATE SKIP LOCKED`. Fewer lines than the APScheduler configuration, no library semantics, impossible to double-fire.
- **Test first?** Cheap to test (restart + concurrency), but **the audit recommends replacing it rather than testing it.**

### WhatsApp Cloud API
- **Why** Official; supports image and document headers; provides delivery receipts that are our *evidence* for the mid-call row.
- **Serves** FR-09 (15 pts) + FR-14/15 (10 pts) — **25 points combined, the second-largest cluster after the call itself.**
- **Risk** **Highest-uncertainty item after telephony.** Business verification, template approval latency, template *rejection*, opt-in policy, and category-based throttling all sit outside our control. And the mid-call timing has a physical dependency nobody mentioned — see gate G6 in the feasibility doc.
- **Cost** Per-conversation, India rates, category-dependent. `VERIFY`.
- **Latency** Usually seconds; **not guaranteed and not ours to control**, which is uncomfortable for a row scored on timing.
- **Integration** The API is easy. **The onboarding is the work.**
- **Simpler alternative** An Indian BSP (WAPI — named in the PDF — AiSensy, Gupshup, Interakt): same underlying API, faster template handholding, monthly subscription. Twilio WhatsApp: same template gate, no advantage. Unofficial libraries: instant and free-form, ToS-violating, indefensible on the callback.
- **Test first?** **Yes, and first of everything**, because its clock is the longest and entirely external.

---

## 4. Architecture reconsideration

### Do I still recommend the same architecture?

**Yes on the core, with five specific revisions.** The two-lane split (speech loop separated from the understanding loop) survives the audit unchanged, because it is derived from two explicit requirements in tension — "act mid call without blocking the conversation" and the three-second ceiling — rather than from preference. Nothing in the audit weakened it.

What did not survive is the *confidence* around the periphery: three vendor-composability and regulatory assumptions were load-bearing and unverified.

### Revisions

**R1 — Add a provider-inventory gate before the bake-off (Finding A).**
New **P0.0**: enumerate each candidate orchestrator's *native* `te-IN` STT/TTS providers. The bake-off field is then either constrained to that list, or a custom-provider integration is explicitly costed and latency-tested with the hop included. Without this, P0.3 can produce an unusable winner.

**R2 — Split the telephony gate into termination and answerability (Finding B), and add the regulatory gate (Finding C).**
Measure connect quality on our own phones *and* answer behaviour on a phone that is not expecting the call. Promote "WhatsApp first, announcing the calling number" to a design requirement. Ask Indian providers about DND/promotional-route policy before starting KYC.

**R3 — Replace APScheduler with a DB-polling worker (Finding E).**
Roughly the same number of lines, no double-fire hazard, no library semantics. For one scheduled job, the library was habit rather than judgement.

**R4 — Specify non-blocking tool calls as the primary mid-call mechanism (Finding D).**
Async tool where the orchestrator supports it; the fast synchronous ack becomes the documented fallback. Verify in P0.4.

**R5 — Add a whole-lane fallback rather than forcing a custom provider.**
If native-provider Telugu is inadequate, the better move is to substitute the *entire* speech lane with a speech-to-speech model (which handles code-switching natively and may render Telugu better end-to-end) than to bolt a custom Telugu provider into a cascaded pipeline. We would lose per-turn transcript fidelity, so the understanding lane would consume the orchestrator's transcript instead. **This is a pre-planned Plan B, not a preference** — chosen only if P0.0/P0.3 say so.

**Minor:** soften Postgres to "Postgres if the host has ephemeral disk; SQLite on a volume is acceptable" (Finding F); add provenance markers to the invented thresholds in the project rules and the design doc (Finding K); staff or drop the native-Telugu-speaker dependency in P0.3.

### What I would *not* change
- The two-lane split.
- Dual trigger paths for the mid-call action.
- Official WhatsApp over unofficial libraries — the schedule risk is real and was correctly identified, and the alternative is indefensible in the conversation the 5-point row is literally about.
- Building in scorecard order with a submittable state from P5 onward.
- FastAPI, and the general instinct to keep the backend boring.
