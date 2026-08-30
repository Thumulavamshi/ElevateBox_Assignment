# Cost, Feasibility Gates, and Score Strategy

Companion to [`audit.md`](audit.md). Read that first — several items here exist because the audit found the original plan was measuring the wrong thing.

> **Pricing discipline:** every unit price below is marked `VERIFY`. Nothing here is quoted from a vendor. The arithmetic model is real and reusable; the numbers plugged into it are order-of-magnitude placeholders drawn from my own estimation, and they must be replaced with figures read off current pricing pages before any commitment. Verifying all of them is roughly a 30-minute task across ten browser tabs.
>
> **FX:** ₹88 = $1 assumed throughout. `VERIFY` current rate.

---

# Part 1 — External Feasibility Gates

Things that can prevent us from completing this assignment **even if our application code is perfect**. Each gate has a cheapest-possible experiment, a pass bar, and a stated fallback.

Gates are ordered by *(probability of blocking) × (cost of discovering it late)*.

---

### G1 — Outbound voice termination to Indian mobiles
**What could block us:** the provider cannot route to `+91` mobiles at acceptable quality, or calls are silently filtered by the destination carrier. Everything else in the assignment is downstream of this.

**Cheapest experiment:** free-trial account on one provider → place 10 calls to two `+91` handsets we own, playing a fixed TTS sentence. No application code; a curl request or the provider console is enough.
**Cost:** trial credit, likely under $2 (₹175). **Time:** 1 hour.
**Pass bar:** ≥8/10 connect with clean, non-robotic audio and no obvious one-way delay. *(Bar is mine — see audit §1.2.)*
**If it fails:** try the next route in order (Vapi-native → Twilio → Plivo → Indian CPaaS). If all international routes fail, Indian CPaaS becomes mandatory and G3 becomes the critical gate.

---

### G2 — Caller ID presentation and answerability
**What could block us:** the evaluator sees an unknown `+1`/`+44` number and does not answer. **This is the gate the original plan got wrong** (audit Finding B) — G1 measures whether the call *arrives*, G2 measures whether it is *picked up*, and only G2 gates the 25-point row in practice.

**Cheapest experiment:** ask two people who are *not expecting a call* to report what caller ID appeared and whether they would have answered it unprompted. Piggybacks on G1's calls — marginal cost zero.
**Cost:** $0. **Time:** 15 minutes.
**Pass bar:** the number presents as a plausible, non-spam-flagged caller.
**If it fails:** two mitigations, both cheap. (1) **Send the WhatsApp first, naming the exact number that will call** — this converts an unknown number into an expected one and costs nothing. The audit recommends adopting this regardless of outcome. (2) Pursue an Indian DID, which pushes us into G3.

---

### G3 — Indian regulatory routing (DND / promotional traffic)
**What could block us:** Indian CPaaS providers scrub promotional traffic against the DND registry and require sender registration. An automated outbound sales call is promotional on its face. **The route that best fixes G2 may be the route most likely to refuse the call** — a tension the original plan missed entirely (audit Finding C).

**Cheapest experiment:** a pre-sales email or chat to two Indian CPaaS providers asking directly: *can a single AI-voice outbound sales call be placed to a possibly-DND-registered mobile on your platform, and what registration does it require?* Ask **before** starting KYC.
**Cost:** $0. **Time:** 20 minutes to send; 1–3 days for answers — which is exactly why it goes out on day one.
**Pass bar:** a clear yes with a known registration path and a stated lead time.
**If it fails:** stay on the international route and lean entirely on the G2 announce-the-number mitigation.

---

### G4 — WhatsApp business-initiated messaging capability
**What could block us:** we cannot send to a number that has never messaged us. Requires a Meta Business account, a verified sender number, and approved templates. 25 points depend on it, and **the clock is entirely external.**

