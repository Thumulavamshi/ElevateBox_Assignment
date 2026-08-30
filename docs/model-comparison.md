# Classification model comparison

Which LLM runs the Hot/Warm/Cold lane (15 points). Researched 2026-08-28 against vendor
documentation.

> **The eval did not run against any model.** There is no `ANTHROPIC_API_KEY`, no `GEMINI_API_KEY`,
> and neither SDK is installed. You asked me not to purchase credits or add keys, so everything
> below on *accuracy* is a prior, not a measurement. The 44-case harness is ready and
> provider-agnostic; one command produces real numbers the moment a key exists.

---

## 1. What is actually available

**Gemini Flash** (verified from Google's model list):

| Model | ID | Status |
|---|---|---|
| Gemini 3.7 Flash | `gemini-3.7-flash` | **Stable, newest** |
| Gemini 3.6 Flash | `gemini-3.6-flash` | Stable |
| Gemini 3.5 Flash | `gemini-3.5-flash` | Stable |
| Gemini 3 Flash | `gemini-3-flash-preview` | Preview |
| Gemini 2.5 Flash | `gemini-2.5-flash` | Stable |

**You asked specifically about Gemini 3.5 Flash. It exists, but it is two generations behind and
costs *twice as much* on the paid tier** ($1.50/$9.00 per 1M tokens) as 3.6 and 3.7 Flash
($0.75/$3.75 through Dec 2026). There is no reason to pick it over 3.7 Flash.

**Claude** (from the current model table):

| Model | ID | Input $/1M | Output $/1M |
|---|---|---|---|
| Opus 5 | `claude-opus-5` | $5.00 | $25.00 |
| Sonnet 5 | `claude-sonnet-5` | $2.00 | $10.00 |
| Haiku 4.5 | `claude-haiku-4-5` | $1.00 | $5.00 |

---

## 2. Gemini free tier — verified and unverified

**Verified from Google's pricing page:** Gemini 3.7, 3.6, 3.5 and 2.5 Flash are all **free of charge**
on the free tier for input and output.

**Verified, and the finding that actually matters:** on the free tier, *"Content used to improve our
products: **Yes**"*. On paid tiers it is **No**.

That is a real consideration for this project. The live call is a stranger's actual business
conversation — what they sell, their budget, their timeline. Running it through a tier that trains
on the content is a choice, not an accident, and *"why did you send your evaluator's call data to a
free training tier?"* is a bad question to face in the round that follows.

**NOT verified:** Google's rate-limit documentation **no longer publishes free-tier numbers** — it
says limits "can be viewed in Google AI Studio" and vary by tier. Third-party blogs claim roughly
**10–15 RPM, 250,000 TPM, 250–1,500 RPD** for Flash models. Treat those as `VERIFY`; check
<https://aistudio.google.com/rate-limit> against your own key.

If those figures are roughly right, they are comfortably sufficient here:

| Our load | Requirement |
|---|---|
| One eval run (44 cases) | ~44 requests → ~4½ min at 10 RPM |
| One live call | ~8 classifications over ~4 min → **~2 RPM** |
| A day of rehearsal (10 calls + 3 evals) | ~215 requests |

Rate limits are not the deciding factor. The training clause is.

---

## 3. Structured output

Both support it, and our `LeadRead` Pydantic schema works with each unchanged:

- **Claude** — `client.messages.parse(..., output_format=LeadRead)` returns a validated
  `response.parsed_output`. Validation is done by the SDK.
- **Gemini** — `response_format={"type": "text", "mime_type": "application/json", "schema":
  LeadRead.model_json_schema()}`, then parse `interaction.output_text`. Supported schema features
  cover everything we use (string, number, enum, description, required, additionalProperties).
  Google notes "not all JSON Schema features are supported" and that very large or deeply nested
  schemas may be rejected — ours is five flat fields, so this is not a risk.

Verdict: **no meaningful difference for our schema.**

---

## 4. Comparison

Accuracy and adversarial-handling columns are **priors, not measurements**.

| | Gemini 3.7 Flash | Claude Haiku 4.5 | Claude Sonnet 5 | Claude Opus 5 |
|---|---|---|---|---|
| Classification accuracy | unmeasured | unmeasured | unmeasured | unmeasured |
| Indirect / adversarial intent | likely good; frontier-class Flash | good | strong | strongest |
| Structured output | schema-based, adequate | SDK-validated | SDK-validated | SDK-validated |
| Latency (off speech path) | Flash tier, fastest class | very fast | fast | slowest |
| Noisy phone transcripts | untested | untested | untested | untested |
| API reliability | mature | mature | mature | mature |
| Free tier | **yes, all Flash models** | none | none | none |
| Data used for training | **yes on free tier**, no on paid | no | no | no |
| **Cost, this whole project** | **$0** (free) / ~$0.75 paid | **~$1** | **~$2** | **~$5** |

### The cost number is the surprise

Estimating from real call data (~8 classifications per call, transcript growing to ~1,500 input
tokens, ~200 output), **50 rehearsal calls plus a dozen eval runs**:

| Provider | Estimated total for the entire project |
|---|---|
| Gemini free tier | **$0** |
| Gemini 3.7 Flash (paid) | ~$0.75 |
| Claude Haiku 4.5 | ~$1 |
| Claude Sonnet 5 | ~$2 |
| Claude Opus 5 | ~$5 |

**This lane costs between nothing and five dollars, total.** The question was framed as "can Gemini
replace Anthropic at effectively zero cost" — the honest answer is that the cost difference across
every option here is smaller than one test call's telephony spend. **Choose on accuracy and data
policy. Price is noise at this scale.**

(Anthropic's minimum credit purchase is typically $5, so the practical floor is $5 regardless.)

---

## 5. Recommendation

**Use `gemini-3.7-flash` on the free tier, starting now.**

Reasons, in order:

1. **It costs nothing to get the evidence.** We have been recommending things without measuring
   them; a free tier removes the last excuse. Run the 44 cases, get a confusion matrix.
2. It is the newest stable Flash, not the 3.5 you asked about — same free tier, better model, and
   half the paid price if we ever leave the free tier.
3. Structured output covers our schema exactly.
4. Free-tier limits exceed our load by a wide margin (~2 RPM during a live call).

**Then decide on evidence:**

- **If it clears the gate** (100% on the assignment's four phrases, ≥85% overall, ≥80% on
  barriers) → keep it, but **move to a paid Gemini key before the evaluator call** so the training
  clause does not apply to a stranger's conversation. That costs under a dollar.
- **If it fails** → buy the $5 Anthropic minimum and re-run with `claude-haiku-4-5`, then
  `claude-sonnet-5`. Both are one config change; no code moves.

**Do not buy Anthropic credit yet.** There is no evidence we need it, and getting that evidence is
free.

---

## 6. Switching providers

The classifier is provider-agnostic. Schema, system prompt and the deterministic rules overlay are
shared; only the transport differs.

```bash
pip install -U google-genai
export GEMINI_API_KEY=...
python backend/eval_classifier.py --llm
```

Provider resolution: `CLASSIFIER_PROVIDER` if set, else whichever key is present, else anthropic.
`CLASSIFIER_MODEL` overrides the model. `/health` reports readiness for every provider, and
`eval_classifier.py --provider {anthropic,gemini}` forces one for a head-to-head.

The rules overlay needs no key at all and stays at **44/44** regardless of which model is chosen.

---

**Sources:** [Gemini models](https://ai.google.dev/gemini-api/docs/models) ·
[Gemini pricing](https://ai.google.dev/gemini-api/docs/pricing) ·
[Gemini rate limits](https://ai.google.dev/gemini-api/docs/rate-limits) ·
[Gemini structured output](https://ai.google.dev/gemini-api/docs/structured-output) ·
[Gemini quickstart](https://ai.google.dev/gemini-api/docs/quickstart)
