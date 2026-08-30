# Language test script — Telugu, Hindi, code-switching

The experiment `docs/g10-provider-inventory.md` §7 specified and nobody has run yet. It settles the
**one genuinely open decision** on the 10-point language row: which TTS speaks Telugu well enough,
and whether Soniox actually transcribes Telugu off 8 kHz telephony audio rather than off a
marketing page.

**Three calls, ~35 minutes, ~$3.** Identical except for the voice.

---

## Why this cannot be skipped

`CLAUDE.md`: *"Prefer measuring over assuming, especially for Telugu STT/TTS quality. Vendor
documentation is not evidence."*

Everything about Telugu in this repo so far is **documentation**, not observation. g10 §6 lists the
open questions plainly: whether `languages: []` passes through Vapi correctly, whether Soniox holds
up on telephony audio, and whether any of the voices keep **one voice identity across a
code-switched sentence** instead of flipping mid-utterance.

The voice was chosen from **Vapi's live API** rather than documentation, after the documented
choice turned out not to exist (g10 §5b). But config validity is not audio quality: Cartesia
`sonic-3.5` has still **never spoken a word of Telugu on a real call.** That is what this tests.

---

## Setup

```bash
export SERVER_URL=https://<your-tunnel>    # or the deployed host
python agent/agent.py deploy
python agent/agent.py call --yes
```

**`SERVER_URL` must be set.** Deploying without it strips `serverMessages` and the tool ids, which
silently disables the mid-call WhatsApp and callback booking. `check` warns; believe it.

Between calls, change only the voice — no file edits, so the calls stay comparable:

```
# current default - Ramya, native Telugu female, the only config that covers te+hi+en
VOICE_PROVIDER=cartesia  VOICE_ID=cf061d8b-a752-4865-81a2-57570a6e0565  VOICE_MODEL=sonic-3.5

# same model, a different Telugu voice
VOICE_PROVIDER=cartesia  VOICE_ID=07bc462a-c644-49f1-baf7-82d5599131be  VOICE_MODEL=sonic-3.5

# Hindi-anchored, explicitly built for code-mixing ("Arushi - Hinglish Speaker")
VOICE_PROVIDER=cartesia  VOICE_ID=95d51f79-c397-46f9-b49a-23763d3eaa2d  VOICE_MODEL=sonic-3.5

# English-only fallback if Telugu TTS is unusable - Azure Indic en-IN female
VOICE_PROVIDER=azure     VOICE_ID=en-IN-AartiIndicNeural
```

**Azure and Smallest AI are not options for Telugu** — see `docs/g10-provider-inventory.md` §5b.
Azure has no voice covering te+hi+en, and Smallest AI is no longer a Vapi provider. Telugu needs
Cartesia `sonic-3` or newer; `sonic-2` silently lacks it.

---

## The six utterances

Read these to the agent in this order. Answer its questions normally around them — the point is to
hear Telugu come back, not to follow a script rigidly.

| # | Say | Tests |
|---|---|---|
| 1 | *"నేను చీరలు అమ్ముతాను"* — I sell sarees | Telugu transcribes at all, on phone audio |
| 2 | *"రెండు వందల డిజైన్లు ఉన్నాయి"* — about two hundred designs | Telugu numbers, which is where STT usually breaks |
| 3 | *"I need it in about a month"* | English baseline in the same call |
| 4 | *"मुझे payment gateway चाहिए"* — I need a payment gateway | Hindi, with an English noun |
| 5 | **"Budget ante around one lakh anukuntunna"** | **Telugu → English mid-sentence. FR-04.** |
| 6 | **"I'll decide later, ఇప్పుడు budget ఎక్కువ లేదు"** | **English → Telugu mid-sentence, and a WARM budget barrier** |

Then, to exercise the scored rows in the same call:

| # | Say | Tests |
|---|---|---|
| 7 | *"వివరాలు వాట్సాప్ కి పంపండి"* — send the details to WhatsApp | Mid-call action fires from **Telugu** (rules overlay, no model call) |
| 8 | *"రేపు ఉదయం call చేయండి"* — call me tomorrow morning | Callback booked from a Telugu time phrase |

---

## What to check afterwards

```bash
python agent/agent.py review          # latency, discovery coverage, turn length
```

Then read the transcript and **listen to the recording** — `review` cannot hear tone, and tone is
most of what is being judged here.

### Pass bar (from g10 §7, plus the rows built since)

- [ ] Telugu utterances come back **as Telugu**, not dropped and not romanised mush
- [ ] **Both halves of 5 and 6 survive.** This is the make-or-break line for FR-04
- [ ] The agent **replies in Telugu** from utterance 1 onward and does not drift back to English
- [ ] The voice is **intelligible in Telugu** and does not change speaker mid-sentence
- [ ] No per-language configuration was needed
- [ ] p50 end-of-speech → first-audio still under 3 s (Vapi's `performanceMetrics`, never derived)
- [ ] Utterance 7 fires the WhatsApp **during** the call
- [ ] Utterance 8 books a callback and the agent **says the resolved time back in Telugu**

### If STT fails
Try Google or Gladia in the same harness before touching Sarvam — g10 §4 costs out the custom
Sarvam bridge and rejects it.

### If TTS fails
That is the cheaper problem. Three native options remain untried, and this is exactly what the
three calls are for.

### If it all fails
Pin `transcriber.languages` back to `["en"]` and ship English-only. That is 10 points, and the
assignment explicitly accepts honest partial work with a note. **Do not spend days here** — the
score strategy names "forcing a custom Telugu provider" as the second-biggest time sink in the
project.
