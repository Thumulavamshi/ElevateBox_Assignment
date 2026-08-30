# Milestone 1 — First automated English call

**Goal:** one automated call to a mobile we own, holding a basic two-way English conversation.

**Not in scope yet:** WhatsApp, classification, scheduling, Telugu/Hindi, dashboard, backend. Deliberately. English-only means that if the first call misbehaves, we know it is not language detection.

**Status: blocked on Twilio reactivation.** Everything that can be built and validated without a call is done. Nothing here has spent money or dialled anything.

---

## What you do when Twilio comes back — the whole list

### 1. Twilio console (~5 min)

| | Where | Why |
|---|---|---|
| **Enable India** | Voice → Settings → **Geographic Permissions** → search India → tick → Save | Without this every call fails with **error 21215** before the phone rings |
| **Upgrade off trial** | Billing → Upgrade | Trial can only dial *verified* numbers. Fine for your phones, but you can't verify the evaluator's — so this blocks demo day, not today |
| **Buy a number** | Phone Numbers → Buy | Cheapest available is fine. Caller-ID quality is a separate test (P0.2b), not this one |

### 2. Vapi dashboard (~2 min)
Phone Numbers → **Import** → paste your Twilio Account SID, Auth Token, and number → click the imported number → **copy its ID** (a UUID, not the phone number).

Doing the import here means I never need your Twilio credentials at all.

### 3. Fill in `.env` (~1 min)

```bash
cp .env.example .env
```

Then open `.env` and set exactly three values:

```
VAPI_API_KEY=          # Vapi → Settings → API Keys → the PRIVATE key
VAPI_PHONE_NUMBER_ID=  # the UUID from step 2
TEST_NUMBER=+919876543210   # YOUR OWN mobile, E.164, no spaces
```

`.env` is gitignored. `run_probe.py` never prints its values — only character counts.

### 4. Run three commands

```bash
python experiments/voice-feasibility/run_probe.py check
```
Offline. No network, no spend. Tells you exactly which fields are still empty.

```bash
python experiments/voice-feasibility/run_probe.py preflight
```
Read-only + free. Verifies the API key, confirms the phone number is on your account, and **validates the voice/transcriber/model config server-side** — so a bad voice ID fails here, for free, instead of halfway through a real call. Prints a `VAPI_ASSISTANT_ID` to paste into `.env`.

```bash
python experiments/voice-feasibility/run_probe.py call --yes
```
**The only command that spends money and rings a phone.** Answer it, talk for ~90 seconds, say goodbye. It polls until the call ends, then prints the transcript, cost, recording URL, and saves the full payload to `results/`.

---

## What's configured

| Piece | Value | Why |
|---|---|---|
| Telephony | Twilio via Vapi | Vapi's free numbers **cannot make international calls** — BYO is mandatory |
| STT | Soniox `stt-rt-v5`, `languages: ["en"]` | Verified against Vapi's provider docs. **The multilingual phase is a one-line change**: set `languages: []` and Telugu/Hindi auto-detection with code-switching turns on. Nothing else changes. |
| TTS | Azure `en-IN-NeerjaNeural` | Female Indian voice, per the assignment's own hint that it lands better on outbound calls here |
| LLM | `gpt-4o-mini` | For a probe the model barely matters — this tests telephony + STT + TTS. Model choice is a later decision. |
| Turn style | 1–2 sentences, hard-capped | Long turns are the main "sounds like a recording" tell |

## Safety

`call` refuses to dial **8688664337** — tested against seven spellings (`+91…`, spaced, hyphenated, bare 10-digit, leading zero). The guard compares digits only, so no formatting variant gets through, and it fires **even with `--yes`**. Rehearsal happens on numbers we own; the evaluator gets exactly one deliberate call, later, after clean rehearsals.

## If the voice ID is rejected

`preflight` will fail with a `voice`/`voiceId` error. Don't edit `assistant.json` — override it from `.env`:

```
VOICE_PROVIDER=azure
VOICE_ID=<paste a valid ID from the Vapi dashboard>
```

Pick any **female Indian English** voice in Vapi → Voices. Azure `en-IN` and ElevenLabs both work; the probe doesn't care which.

## Other likely failures

| Symptom | Cause | Fix |
|---|---|---|
| `21215` in Twilio logs, phone never rings | India not enabled | Step 1, row 1 |
| Vapi `401` | Using the *public* key | Use the private key |
| `400 … credential` | Provider needs its own key | Vapi → Provider Keys, add Soniox |
| Rings, silence, then hangs up | TTS or STT misconfigured | Check `preflight` output |
| Call connects but no transcript | Soniox credential missing | Same as row 3 |

## Cost

~**$1–3** for one to three short calls. Vapi is $0.05/min (verified from their pricing page); Twilio's India mobile rate and Soniox usage are `VERIFY` — the `call` command prints the actual Vapi-side cost when it finishes.

## Recording the result

Fill in [`test-script.md`](test-script.md) after the call. For this milestone only the English rows matter — the Telugu and code-mixed rows are for the multilingual phase later.

**Milestone 1 is met when:** the phone rings unprompted, a two-way English conversation happens for ~90 seconds, and a transcript comes back.
