# Deployment — Render, step by step

The assignment asks for **"the working prototype, live, that can call the number on
demand"** and forbids **"anything that needs us to install something to see it work."**
That makes deployment a scored submission item, not hosting convenience.

**Target: Render Starter ($7/mo) + a 1 GB persistent disk.** Roughly 30 minutes.

---

## Why Render, and why not the alternatives

| Rejected | Why |
|---|---|
| Render/Railway **free tier** | Sleeps. The evaluator's first click hangs 30–50 s. That trades the 25-point row for $7. |
| Vercel / Lambda / Cloudflare Workers | **Serverless cannot run this.** `callbacks.worker()` and `reconcile.worker()` are long-lived loops started in the app lifespan, and the action bus holds in-flight tasks. |
| A bare VPS | You would own TLS, restarts and deploys for no gain. |
| Railway | Genuinely fine, slightly faster to set up. Pick it if you prefer; every step below maps across. |

**Region: US.** Counterintuitive but deliberate — `schedule_callback` is a *synchronous*
tool call sitting on the speech path, and Vapi's infrastructure is US-based. A Mumbai
host adds ~200 ms to every tool round trip. Nothing else here is latency-sensitive.

**One instance only.** SQLite lives on a single attached disk. Scaling out would need
Postgres; the callback claim is already safe either way.

---

## Step 0 — Prerequisites (do these first)

### 0.1 Put the repo on GitHub

There is no git repo yet.

```bash
git init
git add -A
git commit -m "ElevateBox AI voice sales agent"
git branch -M main
git remote add origin https://github.com/<you>/elevatebox-voice-agent.git
git push -u origin main
```

**Before pushing, confirm no secrets are going up:**

```bash
git check-ignore -v experiments/voice-feasibility/.env
git ls-files | grep -i "\.env$"      # must print NOTHING
```

`.gitignore` already covers `.env` and `.env.*`. The repo link is a submitted artifact,
so this check matters.

### 0.2 Confirm the media files are committed

The follow-up inlines them as base64, so they ship in the repo:

```bash
git ls-files assets/
```

You should see `Architecture.png` and `resume.pdf`. `.env` now points at
**repo-relative** paths (`assets/Architecture.png`), which resolve on Linux; the old
`C:\Users\...` paths would have silently lost the architecture image — a required
Section 06 element.

**Resize `Architecture.png` under 500 KB** before pushing. At 1853 KB encoded it warns,
uploads slowly, and WhatsApp recompresses it anyway.

### 0.3 Swap the résumé

`assets/resume.pdf` is still the Qualcomm placeholder. Replace it with your real
résumé before anything reaches the evaluator.

---

## Step 1 — Create the Render service

