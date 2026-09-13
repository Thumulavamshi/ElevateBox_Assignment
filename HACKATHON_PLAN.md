# Multi-App Agent Hackathon — build plan

**Lemma × Comma Capital · Sunday 13 Sep 2026, 09:00–17:00 · virtual**

> Build one useful, multi-step AI agent. Connect it to at least three external apps.
> Show how you know it works.

---

## The pitch

An AI agent that phones a lead, holds a real sales conversation in English, Hindi or Telugu,
and does the follow-up work a salesperson would otherwise do — **checking the calendar and
booking the callback, updating the CRM, and alerting the sales team — while the call is
still live**, with evidence that every action happened exactly once.

**The three apps: Google Calendar · HubSpot · Slack.** Gmail is an optional fourth.

**None of them need anything from the lead except what they say on the phone.** Every app acts
on the *sales team's* side, using the team's own accounts. The only thing we know about the lead
is their phone number, so the only lead-facing message is WhatsApp, which uses exactly that.

Voice is the input channel. **The apps and the proof are the product.**

---

## Where we start from — verified, not claimed

| Capability | State |
|---|---|
| Autonomous outbound calls (Vapi + Telnyx SIP) | working |
| Conversation in en / hi / te, with language lock and explicit-switch override | working, measured on live calls |
| Extraction of 5 discovery slots with verbatim quotes, verified against the transcript | working |
| Hot / Warm / Cold classification (deterministic rules overlay + LLM), off the speech path | working |
| Idempotent action bus — one action per call × type, background execution, retries | working |
| Spoken time → IST datetime resolver ("రేపు సాయంత్రం 4", "कल दो बजे") | working, 57/57 on a frozen clock |
| Callback worker — guarded claim, cannot double-dial, misfire handling | working |
| WhatsApp mid-call + follow-up (UltraMsg) | working |
| `/monitor` live view | working |
| Offline tests | 133 smoke assertions, 59 classification cases, quote-integrity verifier |

**Measured:** 75 answered calls · **$0.073/min** · median turn latency **1.6–1.9 s** over the
last 26 turns, **0 over 3 s**.

**Honest gap against the brief:** counted by the brief's definition, today there is **one**
external app the agent acts on — WhatsApp, through an unofficial gateway. Vapi, Telnyx, OpenAI,
Cartesia and Soniox are the agent's voice pipeline, not apps it operates on. Callbacks land in
local SQLite. **The multi-app layer is today's work.**

---

## The three apps

Every action goes through the existing action bus (`backend/app/actions.py`), so it inherits
idempotency, background execution and retries. Each app also gets its **own** duplicate guard,
because the bus protects against our double-dispatch, not against a network retry after a
success we never saw.

### 1 · Google Calendar — check availability, then book

Not a write-only sink. The agent reasons over live calendar state before committing.

```
lead: "call me tomorrow at 4"
  → timeparse resolves 16:00 IST
  → freeBusy on the rep's calendar for 16:00–16:30
      free → create event → "Booked, tomorrow at four."
      busy → next free 30-min slot in working hours → "Four is taken — is five okay?"
  → lead confirms → create event
```

- **Where:** inside the existing synchronous `schedule_callback` tool, via `callbacks.book()`.
- **API:** `POST /calendar/v3/freeBusy`, `POST /calendar/v3/calendars/{id}/events`.
- **Duplicate guard:** client-supplied event `id` derived from the callback row id (Calendar
  ids accept base32hex `0-9a-v`). A retry returns 409 instead of creating a second event.
- **Event:** title `Callback: <name> — <what they sell>`, IST time, description with the slots,
  the lead's phone, and a link to the call in the web UI.
- **Latency:** freeBusy adds a round trip inside a synchronous tool. Target < 800 ms. On timeout,
  book anyway, flag `availability_unchecked`, never leave the agent waiting.
- **Code:** new `backend/app/gcal.py`; hook in `callbacks.book()`.

### 2 · HubSpot — the system of record

A free CRM: **contacts** (people), **deals** (sales opportunities that move through pipeline
stages), and **notes** attached to them. It is what a sales team actually opens the morning
after — which is what makes our classification mean something outside our own database.

| Our read | HubSpot action |
|---|---|
| any real conversation | upsert contact by phone |
| **Hot** | create deal → stage `qualifiedtobuy` |
| **Warm** + callback booked | create deal → stage `appointmentscheduled` |
| **Cold** | contact only, no deal — "log it, move on" |
| call ended | note on the deal: summary, barrier, verbatim quotes, link to the Calendar event |

