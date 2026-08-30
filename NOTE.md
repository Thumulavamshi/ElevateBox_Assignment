# What works, what doesn't, what I'd build next

**What works.** It dials on its own and holds a real conversation in English, Hindi or
Telugu, staying in whichever language you answer in and handling code-mixed sentences.
Median turn latency 1.7 seconds, none over three. It runs discovery on all five topics,
reads Hot/Warm/Cold from indirect answers — 96% over 57 labelled cases, 4/4 on the four
phrases in your brief — fires a WhatsApp mid-call on intent rather than at call end, books
callbacks from spoken time in all three languages and says the resolved time back, then
follows up quoting what you actually said.

**What doesn't.** WhatsApp goes through UltraMsg, an unofficial gateway. Meta business
verification and Twilio both dead-ended on KYC, so this was the only path to a working
demo. It sends reliably, but it drives a linked account, not the Business API. The
cold-lead brochure and the warm callback-confirmation message are unbuilt. There is no
dashboard — call state is JSON.

**What I'd build next.** Move WhatsApp to the official Cloud API once verification clears.
Own the media stream instead of a managed orchestrator. Add decision-maker phrases to the
deterministic classifier layer: the model's only two misses were both someone saying
another person decides.

---

**Vamshidhar Thumula** · +91 8309942858
Live prototype · Repository · Architecture diagram attached
