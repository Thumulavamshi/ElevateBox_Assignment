# Requirements Analysis — ElevateBox SDE Intern Assignment

**Source of truth:** `requirements/ElevateBox_SDE_Intern_Assignment.pdf` (5 pages, ElevateScale Technologies Private Limited, brand ElevateBox).
This file is a derived analysis. The PDF is never to be modified.

> **Audited.** See [`audit.md`](audit.md) for which items below are the evaluator's requirements and which are our assumptions or engineering targets. **Every numeric threshold in this document other than the scorecard values, the 60 pass mark, "three seconds", and "200 words" is ours, not the assignment's.**

**Read status:** all 5 pages read in full, including the 8-step timeline diagram (p2), the Hot/Warm/Cold cards (p3), the reference-architecture diagram (p3), the scorecard table (p4), the "must contain" table (p4), and the two-column send / do-not-send lists (p4–p5). Two tables in the PDF extract with interleaved columns in plain text; row alignment was verified against per-word coordinates and page renders.

---

## 1. The assignment in one paragraph (as written)

> "I am a potential customer looking to build an e-commerce website. Build an AI voice system that calls me on 8688664337, speaks to me in Telugu, Hindi or English, sells me the service, works out how serious a buyer I am, and takes the next action while we are still on the call. Then sends me a WhatsApp with the context of what we discussed, your resume and your number."

**The outcome rule:** "If your system calls me and it works, I call you back. That is the entire selection process."

**Target number:** `8688664337` (India, +91). This is both the lead's number and the submission destination.

---

## 2. The canonical 8-step flow (p2 timeline diagram)

The PDF prints this as a numbered timeline captioned *"The eight things your system has to do, in the order it has to do them."* Verified by coordinate alignment of the step numbers to their labels:

| # | Step | Caption in diagram |
|---|------|--------------------|
| 1 | **Dial** | the system places the call |
| 2 | **Speak** | Telugu, Hindi or English |
| 3 | **Discover** | budget, products, timeline, features |
| 4 | **Understand** | parse what was actually said |
| 5 | **Classify** | Hot, Warm or Cold |
| 6 | **Act mid call** | WhatsApp fires while still talking |
| 7 | **Schedule** | call me back tomorrow morning, understood |
| 8 | **Follow up** | built from their own words |

Note the ordering implication: **Classify (5) precedes Act mid call (6)**, and **Schedule (7) precedes Follow up (8)**. Classification is a live, in-call function — not a post-call batch job.

---

## 3. Explicit functional requirements

### 3.1 Section 02 table — "What your system must do" (verbatim, row-aligned)

| # | Requirement | What we will check on the call |
|---|-------------|-------------------------------|
| 1 | Place the call | Your system dials 8688664337 by itself. No manual dialling, no you on the line. |
| 2 | Speak the language | Telugu, Hindi or English. Handle whichever one I answer in, and stay in it. |
| 3 | Sell the service | Pitch e-commerce website development like a person would, not like a recorded message. |
| 4 | Ask the right questions | Budget, what I sell, how many products, timeline, features I need. Ask them naturally, not as a form. |
| 5 | Understand the answers | Parse what I actually said, including when I am vague, and classify me as Hot, Warm or Cold. |
| 6 | Act during the call | If I show high buying intent, a WhatsApp message reaches me before the call ends. Mid call, not after. |
| 7 | Schedule from speech | If I say call me back tomorrow morning, your system understands it and books the callback itself. |
| 8 | Follow up smartly | The follow up references what I actually said, not a template with my name pasted in. |
| 9 | Send yourself, with context | After the call, a WhatsApp message carrying the full context of what we actually discussed, your resume, your mobile number, and an image showing how you built it. Detail in Section 06. |
| 10 | Work | If it works, I call you back. That is the whole selection process. |

### 3.2 Page 1 — "What it must do" (the same list, condensed)

01 Calls me on 8688664337, on its own · 02 Speaks Telugu, Hindi or English · 03 Sells e-commerce website development · 04 Asks budget, products, timeline, features · 05 Understands my answers · 06 Classifies me Hot, Warm or Cold · 07 Fires a WhatsApp mid call on high intent · 08 Books the callback when I name a time · 09 Follows up using what I actually said · 10 Sends your resume, number and build image

### 3.3 Normalized functional requirements