**Cheapest experiment:** create the account and submit all three templates. That *is* the experiment — there is no cheaper proxy for approval latency than starting the approval.
**Cost:** $0 to submit. **Time:** 2 hours of setup; approval latency unknown and unbounded.
**Pass bar:** all three templates approved, and one real message delivered to a phone we own that has never messaged the sender.
**If it fails or stalls:** Indian BSP (WAPI/AiSensy/Gupshup) — same underlying API, faster handholding, monthly fee. Last resort, disclosed not hidden: an unofficial library, which the audit recommends against.

---

### G5 — Opt-in policy and template category
**What could block us:** Meta policy expects businesses to have obtained opt-in before messaging. The evaluator has not opted in to us. Template **category** also matters: a MARKETING template to a non-opted-in user is the most throttling-prone combination, while UTILITY is more reliable but must genuinely read as transactional.

**Cheapest experiment:** submit one template in each plausible category and observe which is approved and how each behaves on a test send. Reveals the category boundary for our exact copy at no extra cost.
**Cost:** $0 plus a handful of test conversations. **Time:** folded into G4.
**Pass bar:** an approved template whose copy we can actually live with.
**If it fails:** rewrite the copy to fit the category that approves. The constraint shapes the copy, not the other way round.

---

### G6 — Mid-call WhatsApp *delivery* (not just dispatch)
**What could block us — and this was missing from the plan entirely:** for the message to arrive **while the call is live**, the evaluator's handset must have working data *during* a voice call. On VoLTE/5G that is normal. On a circuit-switched 2G/3G fallback, data is suspended for the duration of the call and **the message will not arrive until the call ends** — failing a 15-point row through no fault of our code. Separately, template throttling can add unpredictable delay.

**Cheapest experiment:** call our own handset, and while on that call, send a template message to it. Repeat on a second handset and, if possible, on a different carrier. This is the single highest-value cheap experiment in the whole list.
**Cost:** a few pennies. **Time:** 20 minutes, once G4 passes.
**Pass bar:** message visibly arrives during the call, on both handsets, within a few seconds.
**If it fails:** unfixable on the recipient's side. Mitigate by firing as early in the call as possible (maximising the window), and by having the agent say aloud that it has been sent — so the action is *observable* even if the buzz is late. Note it honestly in the 200-word note.

---

### G7 — Telugu speech recognition
**What could block us:** no usable streaming Telugu STT, or accuracy too low for classification to work downstream. Gates 10 points directly and degrades 15 more.

**Cheapest experiment:** record ~20 Telugu utterances **over a real phone call** (8 kHz telephony audio, not a clean laptop mic — this distinction matters and studio-quality tests will flatter every vendor). Run them through each candidate's free tier. Compare against hand transcripts.
**Cost:** free tiers, roughly $0–$5 (₹0–₹440). **Time:** 3 hours including recording.
**Pass bar:** transcripts good enough that a strong LLM reads the intent correctly — which is the real requirement, not word error rate.
**If it fails:** fall back to the R5 whole-lane substitution (speech-to-speech), or accept Hindi/English strength and disclose the Telugu limitation in the note.

---

### G8 — Telugu speech synthesis
**What could block us:** no natural female Telugu voice, or one that mangles code-switched sentences by changing voice mid-utterance.

**Cheapest experiment:** synthesise the same 10 sentences (including 3 code-mixed) through each candidate's free tier or web demo. Play them to a Telugu speaker over a phone call, not over laptop speakers.
**Cost:** $0–$5. **Time:** 2 hours.
**Pass bar:** a Telugu speaker says it sounds like a person, and a mixed sentence does not change voice mid-way.
**Unstaffed dependency (audit Finding K):** we have not confirmed access to a native Telugu speaker. **Resolve this before P0.3, or the 10-point row has no acceptance test.**
**If it fails:** Azure/Google `te-IN` as the safe floor.

---

### G9 — Hindi, English, and code-switching
**What could block us:** little. This is the lowest-risk language gate; every serious vendor handles Hindi and Indian-accented English. The real risk is *switching* — the system locking to the wrong language on turn one, or breaking on a mixed sentence.