- **Trigger:** classification change in the understanding lane, finalised at call end.
- **No email needed.** A contact can be created from a phone number and a name alone.
- **Duplicate guard:** search contact by phone before creating; store HubSpot ids on the call row.
- **Auth:** private app access token, contacts / deals / notes write scopes.
- **Code:** new `backend/app/hubspot.py`; handler `crm_sync`.

### 3 · Slack — alert the sales team while the call is live

The lead never touches Slack. The agent posts into the **team's own channel** with a bot token.

| Moment | Message |
|---|---|
| intent turns **Hot** mid-call | *"Hot lead on the line now — sells groceries, ~200 products, wants it within a month."* with a link to the live call page |
| callback booked | event time + link to the Calendar event |
| call ended | one-line summary + link to the HubSpot deal |
| vulnerability, dispute, or "speak to a person" | escalation ping so a human can take over |

- **Why it's the third app:** it fires **during** the call, which is the strongest moment in
  the demo and the part a connector-wired chat agent can't imitate.
- **API:** `chat.postMessage`; later updates edit the same message with `chat.update` rather
  than posting a new one each time.
- **Duplicate guard:** store the message `ts` on the call row; if it exists, update, never post.
- **Auth:** Slack app with a bot token (`chat:write`), invited to one channel.
- **Code:** new `backend/app/slack.py`; handler `team_alert`.

### 4 · Gmail — optional, only if time remains after 15:00

Reuses the Google login already set up for Calendar. **Sends to the rep's own inbox**, so it
needs nothing from the lead: the full call report with quotes and links to the deal and event.

Never emails the lead. The agent doesn't collect an email address — spelling one over a phone
line is unreliable — and the lead's follow-up already goes to WhatsApp using their phone number.

### WhatsApp — existing, secondary, disclosed

Stays as the lead-facing channel. **Not counted toward the three.** Presented honestly as an
unofficial gateway (UltraMsg) chosen after Meta business verification stalled; the production
path is the Meta Cloud API, kept intact behind `WHATSAPP_PROVIDER=meta`.

---

## Reliability — detecting carrier media faults

Background: Telnyx confirmed inbound RTP reaches their media servers healthy (MOS 4.49, 0% loss),
yet ~18% of calls (6 of 33) delivered no caller audio to the pipeline. Two signatures:

| Signature | Detection |
|---|---|
| Silent ring before answer | created → answered > 15 s |
| No-way audio after answer | answered, ≥ 20 s elapsed, 1 agent turn, **0 lead turns** |

- Flag the call `suspected_no_audio`; show a live banner in the UI:
  *"No audio from the caller — likely a carrier fault. Hang up and redial."*
- Already handled: a call with no conversation sends no follow-up.
- **No automatic redial.** It would place a second real call; a human decides.
- **Demo mitigation:** web call through the Vapi Web SDK (browser microphone) bypasses telephony
  entirely — same assistant, same tools, no carrier.

---

## Web interface

No build step. Static HTML + vanilla JS served by FastAPI from `backend/app/static/`, polling
the read routes that already exist — the same idiom as `/monitor`.

| Page | Contents |
|---|---|
| **Start** | Web call (Vapi Web SDK) · phone call (existing `POST /calls`) |
| **Calls** | time, duration, language, intent, action badges (Calendar / HubSpot / Slack / WhatsApp), fault flags |
| **Call detail** | live transcript, intent timeline, slots with quotes, action timeline with **deep links into each app**, callback, fault banner |
| **Integrations** | per app: connected / missing scope / last error — extends `/health` |
| **Evidence** | latest eval run: pass rate per assertion, idempotency results |

New routes: `GET /api/evals/latest`; `/health` gains an `integrations` block.

---

## Proof — "show how you know it works"

1. **Replay harness against real apps.** Real recorded call transcripts replayed through
   `/vapi/webhook`, then assertions against the live sandbox apps:
   - Calendar event exists, at the correct IST time
   - a busy slot produces an alternative, not a double-booking
   - HubSpot contact exists; deal stage matches the classification
   - HubSpot note contains the lead's verbatim quote
   - Slack alert posted once, and later edited in place rather than re-posted
   - **each exactly once**