| ID | Requirement | Source |
|----|-------------|--------|
| FR-01 | System places an outbound voice call to +91 8688664337 autonomously, with no human dialling and no human on the line. | p1 #01, p2 R1 |
| FR-02 | The call must be triggerable **on demand** by the evaluator without installing anything. | p4 "The working prototype, live, that can call the number on demand" + p5 do-not-send "Anything that needs us to install something to see it work" |
| FR-03 | The agent converses in Telugu, Hindi, or English, adopting whichever language the lead answers in and **staying in it**. | p2 R2 |
| FR-04 | The agent handles **code-switched** sentences (Telugu + English mixed). | p3 "Code switching. Telugu and English in the same sentence is normal here." + scorecard "including mixed sentences" |
| FR-05 | The agent pitches **e-commerce website development** conversationally, not as a recorded message. | p2 R3 |
| FR-06 | The agent performs discovery on five slots: **budget, what they sell, how many products, timeline, features needed** — asked naturally, in a natural order, not as a form. | p2 R4, scorecard "Discovery quality" |
| FR-07 | The system parses what the lead actually said, including vague/indirect answers. | p2 R5 |
| FR-08 | The system classifies the lead as **Hot / Warm / Cold**, correctly, from **indirect** answers. | p2 R5, p3, scorecard "Intent classification" |
| FR-09 | **Hot →** a WhatsApp message reaches the lead **before the call ends**, triggered by intent, not by call end. | p2 R6, p3 HOT card, scorecard "Mid call action" |
| FR-10 | **Warm →** capture the barrier (budget / timing / someone else decides) and schedule the callback. | p3 WARM card |
| FR-11 | **Cold →** log it, send the brochure, move on. | p3 COLD card |
| FR-12 | The system converts spoken time expressions ("call me back tomorrow morning") into a **booked** callback, itself, including vague phrasing. | p2 R7, scorecard "Callback scheduling" |
| FR-13 | The follow-up references what the lead actually said — not a template with a name substituted. | p2 R8, scorecard |
| FR-14 | After the call, a WhatsApp message must contain all four of: (1) the context of the call, (2) proper human framing of that context, (3) the sender's mobile number, (4) an image of how it was built. | p4 Section 06 table |
| FR-15 | The resume goes with it; automatic attachment by the system is explicitly "better". | p4 |
| FR-16 | The agent must survive a **real two-way conversation** — interruption, silence, off-script input. | scorecard 25-pt row, p3 hard parts |

---

## 4. Non-functional requirements

| ID | Requirement | Source / target |
|----|-------------|-----------------|
| NFR-01 | **Latency.** "If the reply takes three seconds, the conversation is dead." | p3. Engineering target: end-of-speech → first audio out **< 1.2 s p50, < 2.0 s p95**. Hard ceiling 3 s. |
| NFR-02 | **Interruption / barge-in.** "People talk over the bot. Handle it." | p3. Agent audio must stop within ~200 ms of detected speech and the turn must re-plan. |
| NFR-03 | **Non-blocking side effects.** "Firing an action mid call without blocking the conversation." | p3. WhatsApp send, DB write, and scheduling must never stall the speech loop. |
| NFR-04 | **First-attempt reliability.** "It works on the first attempt, live, without you babysitting it." | p3 "What will impress us" |
| NFR-05 | **Human-sounding voice.** "The conversation sounds like a person, not a menu." | p3 |
| NFR-06 | **Naturalness hints (explicit, from the evaluator):** female voice lands better on outbound calls in this market; add a little background noise so it sounds like a room, not a studio — "gets hung up on far less often." | p3 Section 04 |
| NFR-07 | **Handles failure.** Part of the 5-pt Engineering judgement row: "Sensible architecture, handles failure, you can defend your choices." | p4 |
| NFR-08 | **Defensibility.** "You can explain every decision you made and what you would fix next." | p3/p4 |
| NFR-09 | **No install for the evaluator.** | p5 do-not-send |
| NFR-10 | **Cost is not a constraint.** "Spend what you need on APIs, voice minutes, WhatsApp, hosting and tools... Cost is not the filter here." Reimbursed on joining. | p5 |

---

## 5. What happens before, during, and after the call

### Before the call
- The prototype is deployed and reachable at a public URL (no install for the evaluator).
- A trigger exists — a button / endpoint — that starts the call to 8688664337 on demand.
- Agent persona, opening line, language policy, and discovery script are configured.
- WhatsApp sender is provisioned and message templates are approved.
- Media assets are hosted and reachable: architecture image, resume PDF, Cold-lead brochure.
- A lead record is created with the target number and any prior context.

### During the call
1. Outbound dial; detect human answer vs voicemail/no-answer.
2. Natural opening in a language-neutral / bilingual greeting.
3. Detect the lead's language from their first turn; lock to it; tolerate code-switching.
4. Pitch e-commerce website development conversationally.
5. Run discovery across the five slots, adaptively — skip what was volunteered, never re-ask.
6. Continuously extract structured facts from the live transcript.
7. Continuously classify Hot / Warm / Cold from the running transcript.
8. **On Hot:** fire WhatsApp immediately, asynchronously, and have the agent verbally acknowledge it so the lead notices it arrive while still talking.
9. **On Warm:** capture the barrier explicitly and drive to a callback.
10. **On any spoken time reference:** resolve to a concrete IST datetime, confirm it back verbally, book it.
11. Close the call naturally.