**Cheapest experiment:** folded into G7/G8 using the mixed-sentence subset.
**Cost:** $0 marginal. **Pass bar:** correct language lock on turn one, no breakage on mixed input.

---

### G10 — Orchestrator ↔ provider composability
**What could block us:** the Telugu winner from G7/G8 is not natively supported by the chosen orchestrator, forcing a custom integration that adds latency and days of work. **This gate exists because of audit Finding A — the original plan could have produced a winner it could not use.**

**Cheapest experiment:** read each candidate orchestrator's provider list and write down which support `te-IN`. Pure desk research, before any bake-off.
**Cost:** $0. **Time:** 45 minutes. **This is the cheapest high-value experiment in the entire project and it must run first.**
**Pass bar:** at least two natively-supported `te-IN` options exist for both STT and TTS.
**If it fails:** either accept the custom-provider integration with eyes open and re-measure latency including the hop, or switch to the R5 speech-to-speech lane.

---

### G11 — Real-time tool/action triggering
**What could block us:** if the orchestrator only supports *blocking* tool calls, every mid-call action stalls the conversation by a full round trip — directly attacking the 3-second ceiling while trying to satisfy the mid-call row (audit Finding D).

**Cheapest experiment:** in the P0.4 throwaway assistant, define one background tool that hits a webhook, and measure whether the agent keeps talking while it runs.
**Cost:** trial credit. **Time:** folded into P0.4.
**Pass bar:** tool fires, webhook receives, conversation does not pause audibly.
**If it fails:** keep handlers under ~300 ms and accept a small stall; or trigger entirely from the async watchdog and drop the foreground path.

---

### G12 — Callback scheduling actually executing
**What could block us:** very little — this is the most-in-our-control gate on the list. The genuine hazards are timezone drift and duplicate firing (audit Finding E).

**Cheapest experiment:** schedule a job 3 minutes out, restart the process, confirm the phone rings once.
**Cost:** one call. **Time:** 30 minutes, after P1.
**Pass bar:** rings exactly once, at the right IST time, after a restart.

---

### Gate summary

| Gate | Blocks | Prob. of blocking | Cost to test | When |
|---|---|---|---|---|
| G10 Composability | Whole stack choice | Medium | **$0** | **First — desk research** |
| G4 WhatsApp capability | 25 pts | Medium-high | $0 | **Day one — external clock** |
| G3 Indian routing policy | Caller ID strategy | Medium | $0 | **Day one — external clock** |
| G1 India termination | Everything | Medium | ~$2 | Day one |
| G2 Answerability | 25 pts | Medium-high | $0 | With G1 |
| G6 Mid-call delivery | 15 pts | **Low-medium, high impact** | ~$1 | After G4 |
| G7 Telugu STT | 10 + 15 pts | Medium | $0–5 | After G10 |
| G8 Telugu TTS | 10 pts | Medium | $0–5 | After G10 |
| G11 Async tools | 15 pts | Low-medium | trial | With P0.4 |
| G9 Hi/En/mixed | 10 pts | Low | $0 | With G7/G8 |
| G12 Scheduling | 10 pts | Low | ~$0.50 | After P1 |

**Total cost to clear every gate: under $15 (≈₹1,300).** The four highest-value gates — G10, G4, G3, G2 — cost **nothing** and are mostly reading and emailing. There is no financial reason to skip any of them.

---

# Part 2 — Cost model

## 2.1 Reference call assumptions (ours, adjustable)

| Parameter | Value | Note |
|---|---|---|
| Call duration | 4 min | A discovery call that reaches classification |
| Agent speech share | ~50% → ~2 min ≈ ~2,000 characters | Drives TTS cost |
| Conversation turns | ~25 | Drives LLM cost |
| Speech-lane tokens | ~100k in / ~2.5k out cumulative | Grows with transcript; **prompt caching cuts this substantially** |
| Understanding-lane tokens | ~30k in / ~5k out | **Only if debounced.** Undebounced, this grows quadratically with turns — a cost line the original plan never modelled (audit §3) |
| WhatsApp per call | 1–2 conversations | Mid-call + post-call |

