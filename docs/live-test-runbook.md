# Live mid-call test — runbook

Prove the whole flow on a real call: dial → converse → show intent → **WhatsApp arrives while still
talking** → follow-up after hangup.

Uses `hello_world` for the message body while our own template is in review. **Only the words
differ** — the trigger, the timing, the idempotency and the delivery path are all the real ones.

---

## Why a tunnel is needed

Vapi pushes live events (transcripts, tool calls) to a URL. It cannot reach `localhost`. Without a
public URL:

- no transcripts reach the understanding lane → the watchdog never sees intent
- no tool call reaches our handler → the agent's `send_details_now` goes nowhere

So the mid-call action **cannot fire at all** until Vapi can reach the backend. A tunnel gives us
that in one command, without committing to a deploy.

`agent.py` refuses to pretend: deploying without `SERVER_URL` strips the tools and webhooks and
prints a warning saying the mid-call WhatsApp cannot fire.

---

## Step 1 — install a tunnel (once)

`cloudflared` needs no account and is a single binary:

```
winget install --id Cloudflare.cloudflared
```

If winget is unavailable, download `cloudflared-windows-amd64.exe` from Cloudflare's GitHub
releases, rename it `cloudflared.exe`, and put it somewhere on PATH.

---

## Step 2 — point the mid-call action at hello_world

Add to `experiments/voice-feasibility/.env`:

```
WHATSAPP_TEMPLATE_MIDCALL=hello_world
```

Language and the no-parameters behaviour are detected automatically (`hello_world` is `en_US` and
takes no variables). Delete this line once our own template is approved — nothing else changes.

---

## Step 3 — three terminals

**Terminal 1 — the backend**

```
python -m uvicorn app.main:app --app-dir backend --reload --port 8000
```

**`--reload` matters.** Without it, editing backend code changes nothing until you restart the
process - and everything else (deploy, tunnel, config) keeps looking correct while the server serves
old code. That wasted two live calls. `agent.py call` now compares the running build hash against
the source on disk and refuses to dial if they differ.

**Terminal 2 — the tunnel**

```
cloudflared tunnel --url http://localhost:8000
```

It prints a URL like `https://random-words-1234.trycloudflare.com`. **Copy it.**

Sanity-check it in a browser: `<that-url>/health` should return JSON with
`"whatsapp": {"ready": true}`.

**Terminal 3 — deploy and call**

```
set SERVER_URL=https://random-words-1234.trycloudflare.com
```

```
python agent/agent.py deploy
```

Confirm it prints `serverUrl` and `tools: ['send_details_now']`. If it warns that `SERVER_URL` is
not set, the variable did not reach the process — set it in `.env` instead.

```
python agent/agent.py call --yes
```

---

## Step 4 — on the call

Answer, then **show positive intent**. Any of these should trigger it:

- *"Send me the details."*
- *"How soon can you start?"*
- *"Can you share the pricing on WhatsApp?"*

**Watch your phone while still talking.** The message should arrive within a couple of seconds, and
Maya should say something like *"just sent that across to your WhatsApp."*

Keep talking for another 30 seconds after it arrives — that is what makes it a *mid-call* action
rather than an end-of-call one.

Then say goodbye. A second message (the follow-up) should arrive shortly after the call ends.

---

## Step 5 — check the evidence

```
python agent/agent.py review
```

```
curl <tunnel-url>/calls
```

Then `GET /calls/{id}` for the full picture: turns, classification history, and the action ledger
with `requested_at` / `sent_at`. Compare `sent_at` against the call's `ended_at` — **that timestamp
pair is the proof the message landed mid-call**, which is exactly what the 15-point row is scored on.

---

## Expected trigger path

Two independent paths, one message:

1. **Tool call** — the model calls `send_details_now`. Handler claims the action, returns in
   milliseconds with a line the agent can speak, and the send happens in the background.
2. **Watchdog** — the transcript webhook reaches the understanding lane, the rules overlay reads
   "send me the details" as hot with no model call, and dispatches.

Whichever is second is a **no-op** — they share one idempotency key. The ledger records which fired
via `trigger_source`. Verified in simulation: tool call fired, watchdog saw the same intent one turn
later, total messages sent = 1.

---

## If something does not fire

| Symptom | Cause |
|---|---|
| No WhatsApp, agent never mentions it | Tunnel URL wrong or `deploy` warned about `SERVER_URL`. Check `agent.py inspect` |
| Agent says it sent but nothing arrives | Check backend logs. Likely a Meta API error — the ledger's `error` column has it |
| Nothing in `/calls` at all | Vapi cannot reach the tunnel. Open `<tunnel>/health` in a browser |
| Message arrives only *after* hangup | The trigger fired late. Check `requested_at` vs `ended_at` in the ledger |
| Tunnel URL changes | It is random per run. Re-`deploy` with the new URL each time |

---

## After the test

Remove `WHATSAPP_TEMPLATE_MIDCALL=hello_world` once the real template is approved.

The tunnel URL dies when you close Terminal 2 — that is fine for testing, but **the submitted
prototype needs a real deployment**, since the assignment requires a live URL the evaluator can use
on demand.