### After the call
1. Persist the final transcript, extracted slots, classification, and every action taken.
2. Compose the follow-up WhatsApp from the actual transcript, quoting specifics.
3. Send it with the architecture image and the resume attached, with the mobile number clearly visible.
4. If a callback was booked, a real scheduled job exists and will actually place that call.
5. Reconciliation: if the call dropped or a webhook was missed, a sweeper still sends the follow-up.
6. Everything visible on the dashboard for inspection and for defending decisions.

---

## 6. Language requirements

| Aspect | Requirement |
|--------|-------------|
| Languages | Telugu, Hindi, English — any of the three. |
| Selection | The lead chooses implicitly by how they answer. The system must "handle whichever one I answer in, **and stay in it**." |
| Code-switching | Must handle Telugu + English in the same sentence. Called out twice (hard parts, and the scorecard row: "including mixed sentences"). |
| Scoring | 10 points. |
| Practical implication | Telugu is the binding constraint. Hindi and English are well supported by nearly every vendor; Telugu STT and natural Telugu TTS are not. **Vendor choice must be driven by measured Telugu quality, not assumed.** |

---

## 7. Discovery requirements ("lead discovery")

**Interpretation note:** the assignment contains **no lead-sourcing / lead-generation requirement**. There is exactly one lead, and its number is given. "Discover" in this document means *in-call discovery questioning*. Anything resembling a lead-scraping pipeline is out of scope and would be a distraction. (Logged as OQ-01.)

Five slots must be covered, naturally, in a sensible order:

| Slot | Prompt intent |
|------|---------------|
| `budget` | What are they willing to spend |
| `products` | What do they sell |
| `product_count` | How many products (catalog size) |
| `timeline` | When do they want it live |
| `features` | What features they need (payments, delivery, multi-vendor, etc.) |

Scorecard wording: *"Asks the questions that actually qualify a buyer, in a natural order"* — 10 points. Explicit anti-pattern: "not as a form."

---

## 8. Hot / Warm / Cold — criteria and required actions (p3 cards, verbatim)

| | **HOT** | **WARM** | **COLD** |
|---|---|---|---|
| **Headline** | High buying intent | Interested, not ready | Just looking |
| **Signal** | Wants it, asking price and timeline | Real need, but a barrier: budget, timing, someone else decides | Curious, no clear need or budget |
| **Required action** | **Fire the WhatsApp before the call ends** | **Capture the barrier, schedule the callback** | **Log it, send the brochure, move on** |

Caption: *"Three states, three different actions. The action is the point, not the label."*

**The stated failure mode:** *"Most systems fail here. They transcribe well and then treat every caller the same. The classification is what decides the action, so get this part right."*

**Where they will push us (verbatim, p3):** *"Real people do not say I am a hot lead. They say things like **send me the details**, **my budget is not much right now**, **my brother handles this**, or **how soon can you start**. Your system is being judged on how it reads that, and on what it does next."*

Those four phrases are effectively a published test set. Mapping:

| Utterance | Read | Why |
|-----------|------|-----|
| "send me the details" | Hot (buying signal, wants material now) | Explicit request for material → mid-call WhatsApp is the literal correct action |
| "how soon can you start" | Hot | Asking timeline/price is the HOT card's own definition |
| "my budget is not much right now" | Warm, barrier = **budget** | Real need, stated constraint |
| "my brother handles this" | Warm, barrier = **someone else decides** | Real need, decision-maker elsewhere |

"Send me the details" is deliberately ambiguous-looking — it can read as a brush-off. The HOT card resolves it: the action for a details request is to *send the thing, now, while on the call*. Sending it costs nothing if the read is wrong; not sending it loses 15 points if the read is right. **Bias the boundary toward firing.**

---

## 9. Mid-call WhatsApp requirements

- Trigger: **high buying intent**, i.e. classification crossing to Hot. Scorecard: *"WhatsApp fires during the call, triggered by intent, **not by call end**."*
- Timing: the message must **reach** the lead before the call ends. Delivery, not just dispatch.
- Must not block the conversation (NFR-03).
- Worth 15 points — tied for the second-highest single row on the scorecard.
- "What will impress us" includes: *"The WhatsApp arrives while we are still talking."*

**Scoring implication:** the evaluator has to *notice* it arrive. Firing silently risks them not looking at their phone. The agent should verbally acknowledge the send in the same breath ("I've just sent that to your WhatsApp — you should see it now"), which converts a passive delivery into an observed event.

---

## 10. Callback scheduling requirements

- Input: spoken natural-language time. Canonical example: "call me back tomorrow morning."
- Output: a **booked** callback — the system "understands it and books the callback itself."
- Must handle **vague phrasing** (explicit in the scorecard).
- Worth 10 points.
- Listed under "the hard parts": *"Turning call me back tomorrow morning into an actual scheduled time."*
- Warm leads: scheduling the callback is their prescribed action.

---

## 11. Follow-up requirements

