# G10 / P0.0 — Provider Composability Inventory

**Question:** does Vapi natively support a Telugu-capable STT and TTS, or do we need a custom Sarvam integration?
**Answer:** natively supported. **Do not build a custom Sarvam bridge for v1.**
**Method:** vendor documentation, August 2026. Desk research only, $0, no accounts created.

---

## 1. Vapi's native provider lists

**Transcribers (STT):** AssemblyAI · Azure · Cartesia · Deepgram · ElevenLabs · Gladia · Google · OpenAI · **Soniox** · Speechmatics · Talkscriber · xAI

**Voices (TTS):** Vapi Voices · Azure · Cartesia · Deepgram · ElevenLabs · Hume · Inworld · LMNT · Microsoft · MiniMax · Neuphonic · OpenAI · PlayHT · Rime AI · Sesame · **Smallest AI** · WellSaid · xAI

**Sarvam appears in neither list.** Audit Finding A is confirmed: the design's "swap in whatever wins the bake-off" premise was false for Sarvam specifically. Using Sarvam requires the Custom Transcriber and Custom TTS paths.

---

## 2. The decisive finding: Telugu ≠ Telugu code-switching

FR-04 requires Telugu and English **in the same sentence** — the assignment calls this out twice. Several providers "support Telugu" in a way that does not satisfy this.

| Transcriber | Telugu? | Telugu **in a code-switching mode**? | Verdict |
|---|---|---|---|
| **Soniox** `stt-rt-v5` | Yes — in its 60+ language set | **Yes.** Setting `transcriber.languages` to `[]` enables auto-detection "including code-switching within a conversation" | ✅ **Only clean match** |
| **Deepgram** Nova-3 | Yes, as a single selected language (`te`) | **No.** The `multi` code-switching set is English, Spanish, French, German, **Hindi**, Russian, Portuguese, Japanese, Italian, Dutch — **Telugu is excluded** | ❌ Telugu-only *or* code-switching, never both. Fine for Hindi+English. |
| **Google** | Multilingual setting available | Unverified for Telugu; Vapi notes it is slower | ⚠️ Fallback, needs checking |
| **Gladia** | Vapi cites "excellent ... code-switching" | Telugu coverage unverified | ⚠️ Fallback, needs checking |
| Azure / OpenAI / Speechmatics / Talkscriber | — | **No auto-detection at all** per Vapi's own docs | ❌ |

**This is the whole result.** Deepgram would nominally pass a naive "does it support Telugu?" check and then fail the actual requirement in production. Note also that **Vapi's own multilingual guide recommends Deepgram Nova-3 `multi`** — that recommendation is wrong for our case, and we deviate from it with evidence.

**Worth noting:** the assignment suggested Soniox for live transcription. That hint turns out to be technically correct for precisely the hardest part of the language requirement.

---

## 3. Telugu-capable TTS natively in Vapi

| Provider | Telugu | Note |
|---|---|---|
| **ElevenLabs** | Yes — dedicated Telugu voices | Strongest naturalness reputation; needs a female Indian voice selected |
| **Azure / Microsoft** | Yes — `te-IN` neural voices | Also exposes a `multilingual-auto` voice ID for automatic language selection |
| **Smallest AI** | Indian vendor, "all major Indian languages" | `VERIFY` — the Vapi doc page 404'd during this check |
| **Vapi Voices V2** | `language: "auto"` | Built-in auto language detection |

**Pass bar met:** the P0.0 exit criterion was ≥2 native options for both STT and TTS. STT has 1 clean + 2 unverified fallbacks; TTS has 3–4.

---

## 4. Cost of the custom Sarvam path (the rejected alternative)

Sarvam is technically capable — Saarika/Saaras STT and Bulbul TTS both stream over WebSocket, with claimed ~180 ms TTS first-byte latency. The problem is not Sarvam; it is what wiring it into Vapi costs us:

- **Custom Transcriber:** we host a WebSocket server. Vapi sends 16 kHz **stereo** linear16 PCM after a JSON `start` frame; we must de-interleave channels, forward to Sarvam, and return `{type: "transcriber-response", transcription, channel, transcriptType}` frames. Channel attribution (customer vs assistant) is ours to get right.
- **Custom TTS:** a second, separate integration.
- **Consequences:** two stateful realtime services to deploy, authenticate, monitor, and reconnect — plus **an extra network hop inside the latency budget** we are defending against a 3-second cliff.

**Verdict: not justified.** This buys an unproven quality delta on a **10-point row** in exchange for two hosted realtime services and added latency — the exact pattern flagged as a time sink in the score strategy. Sarvam stays as documented Plan B if Soniox fails on real telephony audio.

---

## 5. Recommendation

**Vapi + native Soniox (`stt-rt-v5`, `languages: []`) + a TTS chosen by bake-off from ElevenLabs / Azure / Smallest AI.**

1. Soniox is the only Vapi-native transcriber meeting Telugu **and** code-switching together — the literal FR-04 requirement.
2. Zero integration cost, no extra hop, nothing to host.
3. Evaluator-aligned: the assignment named Soniox for this exact use case.
4. Sarvam's cost is real and its benefit is unproven.
5. Revision **R5** (whole-lane speech-to-speech substitution) stays parked and is now *less* likely to be needed.

**Implementation note from Vapi's docs:** system prompts must **explicitly list the languages the assistant may speak** — assistants otherwise fail to realise they are multilingual. This goes into the Phase 2 prompt.

---

## 5b. CORRECTION — 2026-08-29, from Vapi's live API

**Three of §3's claims were wrong.** They came from vendor documentation; these come from Vapi's
own `/voice-library` endpoint and its config validator, which is the thing that actually decides.
This is the clearest example in the project of why our own rules say vendor documentation is not
evidence.

