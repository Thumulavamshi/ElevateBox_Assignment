# Phase 2 — English discovery conversation

The 25-point row ("calls and holds a conversation") plus the 10-point Discovery row.

**Now also multilingual.** `transcriber.languages: []` enables Soniox auto-detect with
code-switching; the prompt names English, Hindi and Telugu and mirrors whichever the lead uses.
The **voice is the open question** - see `language-test-script.md` for the bake-off that settles it.
Pin `languages` back to `["en"]` to reproduce the English-only calls below.

## Files

| File | What it is |
|---|---|
| `prompt.md` | **The actual work product.** The system prompt, in a readable file rather than crammed into JSON. Edit → `deploy` → live. |
| `assistant.json` | Vapi config: transcriber, voice, endpointing. No prompt inside it. |
| `agent.py` | `check` / `deploy` / `call` / `review`. Stdlib only. |
| `transcripts/` | One JSON per call. `baseline-milestone1.json` is the pre-Phase-2 call, kept for comparison. |
| `language-test-script.md` | The te/hi/code-switching bake-off: 3 calls, 8 utterances, explicit pass bar. |

Credentials are reused from `experiments/voice-feasibility/.env` — nothing to re-enter.

## Commands

```bash
python agent/agent.py check
```
Offline. No network, no spend.

```bash
python agent/agent.py deploy
```
Pushes `prompt.md` + `assistant.json` to Vapi. Free, places no call. First run prints a `VAPI_ASSISTANT_ID` — **paste it into `.env`** so later deploys update in place instead of creating duplicates.

```bash
python agent/agent.py call --yes
```
Places one call, waits, saves the transcript, then reviews it automatically.

```bash
python agent/agent.py review           # most recent call
python agent/agent.py review <call-id> # a specific one
```
Offline scoring of a saved transcript.

## What `review` measures

**Response latency** — end of your speech to the agent's first audio, per turn. The assignment says three seconds kills the conversation, so this is the number that matters most.

**Discovery coverage** — which of the five topics the agent actually *asked* about. It only counts question turns and skips the greeting, so "I help small businesses" doesn't score as asking what you sell.

**Turn length** — agent turns over two sentences or forty words. Long turns are the main "this is a recording" tell.

**Re-asking** — the same topic asked three or more times.

The numbers can't hear tone. Listen to the recording too — the URL is printed.

## Where we are

Latency numbers below are **Vapi's own `performanceMetrics`**, not derived. An earlier version of
`review` computed latency as (bot start - end of transcribed user utterance) and **overstated it by
1-1.5 s**, because Soniox finalises a transcript after the person has actually stopped speaking.
Two calls were reported as failing the 3 s cliff when Vapi had measured them at ~2.0 s.

| | Baseline | Call #1 | Call #2 | Target |
|---|---|---|---|---|
| Topics asked | 3 of 5 | 5 of 5 | **5 of 5** | 5 of 5 |
| Median turn latency | 1360 ms | 1990 ms | **1971 ms** | under 1500 ms |
| Turns over 3 s | 1 of 7 | 1 of 9 | **1 of 7** | 0 |

**Latency is not the crisis it looked like.** ~2.0 s median is under the assignment's 3 s cliff.
Discovery is solved. The two live problems are audio naturalness and sales content.

### Where the 2.0 s actually goes (call #2 average)

| Component | ms |
|---|---|
| LLM | 571 |
| endpointing | 517 |
| TTS | 454 |
| STT | 398 |
| **total** | **2024** |

Note the baseline measured **1.43 ms** of endpointing latency against our **517 ms** — the
`startSpeakingPlan` we added costs roughly half a second. That is the single biggest available
saving, but removing it risks the mid-thought cut-ins it was added to prevent. Worth one A/B call
once the higher-priority items below are settled.

### The "laggy gaps between words" - diagnosed

Not latency. The raw LLM output was:

    "Got it. A fully featured store. Just to check: what. 's your. Budget for this project?"
    "Good buy. Good buy."

A full stop is a pause in TTS, so those stray ones are heard as stutters mid-sentence. Cause: the
model sees Soniox's messy transcript punctuation ("Uh, somewhere. Around 50 to 100.") in its own
context and **mirrors that style**. Fixed with an explicit prompt rule; if it survives, the next
lever is a stronger model than `gpt-4o-mini`.

## How to test

Run three or four calls, playing a different person each time. Don't be a cooperative interviewee — the evaluator won't be.

1. **Straightforward buyer.** Answer normally. Checks all five topics get asked and the recap is right.
2. **Interrupter.** Cut the agent off mid-sentence, twice. It must stop, answer what you said, and not resume its old sentence.
3. **Hesitant talker.** Trail off mid-answer — *"I want it by… uh…"* — and pause. It must wait, not jump in. **This is the exact failure in the baseline call**, where the agent cut in with "Sorry," while the user was still thinking.
4. **Volunteer out of order.** Open with *"I sell sarees, about 200 of them, budget's around a lakh."* It must recognise three topics are answered, never re-ask them, and go after only timeline and features.
5. **Awkward.** Ask "how much does this cost?" first. Ask "are you a bot?". Say "I'm busy". Say "not interested".

After each: `python agent/agent.py review`.

## Tuning without editing files

Set these in `.env` and re-`deploy` — useful for comparing calls:

```
ENDPOINT_WAIT=0.3        # pause before the agent starts thinking
ENDPOINT_NO_PUNCT=1.0    # wait when the transcript has no end punctuation
ENDPOINT_PUNCT=0.3       # wait when it does
VOICE_PROVIDER=azure
VOICE_ID=en-IN-NeerjaNeural
BACKGROUND_SOUND=office  # room ambience; off by default, may cost STT accuracy
```

If latency is still high after tuning, the remaining levers in order: a faster TTS provider, then a faster model. Change one thing per call or you won't know what helped.

## Script debt — deliberately deferred

Phase 2 is being closed as **good enough**, not finished. These are known and logged so they
are not lost. Revisit them *after* WhatsApp and classification land, because the prompt has to
change for those anyway — polishing it now would be partly throwaway work.

1. **Turn length.** 5 of 8 agent turns run past two sentences. This is the direct cost of the
   "give an insight, then ask" rule that made the content good. Tighten the insight, not the rule.
2. **The recap regressed.** Call #2 played back all five slots before closing; call #3 only
   mentioned budget. The close should always recap everything so the person can correct it.
3. **The greeting is three sentences.** It flags as long on every call.
4. **Features gets asked twice** (payments, then tracking/WhatsApp). Reasonable, but it trips the
   re-asking heuristic — decide whether it should be one combined question.
5. **`EDIT ME` pricing is still my invention.** Geeta quotes these rupee ranges on live calls.
   **This must be replaced with real rates before anything goes to the evaluator.**
6. ~~"Never promise a WhatsApp or callback" must come out of the prompt~~ — done; the prompt now
   drives `send_details_now` and `schedule_callback`, and forbids claiming either without the tool.

## Known gaps in this phase

- Both tools are live: `send_details_now` and `schedule_callback`. The prompt forbids claiming
  either happened unless the tool actually did it — the 28 Aug call had the agent say it had sent
  a WhatsApp without calling the tool, which the watchdog happened to cover.
- The pricing block in `prompt.md` is marked `EDIT ME` and is **my placeholder, not your real rates**. The agent will quote it on a live call. `check` warns while the marker is still there.
- `call.start.error-get-transport` killed 3 of 4 milestone-1 attempts. Cause not yet diagnosed. If it recurs, that is a reliability problem for the 25-point row and needs its own investigation.