- "The follow up references what I actually said, not a template with my name pasted in."
- "What will impress us": *"The follow up quotes something specific I said."*
- Built "from their own words" (step 8 of the timeline).
- Scorecard row combines follow-up with WhatsApp quality: *"References real content from the conversation, and carries the four things listed in Section 06"* — 10 points.

---

## 12. What the final WhatsApp message must contain (p4 Section 06)

Preamble: *"This is part of the assignment, not an afterthought. When the call ends, the message that reaches me must contain all four of these."*

| # | Must contain | What good looks like |
|---|--------------|----------------------|
| 1 | **The context of our call** | "What I said I wanted, the budget I mentioned, the timeline, the features I asked about. Specifics from the conversation, not a summary that could apply to anyone." |
| 2 | **Proper framing of that context** | "Written as a person would write it after a real call. It should read like a follow up, not like a log file pasted into WhatsApp." |
| 3 | **Your mobile number** | "Clearly visible, so I can call you back without hunting for it." |
| 4 | **An image of how you built it** | "One image showing your architecture and flow. Hand drawn on paper is fine. We want to see how you think, not how well you use a diagram tool." |

Plus: *"Your resume goes with it. If your system can attach the resume automatically, better."*

---

## 13. Required submission artifacts

**Send to 8688664337:**
1. The working prototype, live, that can call the number on demand
2. A one page architecture diagram of what you built, as an image or PDF, showing the flow from call to action
3. A short note, **under 200 words**, on what works, what does not, and what you would build next
4. Your resume
5. Your mobile number
6. A repository link if you have one

**Do not send:**
1. A presentation explaining how you would build it
2. A plan, a proposal, or an estimate
3. A demo video instead of a working system
4. Anything that needs us to install something to see it work

Page 1 reinforces: *"Do not send a deck explaining how you would build it. Build it. Call me."*

---

## 14. Scorecard and how to maximize it (p4, verbatim)

| What we assess | What full marks looks like | Points |
|---|---|---|
| It calls and holds a conversation | Dials on its own, speaks naturally, survives a real two way conversation | **25** |
| Language handling | Works in Telugu, Hindi or English, including mixed sentences | **10** |
| Discovery quality | Asks the questions that actually qualify a buyer, in a natural order | **10** |
| Intent classification | Reads Hot, Warm or Cold correctly from indirect answers | **15** |
| Mid call action | WhatsApp fires during the call, triggered by intent, not by call end | **15** |
| Callback scheduling | Turns spoken time into a booked callback, correctly, including vague phrasing | **10** |
| Follow up and WhatsApp quality | References real content from the conversation, and carries the four things listed in Section 06 | **10** |
| Engineering judgement | Sensible architecture, handles failure, you can defend your choices | **5** |
| **Total** | | **100** |

Threshold: *"Anything at 60 or above gets a call back from us."*

### Score-maximization strategy

**Effort must be allocated by points, not by how interesting the problem is.**

- **25 pts — Call + conversation.** Largest row, and a hard dependency for every other row: if the call does not connect or the latency is bad, *the other 75 points are unreachable*. Sub-targets: autonomous dial to a +91 mobile, human-answer detection, <1.2 s p50 turn latency, working barge-in, graceful recovery from silence and off-script input, female Indian voice, subtle room ambience.
- **15 pts — Intent classification.** The document flags this as the common failure. Build a labelled evaluation set from the four phrases the PDF itself supplies plus Telugu/Hindi equivalents, and measure accuracy offline before the live call. Classify continuously on the running transcript, not once at the end.
- **15 pts — Mid-call action.** Two independent trigger paths (LLM tool call **and** an async classifier watchdog) so a single miss does not cost 15 points. Fire non-blocking, verbally acknowledge, and instrument the delivery timestamp against call-end so we can prove it landed mid-call.
- **10 pts — Language.** Choose STT/TTS on measured Telugu quality, not on brand. Run a bake-off before committing.
- **10 pts — Discovery.** Slot-tracking state machine, not a fixed script: never re-ask what was volunteered, always ask what is missing before closing.
- **10 pts — Callback scheduling.** Deterministic IST resolver with an LLM front-end, unit-tested over ~30 phrasings; verbally confirm the resolved date/time back to the lead (this is what the evaluator can actually hear and score); and make the scheduled job real, so a callback genuinely fires.
- **10 pts — Follow-up quality.** Compose from actual extracted slots with at least one near-verbatim quote. Assert programmatically that the outgoing message contains ≥3 extracted values before sending; block and regenerate if it reads generic.
- **5 pts — Engineering judgement.** Cheapest row, largely earned by the artifacts we are producing now plus honest failure handling and the under-200-word note.

**Compounding effects:** the mid-call WhatsApp depends on classification (15 depends on 15), and follow-up quality depends on extraction accuracy. Roughly **40 of 100 points sit downstream of the extraction + classification layer**, which is the strongest argument for the decoupled async classifier design.

---

## 15. Technical challenges named explicitly by the assignment (p3)