## 2.2 Unit prices — all require verification

| Line | Unit | Price | Status |
|---|---|---|---|
| Outbound voice → India mobile | per min | ? | `VERIFY` |
| Orchestrator platform fee | per min | ? | `VERIFY` — charged **on top of** providers |
| STT | per min | ? | `VERIFY` |
| TTS | per 1k chars | ? | `VERIFY` |
| LLM (speech lane) | per M tokens | ? | `VERIFY` |
| LLM (understanding lane) | per M tokens | ? | `VERIFY` |
| WhatsApp conversation (India) | per conversation | ? | `VERIFY` — category-dependent |
| Phone number rental | per month | ? | `VERIFY` |
| Hosting (always-on) | per month | ? | `VERIFY` |
| Managed Postgres | per month | likely $0 | `VERIFY` |
| BSP subscription (if needed) | per month | ? | `VERIFY` |

## 2.3 Scenario estimates

Derived from the model above with **order-of-magnitude placeholder rates**. Treat every figure as a band to be replaced, not a quote.

| Scenario | Voice minutes | Est. USD | Est. INR |
|---|---|---|---|
| **Initial setup** (accounts, templates, 0 calls) | 0 | $0 – $10 | ₹0 – ₹880 |
| **Gate testing** (G1–G12, all gates) | ~15 | $5 – $15 | ₹440 – ₹1,300 |
| **10 test calls** | 40 | $8 – $25 | ₹700 – ₹2,200 |
| **20 test calls** | 80 | $15 – $50 | ₹1,300 – ₹4,400 |
| **50 test calls** | 200 | $35 – $110 | ₹3,100 – ₹9,700 |
| **Final demonstration** (3 calls + messages) | 12 | $3 – $10 | ₹260 – ₹880 |
| **Hosting + number, 1 month** | — | $10 – $40 | ₹880 – ₹3,500 |
| **BSP subscription, 1 month** (only if G4 stalls) | — | $12 – $35 | ₹1,050 – ₹3,100 |

**Realistic all-in through submission (≈50 test calls, one month of infrastructure):**
### $60 – $220 · ₹5,300 – ₹19,400

The spread is dominated by two unknowns: the orchestrator's per-minute fee, and whether a BSP subscription is needed. Verifying just those two collapses most of the uncertainty.

## 2.4 Cost classification

**Unavoidable**
- Outbound voice minutes to India · Orchestrator or self-built voice loop · STT + TTS · LLM tokens · WhatsApp conversations · Some hosting

**Optional**
- BSP subscription (only if G4 stalls) · Indian DID (only if G2 fails) · Premium TTS over Azure/Google baseline · Call recording storage · A second test handset/SIM (cheap, and genuinely useful for G2/G6)

**One-time**
- Account setup, KYC, business verification (mostly time, not money) · Number provisioning fees · Trial credits · Resume/diagram/brochure production (time only)

**Recurring (monthly)**
- Hosting · Number rental · BSP subscription if used · Database if beyond free tier

**Experimental / test spend**
- Gate testing (~$15) · All rehearsal calls — **this is the largest controllable line.** 50 rehearsal calls cost several times the final demonstration, and that is correct: rehearsal is what buys "works on the first attempt".

## 2.5 The honest framing on money (audit Finding J)

The PDF says *"if you make it through and join us, we reimburse."* **Reimbursement is conditional on being hired.** This is at-risk personal spend, not a budget. The original planning docs read that sentence a little too generously.

Practical consequence: spend where it buys score — call quality, answer rate, always-on hosting, rehearsal minutes — and not where it buys comfort. At $60–$220, this is affordable, but it should be spent deliberately.

---

# Part 3 — Score Maximization Strategy

## 3.1 The minimum viable path to a strong submission

Point estimates below are **mine**, not the evaluator's. They are for sequencing decisions, not promises.

