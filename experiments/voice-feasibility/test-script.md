# Test Script — read this aloud, identically, in all three calls

Six utterances. Do not improvise — identical input is what makes the three TTS candidates comparable.
Wait for the agent to finish replying before the next line (interruption is tested later, in P2).

---

### Telugu only — does Telugu survive 8 kHz telephony audio at all?

**1.** నాకు ఒక ఆన్‌లైన్ షాప్ కావాలి, నేను బట్టలు అమ్ముతున్నాను.
*Naaku oka online shop kaavaali, nenu battalu ammutunnaanu.*
— "I need an online shop, I sell clothes."

**2.** ధర ఎంత అవుతుంది? ఎంత టైం పడుతుంది?
*Dhara enta avutundi? Enta time padutundi?*
— "How much will it cost? How long will it take?"

### English only — baseline

**3.** "I run a small clothing business and I want to start selling online."

**4.** "What's your pricing, and how soon can you start?"

### Code-mixed — THE MAKE-OR-BREAK TEST (FR-04)

**5.** Telugu → English mid-sentence:
నా బడ్జెట్ ఒక లక్ష వరకు ఉంది, but I need payment gateway and delivery tracking also.
*Naa budget oka laksha varaku undi, but I need payment gateway and delivery tracking also.*

**6.** English → Telugu mid-sentence:
"Actually my brother handles this, వాడితో మాట్లాడి చెప్తాను."
*Actually my brother handles this, vaaditho maatlaadi cheptaanu.*
— "…I'll talk to him and let you know."

> Utterance 6 is deliberately one of the four phrases the assignment publishes as a classification test ("my brother handles this"), delivered code-mixed. It probes FR-04 now and previews FR-08 later.

---

## Scorecard — fill from the Vapi transcript + recording

| | Call 1 · Azure | Call 2 · ElevenLabs | Call 3 · Smallest AI |
|---|---|---|---|
| Call connected at all | | | |
| Time from pickup → first word | | | |
| **U1 Telugu transcribed correctly** | | | |
| **U2 Telugu transcribed correctly** | | | |
| U3 English correct | | | |
| U4 English correct | | | |
| **U5 — BOTH halves survive** | | | |
| **U6 — BOTH halves survive** | | | |
| Agent replied in the right language | | | |
| Telugu TTS intelligible (rate 1–5) | | | |
| **Voice stays the same across a mixed sentence** | | | |
| Turn latency felt under ~2 s | | | |
| Audio quality / dropouts | | | |

**Two evaluators** (you + the second Telugu speaker) rate the TTS naturalness rows independently, then compare. Disagreement on Telugu naturalness is itself a signal.

## Pass bar

- Telugu transcribed **as Telugu** — not dropped, not romanised mush
- **Rows U5 and U6 pass.** This is the requirement the assignment calls out twice; a fail here matters more than any TTS complaint
- No per-language configuration was needed anywhere
- TTS renders Telugu intelligibly and holds one voice through a mixed sentence
- A two-way conversation actually happened for ~2 minutes

## Record the failures too

Note anything odd verbatim — truncated first words, the agent switching to English unprompted, long pauses, transcription of Telugu into Roman script. These become the "what does not work" half of the under-200-word submission note, and they are more useful now than they will be later.