> **"The hard parts, in our experience"**
1. **Latency.** "If the reply takes three seconds, the conversation is dead."
2. **Interruption.** "People talk over the bot. Handle it."
3. **Code switching.** "Telugu and English in the same sentence is normal here."
4. **Firing an action mid call without blocking the conversation.**
5. **Turning "call me back tomorrow morning" into an actual scheduled time.**

> **"What will impress us"**
1. It works on the first attempt, live, without you babysitting it
2. The conversation sounds like a person, not a menu
3. The WhatsApp arrives while we are still talking
4. The follow up quotes something specific I said
5. You can explain every decision you made and what you would fix next

These ten lines are the closest thing to a hidden rubric the document offers, and they map almost one-to-one onto the scored rows. Treat them as acceptance criteria.

---

## 16. Constraints and warnings in the assignment

| Constraint | Text | Implication |
|---|---|---|
| Stack is free | "Use WAPI, OmniDimension, ElevenLabs, Twilio, Vapi, Retell, Soniox, a self hosted model, or anything else you like. We do not care about the stack. We care that it works." | Optimize purely for working + defensible. No marks for or against any vendor. |
| Suggestions are not requirements | "Nothing here is mandatory and using something else costs you no marks." | OmniDimension / Soniox are hints, not obligations — but the hints reveal what the evaluator considers adequate, so they are worth spiking. |
| No deck | "Do not send a deck explaining how you would build it. Build it. Call me." | Planning docs are for **us**, not for submission. Only the one-page diagram + <200-word note go out. |
| Cost is not the filter | "Spend what you need... Keep the receipts... reimburse what you spent building and testing this." | Do not pick a worse free tier over a better paid one. Buy the always-on host. Keep a receipts log. |
| Deliberately hard | "This assignment is deliberately harder than a normal internship task, because we are hiring on evidence rather than on a resume. Plenty of people will not finish it." | Expect vendor friction. Budget time for it. |
| Partial work is accepted | "If you get partway and the call connects but the classification is weak, send it anyway with your note on what you would fix." | **A working call beats a perfect unshipped system.** Ship in scorecard order and be honest in the note. |
| Rolling deadline, speed rewarded | "We would rather see a working call this week than a perfect one next month." | Bias every decision toward time-to-first-working-call. |

---

## 17. MUST HAVE / IMPLIED–NECESSARY / OPTIONAL–POLISH

### MUST HAVE — explicitly required by the assignment

| ID | Item |
|----|------|
| M-01 | Autonomous outbound call to +91 8688664337 (FR-01) |
| M-02 | Live prototype the evaluator can trigger on demand without installing anything (FR-02, NFR-09) |
| M-03 | Telugu / Hindi / English conversation, lock to the lead's language (FR-03) |
| M-04 | Code-switched sentence handling (FR-04) |
| M-05 | Conversational e-commerce-website sales pitch (FR-05) |
| M-06 | Natural discovery on budget / products / product count / timeline / features (FR-06) |
| M-07 | Understanding of vague and indirect answers (FR-07) |
| M-08 | Hot / Warm / Cold classification from indirect answers (FR-08) |
| M-09 | Hot → WhatsApp delivered before the call ends, triggered by intent (FR-09) |
| M-10 | Warm → barrier captured + callback scheduled (FR-10) |
| M-11 | Cold → logged, brochure sent, call closed (FR-11) |
| M-12 | Spoken time → booked callback, including vague phrasing (FR-12) |
| M-13 | Follow-up built from the lead's actual words (FR-13) |
| M-14 | Post-call WhatsApp containing all four required elements (FR-14) |
| M-15 | Resume sent with it, auto-attached if possible (FR-15) |
| M-16 | Survives interruption, silence, and off-script input (FR-16) |
| M-17 | Sub-3s (target sub-1.2s) turn latency (NFR-01) |
| M-18 | Barge-in (NFR-02) |
| M-19 | Non-blocking mid-call side effects (NFR-03) |
| M-20 | One-page architecture diagram, image or PDF (submission) |
| M-21 | Under-200-word note on what works / what does not / what next (submission) |
| M-22 | Mobile number + resume + repo link sent to 8688664337 (submission) |

### IMPLIED / NECESSARY — not stated, but the system cannot reliably work without them