| §3 claim | What the API says |
|---|---|
| Azure "exposes a `multilingual-auto` voice ID for automatic language selection" | **No such voice.** `PATCH /assistant` returns 400: *"Couldn't Find Azure Voice ... should look like en-US-EmmaNeural"* |
| Azure `te-IN` neural voices make Azure a Telugu option | Technically true — `te-IN-ShrutiNeural` and `te-IN-MohanNeural` exist — but **all 59 Azure multilingual voices are European/Chinese-anchored and none covers Telugu.** No single Azure voice speaks te + hi + en, and the assistant has only one voice slot |
| Smallest AI is a bake-off entrant | **Not a Vapi voice provider.** The API rejects it: valid providers are `vapi, 11labs, azure, cartesia, custom-voice, deepgram, hume, lmnt, neuphonic, openai, playht…` |

**And the winner was never in the bake-off.** **Cartesia** — absent from §3 entirely — is the only
native provider with genuine Telugu: 9 Telugu voices, 44 language codes, plus Hindi voices including
one literally named *"Arushi - Hinglish Speaker"*.

Vapi's validator is precise about which Cartesia models reach Telugu:

- `sonic` and `sonic-2` → `en, fr, de, es, pt, zh, ja, hi, it, ko, nl, pl, ru, sv, tr` — **Telugu absent**
- Telugu requires → `sonic-3.5`, `sonic-3.5-2026-05-04`, `sonic-3`, `sonic-3-2026-01-12`, `sonic-3-2025-10-27`

**Chosen: `cartesia` / `cf061d8b-a752-4865-81a2-57570a6e0565` ("Ramya - Graceful Host", native Telugu
female) / `sonic-3.5`, with `language` deliberately unset** so the voice follows the text rather than
being pinned to one language — pinning it would defeat "handle whichever one I answer in, and stay in
it". One voice across all three is also what keeps a code-switched sentence in a single speaker
identity, which `system-design.md` §4.4 wanted and Azure structurally cannot provide.

**Still unheard on a real call.** Configuration validity is not audio quality. `agent/language-test-script.md`.

## 6. What this check could NOT establish

Documentation is a provider list, not evidence of quality. Still open:

- **Soniox Telugu accuracy on 8 kHz telephony audio.** All claims are marketing-grade. This is the one thing the experiment must measure.
- Whether `languages: []` passes through Vapi correctly in practice.
- Whether ElevenLabs / Smallest AI hold **one voice identity across a code-switched sentence**, or switch voice mid-utterance.
- Smallest AI's Telugu specifics (doc page 404).
- Soniox and Vapi pricing — `VERIFY`.

---

## 7. Minimum experiment to validate

**One Vapi assistant, three calls, ~35 minutes, ~$2–3.**

Configure a single assistant with `transcriber: { provider: "soniox", model: "stt-rt-v5", languages: [] }`. Place **three calls to our own +91 handset**, identical except for the TTS provider (ElevenLabs → Azure → Smallest AI, female Indian voice each).

Read the same **six-utterance script** into each call:

| # | Type | Purpose |
|---|---|---|
| 1–2 | Telugu only | Does Telugu transcribe at all, on telephony audio |
| 3–4 | English only | Baseline |
| 5 | Telugu→English mid-sentence | The FR-04 requirement |
| 6 | English→Telugu mid-sentence | Switch in the other direction |

Then read Vapi's call transcript and listen back to the recording.

**Pass bar:**
- Telugu utterances transcribed as Telugu — not dropped, not romanised mush
- **Both halves of utterances 5 and 6 survive** — this is the make-or-break line
- No manual per-language configuration needed
- TTS renders Telugu intelligibly and **does not change voice mid-sentence**
- p50 end-of-speech → first-audio latency recorded

**If it passes:** the architecture stands as designed, TTS winner is chosen, and Phase 0 continues to telephony (P0.2a/b/c).
**If STT fails:** try Google or Gladia in the same harness before touching Sarvam.
**If TTS is the failure:** it is the cheaper problem — three native options and Azure `multilingual-auto` remain untried.

This experiment doubles as P0.4 (orchestrator spike) if we add one dummy background tool call to the same assistant — worth doing, since it tests the mid-call trigger mechanism for free.

---

**Correction sources (2026-08-29, live API):** `GET /voice-library/azure?limit=1000` (781 voices) ·
`GET /voice-library/cartesia?limit=1000` (924 voices, 44 language codes) · `PATCH /assistant` 400
validator messages. Note the endpoint defaults to **100 results** — the first pass looked like
"Azure has no Telugu voices" purely because the list was alphabetical and stopped inside the A's.

**Sources:** [Vapi Soniox provider](https://docs.vapi.ai/providers/transcriber/soniox) · [Vapi docs index](https://docs.vapi.ai/llms.txt) · [Vapi custom transcriber](https://docs.vapi.ai/customization/custom-transcriber) · [Vapi multilingual guide](https://docs.vapi.ai/customization/multilingual) · [Deepgram models & languages](https://developers.deepgram.com/docs/models-languages-overview) · [Soniox Telugu STT](https://soniox.com/speech-to-text/telugu) · [Soniox platform](https://soniox.com/) · [Sarvam streaming TTS WebSocket](https://docs.sarvam.ai/api/api-guides-tutorials/text-to-speech/streaming-api/web-socket) · [Sarvam STT overview](https://docs.sarvam.ai/api-reference-docs/api-guides-tutorials/speech-to-text/overview) · [ElevenLabs Telugu](https://elevenlabs.io/text-to-speech/telugu)