| Tier | What works | Est. score | Verdict |
|---|---|---|---|
| **T1** Call connects, holds an English conversation, natural discovery on all five slots | **~35–45** | Below threshold. Not submittable-strong, but already beats a non-working submission. |
| **T2** T1 + classification from indirect answers + mid-call WhatsApp firing on intent | **~62–75** | **Crosses the 60 callback threshold.** This is the real target. |
| **T3** T2 + callback scheduling + context-rich follow-up with all four elements | **~78–88** | Strong submission. |
| **T4** T3 + Telugu and Hindi working properly | **~88–97** | Full marks territory. |

**The single most important structural fact:** T2 is the whole game. Everything before it is table stakes and everything after it is upside. **Build to T2 as fast as possible, then improve.**

Note that T4's language work is only 10 points but is the hardest and most externally-constrained work in the project. **Do not start it before T2 is done.** The original plan's Phase 2 (conversation, all three languages) sat before Phase 4/5 (classification, mid-call) — the audit's view is that the *English* conversation must come first, with Telugu/Hindi added after T2 is reached.

## 3.2 What must work first — in strict order

1. **A call that connects and is answered** (G1, G2). Nothing exists without it.
2. **A conversation that survives interruption at sub-3-second latency.** The 25-point row, and the precondition for demonstrating anything else.
3. **Classification from indirect phrasing.** 15 points and the trigger for 15 more.
4. **The mid-call WhatsApp actually arriving during the call.** 15 points, and gated by an external clock (G4) that must be started on day one regardless of where the code is.

## 3.3 What can wait

- Telugu and Hindi (10 pts — start after T2; ship English-first)
- Callback *execution* (the resolution + spoken confirmation earns most of the 10 points; the automatic re-dial is the tail)
- The Cold-lead brochure (invented requirement, audit §1.1)
- The transcript timeline UI (logs suffice for debugging)
- SMS fallback
- Recording playback

## 3.4 Worth spending money on

| Spend | Why |
|---|---|
| Indian DID / better route, if G2 fails | Directly protects the 25-point row's precondition |
| Always-on hosting | A sleeping free tier makes the evaluator's first click hang — trading 25 points for a few dollars |
| Orchestrator platform fee | Buys ~2 weeks of barge-in and endpointing work |
| Rehearsal minutes (the largest test line) | The only way to earn "works on the first attempt" |
| A second handset/SIM | Makes G2 and G6 testable at all, for very little |
| BSP subscription, **only if** G4 stalls | Unblocks 25 points |

## 3.5 Unnecessary polish

Dashboard beyond a status page · auth · Docker/CI/IaC · voice cloning · sentiment analytics · CRM/multi-lead · call-recording UI · an elaborately produced architecture diagram (**the PDF explicitly says hand-drawn on paper is fine**).

## 3.6 Time sinks that consume effort without moving the score

These are the traps most likely to eat this project, roughly in order of danger:

1. **Building our own telephony/media pipeline** because it is more interesting. Days of latency tuning for points already available by configuration.
2. **Forcing a custom Telugu provider integration** when a natively-supported option would score 8/10 on a 10-point row (audit Finding A). Bounded upside, unbounded cost.
3. **Prompt-tuning without an eval set.** Unfalsifiable, infinitely absorbing, and it *feels* like progress.
4. **Perfecting the architecture diagram** against explicit instructions that hand-drawn is fine.
5. **Over-building the eval set** past the point where n improves the decision (audit Finding I: at n≈40 the interval is ±11 points; going to n=200 buys precision we will not act on).
6. **Chasing the last 200 ms of latency** once comfortably under the 3-second cliff.
7. **Generalising for multiple leads, languages, or tenants** that will never exist.
8. **Rebuilding scheduling infrastructure** for one job (audit Finding E — the fix is *less* code, not more).

## 3.7 The strategy in one line

**Get to T2 — a call that connects, converses, classifies, and fires the WhatsApp mid-call — before touching anything else. Start the WhatsApp and Indian-routing clocks on day one because they are external. Add Telugu after T2, not before.**