| ID | Item | Why it is necessary |
|----|------|---------------------|
| I-01 | **Public HTTPS deployment with a stable URL** | Telephony/voice webhooks need a reachable endpoint; the on-demand trigger has to live somewhere the evaluator can reach. |
| I-02 | **A minimal web trigger UI ("Call me now" button)** | M-02 says live and on demand; the do-not-send list forbids anything requiring installation. A URL with a button is the only clean way to satisfy both. Borderline MUST. |
| I-03 | **Persistence layer** (calls, turns, extracted slots, classifications, actions, callbacks) | Follow-up quality, callback execution, and reconciliation all depend on durable state. Also the evidence trail for "defend your choices". |
| I-04 | **Conversation state / slot tracker** | Required to ask only what is missing and to avoid re-asking — the difference between "natural order" and "a form". |
| I-05 | **Structured extraction schema** | The follow-up must quote specifics; you cannot template specifics you have not extracted. |
| I-06 | **Async job runner + durable scheduler** | Callbacks must actually fire, and must survive a process restart. |
| I-07 | **Idempotency + de-duplication on WhatsApp sends** | Two trigger paths (tool call + watchdog) must not produce two messages. |
| I-08 | **Answer detection** (human vs voicemail vs no-answer) and a retry policy | Otherwise the agent pitches to an answering machine and the whole run is wasted. |
| I-09 | **Per-turn language detection + TTS voice routing** | "Stay in it" and code-switching cannot be satisfied by a single fixed voice/model in most vendor stacks. |
| I-10 | **Hosted, publicly reachable media** (architecture image, resume PDF, brochure) | WhatsApp media must be fetchable by the provider. |
| I-11 | **WhatsApp sender provisioning + pre-approved templates** | Business-initiated WhatsApp to a number that has never messaged us is template-gated. External approval latency, on the critical path. |
| I-12 | **Timezone handling pinned to Asia/Kolkata** | "Tomorrow morning" is meaningless without it; a UTC-defaulted server books the wrong day. |
| I-13 | **Reconciliation sweeper** for missed webhooks / dropped calls | Guarantees the post-call WhatsApp still goes out. Directly serves NFR-07. |
| I-14 | **Structured logging + a transcript/timeline view** | Debugging a live phone call is otherwise impossible, and it is the evidence for the 5-pt row. |
| I-15 | **Secrets management** (no credentials in the repo) | The repo link is a submitted artifact. |
| I-16 | **An offline evaluation set** for classification and time parsing | The only way to know these work before spending the one live first impression. |
| I-17 | **Test numbers we own**, used for rehearsal | The evaluator's number is a limited resource; do not burn the first impression on debugging. |

### OPTIONAL / POLISH — do not let these displace the above

| ID | Item | Note |
|----|------|------|
| O-01 | Live dashboard with real-time transcript streaming | Great for the callback conversation; not scored directly. |
| O-02 | Sentiment / talk-ratio analytics | Not asked for. |
| O-03 | Call audio playback in the dashboard | Cheap if the provider gives recordings; useful for self-review. |
| O-04 | CRM export / multi-lead pipeline | Explicitly out of scope — there is one lead. |
| O-05 | Auth / multi-user dashboard | Not needed for a prototype; a hard-to-guess URL is sufficient. |
| O-06 | Automatic architecture-diagram generation | The PDF says hand-drawn on paper is fine. Do not build a tool for this. |
| O-07 | Voice-cloned custom persona | Marginal gain over a good stock female Indian voice. |
| O-08 | A/B testing of opening lines | Nice, but the sample size is one call. |
| O-09 | Fine-tuned classifier model | A prompted frontier model plus a good eval set is faster and defensible. |
| O-10 | Docker / k8s / IaC | Adds time, adds nothing to the score. |

---

## 18. Open questions

### OQ-01 — Does "lead discovery" mean sourcing leads, or in-call discovery?
- **Unclear:** the brief lists "Discover" as a pipeline stage; it never says where leads come from.
- **Why it matters:** a lead-sourcing subsystem would consume days for zero scored points.
- **Assumption:** it means **in-call discovery questioning** of the five slots. There is exactly one lead and its number is printed on the cover page.
- **Risk if wrong:** essentially none. Nothing in the scorecard rewards sourcing. Low risk, high confidence.

### OQ-02 — Must the four required elements be in a *single* WhatsApp message?
- **Unclear:** "the message that reaches me must contain all four of these" reads singular, but WhatsApp permits only one media attachment per message, and the required set includes both an image and (with the resume) a document.
- **Why it matters:** determines whether we need one message or a 2–3 message sequence; affects template design and approval.
- **Assumption:** send one **primary** message carrying the architecture image + the full context + the mobile number (which satisfies all four literally, since the image is in that message), immediately followed by the resume as a document. The primary message must be self-sufficient.
- **Risk:** if the evaluator counts strictly, a follow-on resume message is a minor deduction at worst.

### OQ-03 — Is the "brochure" for Cold leads a distinct artifact?
- **Unclear:** the COLD card says "Log it, send the brochure, move on." No brochure is specified anywhere in the document.
- **Why it matters:** if Cold is the classification on the live call, we need something credible to send.
- **Assumption:** produce a lightweight one-page service brochure (PDF or image) on e-commerce website development, sent to Cold leads in place of the Hot mid-call message. The post-call context message + resume + architecture image still go out regardless of classification.
- **Risk:** low. Having it costs an hour; not having it leaves Cold with no defined action.