2. **Idempotency, shown live.** Replay the same webhooks twice → one event, one deal, one Slack message.
3. **Repeated runs.** N runs (e.g. 5) → pass-rate table on the Evidence page.
4. **Existing offline suites.** 133 smoke assertions, 59 classification cases, 57 time phrasings.
5. **Cleanup.** The harness tags its records and deletes them afterwards, so demo apps stay clean.

---

## Demo script (~3 minutes)

1. **Integrations** page — all green. *(10 s)*
2. **Start a web call.** Play a grocer. Say *"send me the details"*, then
   *"call me back tomorrow at four"* — with 16:00 pre-blocked on the calendar. *(90 s)*
3. **Call detail** and **Slack** side by side: intent moves to hot, the Slack alert lands while
   the call is still going, slots fill, agent says *"four is taken — five?"*
4. Hang up → flip to **Calendar** and the **HubSpot deal**. *(40 s)*
5. **Evidence** page: pass rate and the idempotency replay. *(30 s)*

Backup: a recorded clean run, ready to play if anything misbehaves live.

---

## Timeline and cut lines

| Time | Work |
|---|---|
| before 09:00 | setup checklist below |
| 09:00 | confirm the rule on pre-existing work; branch |
| 09:15–11:00 | Google OAuth, `gcal.py`, freeBusy inside `book()` |
| 11:00–12:30 | `hubspot.py`, `crm_sync` handler |
| 12:30–13:15 | `slack.py`, `team_alert` handler |
| 13:15–14:30 | replay harness + idempotency test |
| 14:30–15:45 | web UI (Calls, Detail, Integrations, Evidence) + web call |
| 15:45–16:30 | rehearse twice, record the backup |
| 16:30–17:00 | submit — **nothing new after 16:30** |

**Cut lines**

- Any integration fighting for more than 45 minutes → reduce it to write-only and move on.
- UI running late → keep `/monitor` + an Evidence page; skip the rest.
- Gmail → skip entirely; it's the optional fourth.
- **Three solid apps with proof beat four shaky ones.**

---

## Setup checklist — before 09:00

- [ ] Google Cloud project; enable **Calendar API** (and **Gmail API** only for the optional fourth)
- [ ] OAuth consent screen in *Testing*, add yourself as a test user, create a Desktop client
- [ ] Generate a refresh token with Calendar scopes (add `gmail.send` only if doing the optional fourth)
      (Testing-mode refresh tokens expire after 7 days — fine for today, not for production)
- [ ] Rep calendar id; **pre-block 16:00 tomorrow** for the conflict beat
- [ ] HubSpot free account; private app token with contacts / deals / notes scopes
- [ ] Slack app with a bot token (`chat:write`), invited to a `#sales-alerts` channel
- [ ] Vapi **public** key for the Web SDK
- [ ] New env vars — `GOOGLE_CLIENT_ID`, `GOOGLE_CLIENT_SECRET`, `GOOGLE_REFRESH_TOKEN`,
      `GOOGLE_CALENDAR_ID`, `HUBSPOT_TOKEN`, `SLACK_BOT_TOKEN`, `SLACK_CHANNEL_ID`, `VAPI_PUBLIC_KEY` — **never committed**
- [ ] Render env vars updated; after any tool change, `agent.py deploy` then `agent.py inspect`

---

## Risks, stated honestly

- **Pre-existing work** may not be allowed. If not: rebuild lean — a Vapi assistant whose tools
  call the three apps directly — carrying the prompt and guardrail knowledge, not the code.
- **App count is cheap now.** MCP and connector platforms let a team wire six apps in an hour.
  We compete on **depth** (reasoning over app state), **real-time action during a live call**,
  **multilingual voice**, and **proof** — not on breadth.
- **Voice demos are fragile.** Web call, not phone. Recorded backup.
- **UltraMsg is unofficial.** Disclosed; not counted.
- **freeBusy in a synchronous tool** adds latency to a spoken turn. Timeout and book anyway.

---

## Out of scope today

Multi-tenancy · billing · auth on the UI · owning the media pipeline · cold-lead brochure ·
Gmail (optional fourth, only after 15:00) · emailing the lead.

---

## After the hackathon

This is the base for a product, not a throwaway: a curated library of cloned Indian-language
voices, an Indian telephony provider instead of international transit, the official WhatsApp
API through a BSP, and multi-tenancy — self-serve for SMBs and mid-market first.