1. [dashboard.render.com](https://dashboard.render.com) → **New** → **Web Service**
2. Connect the GitHub repo
3. Fill in:

| Field | Value |
|---|---|
| Name | `elevatebox-voice-agent` |
| Region | **Oregon** or **Ohio** (US) |
| Branch | `main` |
| Runtime | **Python 3** |
| Build command | `pip install -r backend/requirements.txt` |
| Start command | `uvicorn app.main:app --app-dir backend --host 0.0.0.0 --port $PORT` |
| Instance type | **Starter — $7/mo.** Not Free. |

`--host 0.0.0.0` is required; the default `127.0.0.1` is unreachable from outside the
container and the service will fail its health check.

---

## Step 2 — Add the persistent disk

**Do this before the first deploy.** Without it, SQLite lives on an ephemeral
filesystem and **every redeploy wipes booked callbacks, the action ledger, and the
transcripts** — the 10-point row would silently stop working.

Service → **Disks** → **Add Disk**:

| Field | Value |
|---|---|
| Name | `data` |
| Mount path | `/data` |
| Size | 1 GB |

---

## Step 3 — Environment variables

Service → **Environment** → add each. Copy the values from
`experiments/voice-feasibility/.env`.

```
DATABASE_PATH=/data/elevatebox.db      ← MUST point at the disk mount

VAPI_API_KEY=...
VAPI_PHONE_NUMBER_ID=ffb065fb-8687-4f26-90e9-6d2fb73c5eab
VAPI_ASSISTANT_ID=...
VAPI_WEBHOOK_SECRET=<generate a long random string>

ALLOWED_DESTINATION=+91XXXXXXXXXX      ← YOUR number until the real run

ANTHROPIC_API_KEY=...
CLASSIFIER_MODEL=claude-haiku-4-5      ← 5x cheaper, 96% on the eval

WHATSAPP_PROVIDER=ultramsg
ULTRAMSG_INSTANCE_ID=...
ULTRAMSG_TOKEN=...
WHATSAPP_ARCHITECTURE_IMAGE_URL=assets/Architecture.png
WHATSAPP_RESUME_URL=assets/resume.pdf
WHATSAPP_RESUME_FILENAME=Vamshidhar-Thumula-Resume.pdf

YOUR_NAME=Vamshidhar Thumula
YOUR_MOBILE_NUMBER=+91XXXXXXXXXX
DEMO_URL=https://<service>.onrender.com
REPO_URL=https://github.com/<you>/elevatebox-voice-agent
```

**`ALLOWED_DESTINATION` is the single safety control.** `POST /calls` takes no phone
number, so this is the only thing the deployed system can dial. Leave it on your own
number until the deliberate evaluator run.

Deploy. Watch the log for `callback worker started` and `reconcile worker started`.

---

## Step 4 — Verify before pointing Vapi at it

```bash
curl https://<service>.onrender.com/health
```

Check:

- `"can_place_calls": true`
- `"missing_settings": []`
- `"db": "/data/elevatebox.db"` ← on the disk, not in the container
- `"destination_is_evaluator": false`
- `"whatsapp": {"ready": true, ...}`
- every entry in `"actions"` reads `wired`

Then open the root URL on your phone. You should get the **Call me now** page.
**Don't press it yet** — Vapi still points at the old tunnel.

---

## Step 5 — Repoint Vapi at the stable URL

From your laptop:

```bash
SERVER_URL=https://<service>.onrender.com python agent/agent.py deploy
```

This rewrites the assistant's `serverUrl` **and** both tools' server URLs. Confirm the
`MID-CALL ACTION READINESS` block shows the Render URL, not a `trycloudflare.com` one.

Set the same `VAPI_WEBHOOK_SECRET` locally before deploying, so the header Vapi sends
matches what the server expects.

**The tunnel is now obsolete.** Stop `cloudflared` and the local `uvicorn`, or two
servers will be competing for the same webhooks.

---

## Step 6 — End-to-end test

Press **Call me now** on your phone. Then:

```bash
curl https://<service>.onrender.com/calls | python -m json.tool
```

You should see the call, its turns, extracted slots, classification history, actions,
and any callback. That page is also the evidence trail for "defend your choices".

---

## Before the evaluator run

- [ ] Real résumé at `assets/resume.pdf`
- [ ] `Architecture.png` redrawn and under 500 KB
- [ ] `EDIT ME` pricing in `agent/prompt.md` replaced with real rates
- [ ] Under-200-word note written — **it must disclose the unofficial WhatsApp gateway**
- [ ] Three consecutive clean rehearsals
- [ ] Only then: `ALLOWED_DESTINATION=+918688664337`, redeploy, and send the WhatsApp
      announcing the number that will call **before** triggering it

---

## Gotchas

**Render sleeps on Free, not Starter.** If the first click ever hangs ~30 s, you are on
the wrong plan.

**`DATABASE_PATH` not on `/data`** is the silent killer — everything works until the
first redeploy, then booked callbacks vanish.

**Redeploying restarts the workers.** A callback due during a deploy is picked up on
the next 20 s poll, and anything over 30 minutes late is marked `missed` rather than
dialled. That is deliberate.

**Render's free Postgres is irrelevant here.** SQLite on the disk is the right call for
one lead and one scheduled job (audit Finding F).