### OQ-04 — Does the mid-call WhatsApp obligation apply only to Hot?
- **Unclear:** the scorecard says "WhatsApp fires during the call, triggered by intent." The Hot card says "before the call ends." Warm and Cold have different prescribed actions.
- **Why it matters:** firing for everyone loses the "triggered by intent" distinction the rubric rewards; firing for no one — because the evaluator plays Warm — loses 15 points.
- **Assumption:** fire the **Hot** message mid-call only on Hot, but bias the Hot boundary generously (any explicit request for details / pricing / start-date ⇒ Hot). Warm and Cold get their own prescribed mid-call actions (barrier + callback confirmation; brochure), which are also observable during the call. All classifications get the full post-call message.
- **Risk:** medium. Mitigation: for Warm, still send the callback-confirmation WhatsApp mid-call — a genuine intent-triggered mid-call action, just a different message. That way *something correct* always fires during the call.

### OQ-05 — When is the evaluator willing to receive the call?
- **Unclear:** no time window given. They receive many candidate calls.
- **Why it matters:** an unanswered call scores zero on a 25-point row.
- **Assumption:** the on-demand trigger URL is the primary path (they call it when ready), and the WhatsApp submission goes first with that link so the call is expected. Any system-initiated attempts restricted to 10:00–19:00 IST with a bounded retry policy.
- **Risk:** medium. Mitigated by making the trigger evaluator-controlled rather than pushing an unexpected call.

### OQ-06 — What persona and company does the agent represent?
- **Unclear:** we are selling e-commerce website development, but the brief does not say as whom.
- **Why it matters:** it appears in the opening line, in the WhatsApp copy, and in the caller-ID impression.
- **Assumption:** the agent introduces itself as an AI assistant calling on behalf of **the candidate** (named), offering e-commerce website development. Honest about being AI if asked. Not impersonating ElevateBox, not claiming to be human.
- **Risk:** low, and honesty is the safer failure mode — an evaluator who asks "are you a bot?" and gets a smooth honest answer scores better than one who catches a lie.

### OQ-07 — How precise must the callback be, and does it have to actually execute?
- **Unclear:** "books the callback itself" — a stored booking, or a call that really happens?
- **Why it matters:** a real executed callback is a much stronger demonstration and costs little extra.
- **Assumption:** resolve to a concrete IST datetime, confirm it verbally, persist it, **and** register a real durable job that will place the call. Vague windows resolve by a stated convention (morning → 10:00, afternoon → 15:00, evening → 18:00 IST) and the agent says the resolved time aloud so the lead can correct it.
- **Risk:** low, upside high.

### OQ-08 — Is an unofficial WhatsApp integration acceptable?
- **Unclear:** WAPI is named as a possible tool; the brief does not address WhatsApp Business Platform policy.
- **Why it matters:** the official Cloud API requires business-initiated messages to use pre-approved templates, putting external approval latency on a 15-point critical path. Unofficial web-protocol libraries send free-form media instantly but violate WhatsApp's terms and risk the sending account.
- **Assumption:** build on the **official WhatsApp Cloud API** with templates as the primary path, and start that onboarding on day one because its latency is external and unbounded. Keep a documented fallback (an Indian BSP such as WAPI / AiSensy / Gupshup, or Twilio WhatsApp) if approval stalls.
- **Risk:** medium-high on schedule, low on correctness. A silent switch to an unofficial library would be indefensible in the "explain your choices" conversation, so it is not the default — and if it ever became the only path to a working demo, it must be disclosed in the note.

### OQ-09 — Any recording/consent disclosure obligation?
- **Unclear:** not addressed.
- **Why it matters:** we will record calls for debugging; the evaluator invited the call, so consent to the call exists, but recording is a separate matter.
- **Assumption:** record for internal debugging, disclose briefly if asked, do not publish recordings. Do not add a legal preamble to the opening line — it would hurt the "sounds like a person" impression for no scored gain.
- **Risk:** low.

### OQ-10 — How many test calls to 8688664337 are acceptable?
- **Unclear:** not addressed, but the number is shared across all candidates.
- **Why it matters:** burning the first impression on a broken build is unrecoverable in practice.
- **Assumption:** **zero** calls to the evaluator until the full end-to-end run has passed on numbers we own. Then one deliberate live call.
- **Risk:** low. This is purely discipline.

---

## 19. Requirement-to-test matrix (thinking like the evaluator)

