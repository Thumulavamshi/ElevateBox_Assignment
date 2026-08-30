# What works, what doesn't, what I'd build next

**What works.** It dials on its own and holds a real conversation in English, Hindi or
Telugu, staying in whichever language you answer in and handling code-mixed sentences.
Median turn latency 1.7 seconds, none over three. It runs discovery on all five topics,
reads Hot/Warm/Cold from indirect answers — 96% over a labelled set, 4/4 on the four
phrases in your brief — fires a WhatsApp mid-call on intent rather than at call end, books
callbacks from spoken time in all three languages and says the resolved time back, then
follows up quoting what you actually said.

**What doesn't.** WhatsApp goes through UltraMsg, an unofficial gateway — Meta business
verification and Twilio both dead-ended on KYC, so it was the only path to a working demo.
It sends reliably, but drives a linked account, not the Business API. Speech recognition
sometimes mis-reads the language on a very short opening reply. No dashboard; call state
is JSON.

**What I'd build next.** Move WhatsApp to the official Cloud API once verification clears.
Own the media stream instead of a managed orchestrator. Add decision-maker phrases to the
deterministic classifier layer: the model's only two misses were both someone saying
another person decides.

---

**Vamshidhar Thumula** · +91 8309942858
Live prototype · Repository · Architecture diagram attached