| Req | What the evaluator is likely to do | What our system must do | How we verify it ourselves | Points | Failure risk |
|---|---|---|---|---|---|
| FR-01 Autonomous dial | Click the trigger link, or just wait for the phone to ring. Check that no human is on the line. | Place the call unattended; speak first within ~1 s of pickup. | 20+ dials to numbers we own from the deployed environment; log pickup→first-audio latency; test no-answer, busy, voicemail. | (25) | **HIGH** — +91 mobile termination, VoIP filtering, caller-ID trust, answer-machine misdetection. |
| FR-16 / NFR-01,02 Holds a conversation | Interrupt mid-sentence. Go silent for 5 s. Ask something off-script ("who is this?", "are you a bot?", "how much exactly?"). Talk over the greeting. | Barge-in stops audio <200 ms and re-plans; silence triggers a natural re-prompt, not a hang; off-script answered, then steered back. | Scripted adversarial call suite (10 scenarios) against our own number; p50/p95 turn latency from logs. | (25) | **HIGH** — latency is the single most likely killer. |
| FR-03/04 Language | Answer in Telugu. Later switch to English. Use one mixed sentence ("Budget ante, around one lakh anukuntunna"). | Detect from the first turn, lock, follow a deliberate switch, understand mixed input without breaking. | One test call per language + one code-mixed; native-speaker review of STT transcript and TTS naturalness; offline WER on ~30 recorded utterances. | 10 | **HIGH** — Telugu STT accuracy and natural Telugu TTS are the weakest links in every vendor stack. |
| FR-05 Sell the service | Judge whether it sounds like a person or a recording. Possibly ask "what do you actually do?" | Short, specific, conversational pitch; adapts to what they sell; no monologue over ~15 s. | Read the transcript aloud; hard cap on TTS segment length; human review of 3 rehearsal calls. | (25) | MEDIUM — over-long scripted turns are the usual tell. |
| FR-06 Discovery | Volunteer some slots unprompted; give a partial answer; refuse one. | Slot tracker: never re-ask a filled slot, always ask missing ones before closing, natural order and transitions. | Assert on rehearsal transcripts that all 5 slots are attempted and none re-asked; automated slot-coverage check. | 10 | MEDIUM — sounding like a form, or closing with slots unfilled. |
| FR-07/08 Classification | Use indirect phrasing verbatim from p3: "send me the details", "my budget is not much right now", "my brother handles this", "how soon can you start". Possibly in Telugu/Hindi. | Correct Hot/Warm/Cold + capture the barrier for Warm; continuously, on the running transcript. | Labelled eval set of 40+ indirect utterances across all three languages, including all four published phrases; target ≥90% on the published four, ≥85% overall. | **15** | **HIGH** — the PDF names this as the common failure. |
| FR-09 Mid-call WhatsApp | Say something high-intent, then look at their phone **while still talking**. | Fire within ~2 s of the intent turn, non-blocking; agent verbally acknowledges; message already contains real specifics. | Instrument `intent_detected_at`, `whatsapp_sent_at`, `whatsapp_delivered_at`, `call_ended_at`; assert delivered < ended in every rehearsal. | **15** | **HIGH** — template approval, provider delivery latency, and the evaluator simply not noticing. |
| FR-12 Callback | "Call me back tomorrow morning." Or vaguer: "sometime next week", "after 6", "Monday". | Resolve to a concrete IST datetime, **say it back**, persist, register a real job. | Unit tests over 30+ phrasings (en/hi/te) with frozen clocks; one end-to-end callback that actually rings our number. | 10 | MEDIUM — timezone drift, ambiguous "next Monday", server clock in UTC. |
| FR-13/14/15 Follow-up | Read the message. Look for their budget, timeline, features, a quote of their words. Look for the number without hunting. Open the image. Look for the resume. | Compose from extracted slots + one near-verbatim quote; image attached; number on its own line; resume follows immediately. | Pre-send assertion: message contains ≥3 extracted values and ≥1 quoted phrase; manual read-through against the four-item checklist; verify media renders on a real phone. | 10 | MEDIUM — generic-sounding summary; media URL not publicly fetchable. |
| NFR-07/08 Engineering judgement | Ask on the callback: why this stack, what breaks, what would you fix. | Coherent architecture, real failure handling, honest note. | These docs + the under-200-word note + a failure-injection pass (kill the WhatsApp API, drop the call, stall the LLM). | 5 | LOW. |
| FR-02 / NFR-09 Deliverable access | Open the link on a phone. Expect it to work with nothing installed. | Public HTTPS page, mobile-friendly, no cold-start stall, one button. | Open on a real phone on mobile data; measure first paint after 30 min idle. | (gates all) | MEDIUM — free-tier cold starts; expired tunnels. |

Parenthesised point values feed the 25-point "calls and holds a conversation" row.

---

## 20. Summary of the highest-leverage conclusions

1. **The 25-point row is also a dependency, not just a score.** If the call does not connect cleanly to a +91 mobile with low latency, nothing else can be scored. De-risk telephony first, before writing product code.
2. **Telugu is the binding vendor constraint.** Pick STT and TTS on measured Telugu quality — an evidence-based bake-off, not a brand choice.
3. **WhatsApp business-initiated messaging has external approval latency on a 15-point critical path.** Start provisioning on day one, in parallel with everything else.
4. **Classification should run asynchronously and continuously**, decoupled from the speech path, with two independent paths to firing the mid-call action. 30 of 100 points hang off it.
5. **The deliverable is a URL, not a repo.** "Live, on demand" plus "nothing to install" means a hosted page with a button.
6. **A working call this week beats a perfect one next month** — the document says so twice. Build in scorecard order and ship.
