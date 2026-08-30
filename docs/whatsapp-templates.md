# WhatsApp template drafts — for submission to Meta

Copy-paste ready. Three templates, designed against the verified constraints and against
Section 06's four required elements.

## Where every required item lives  ← read this first

The résumé and the architecture diagram are **not in the message text**. They are **header media** -
a separate field on the template, above the body. That is why you cannot find them by reading the
bodies below.

| Section 06 requirement | Which message | Where exactly |
|---|---|---|
| 1. The context of our call | **Template 2** | Body, variables `{{1}}`-`{{5}}` |
| 2. Proper framing of that context | **Template 2** | Body, the fixed prose around the variables |
| 3. Your mobile number | **Template 2** | Body, **static text** (not a variable) |
| 4. **An image of how you built it** | **Template 2** | **IMAGE HEADER** ← the architecture diagram |
| "Your resume goes with it" | **Template 3** | **DOCUMENT HEADER** ← the résumé PDF |
| Working prototype URL | **Template 3** | Body `{{1}}` |
| Repository link | **Template 3** | Body `{{2}}` |
| Under-200-word note | **Template 3** | Body `{{3}}`, as a link (too long for a body) |
| Mid-call message | **Template 1** | Body, no media (kept fast on purpose) |

**Template 2 alone satisfies all four Section 06 requirements**, because the image rides in its
header. Template 3 exists only because WhatsApp allows **one** media attachment per message - the
diagram and the résumé physically cannot travel together.

### What a header actually is

In Meta's template builder, above the body, there is a **Header** dropdown:

- Template 1 → **None**
- Template 2 → **Media → Image**
- Template 3 → **Media → Document**

When you pick Media it asks you to **upload a sample file**. That sample is only for Meta's review -
it is not what gets sent. At send time our code supplies the real file by URL:

```
WHATSAPP_ARCHITECTURE_IMAGE_URL   -> Template 2's image header
WHATSAPP_RESUME_URL               -> Template 3's document header
```

Both are still empty in `.env`. **Until they are set, Template 2 sends with no diagram** (the handler
logs a warning saying a required Section 06 element is missing) and **Template 3 refuses to send at
all**, because claiming "my resume is attached" with nothing attached would be a lie.

---

## Constraints these are designed around

| Rule | Consequence |
|---|---|
| Body max **1024 characters total**, including filled variables | Recap must be tight; the under-200-word note cannot fit in a body |
| Variables cannot contain **newlines, tabs, or 4+ consecutive spaces** | Variables are short phrases; all line breaks live in the **fixed** text |
| Fixed body text **may** contain newlines | This is what lets the message read like a person wrote it, not a log file |
| **One media header per message** | The architecture image and the résumé cannot ride on the same message — hence two post-call templates |
| Rejections: too promotional 38%, **vague variables 18%**, missing opt-out 24% | No sales language; variables kept narrow and semantic; nothing that reads as a broadcast |
| ~6 seconds minimum between messages to the same recipient | The post-call pair must be spaced |

## Two decisions worth knowing

**The mobile number and sender name are STATIC text, not variables.** Section 06 requires the number
"clearly visible, so I can call you back without hunting for it." Making it static means it cannot be
broken by a bad variable value, and it removes two variables from the vague-variable rejection risk.

**The mid-call template has no media header.** Meta must fetch header media before delivering, which
adds latency. That row is scored on the message arriving *while we are still talking*, so the
mid-call message is text-only and therefore the fastest thing we can send.

---

## Template 1 — `elevatebox_call_recap_now`

**The 15-point row.** Fires during the call, on high intent.

- **Category:** Utility
- **Language:** English
- **Header:** **NONE** - no media, deliberately (speed)
- **Footer:** none

**Body:**
```
Hi — sending this across while we are still on the call, as promised.

What I have so far: {{1}}, budget around {{2}}, and you want it live {{3}}.

I will send the full details and the architecture right after we hang up.

— Vamshidhar Thumula, +91 XXXXXXXXXX
```

**Sample values for submission:**
- `{{1}}` → `custom t-shirts, around 50 designs`
- `{{2}}` → `one lakh`
- `{{3}}` → `within a month`

*(Replace `Vamshidhar Thumula, +91 XXXXXXXXXX` with your real name and number before submitting — it is static text, so it is baked into the approved template.)*

---

## Template 2 — `elevatebox_followup_context_2`

**The main Section 06 message.** Carries requirement 1 (context), 2 (framing), 3 (number) and
4 (the architecture image) in a single message.

- **Category:** Utility
- **Language:** English
- **Header:** **MEDIA -> IMAGE = YOUR ARCHITECTURE DIAGRAM**
  Sent from `WHATSAPP_ARCHITECTURE_IMAGE_URL`. This is Section 06 requirement 4.
- **Footer:** none

**Body:**
```
Thanks for your time on the call just now — good to hear about {{1}}.

Recapping so I have it right: you are looking at {{2}}, you want it live {{3}}, and the features that matter are {{4}}. On budget you said "{{5}}".

The image above is how I built the system that just called you — dial, discovery, reading intent, and the WhatsApp firing mid-call.

If I have any of that wrong, just tell me. Easiest is to call me back on +91 XXXXXXXXXX.

— Vamshidhar Thumula
```

**Sample values for submission:**
- `{{1}}` → `the custom clothing business`
- `{{2}}` → `around 50 to 100 designs`
- `{{3}}` → `within a month`
- `{{4}}` → `payments, delivery tracking and WhatsApp orders`
- `{{5}}` → `around 1,000 to 2,000 US dollars`

**Why `{{5}}` is a verbatim quote:** the assignment's impress-us list includes *"the follow up quotes
something specific I said."* This slot exists to carry the lead's own words, not a paraphrase.

**Character budget:** fixed text ≈ 430, variables ≈ 150 → ≈ 580 of 1024. Comfortable headroom for a
longer feature list.

---

## Template 3 — `elevatebox_resume_delivery`

Carries the résumé, and the remaining send-list items.

- **Category:** Utility
- **Language:** English
- **Header:** **MEDIA -> DOCUMENT = YOUR RESUME PDF**
  Sent from `WHATSAPP_RESUME_URL`, filename shown to the recipient as the PDF name.
- **Footer:** none

**Body:**
```
My resume is attached.

Live prototype, calls you on demand: {{1}}
Repository: {{2}}
Short note on what works, what does not, and what I would build next: {{3}}

— Vamshidhar Thumula, +91 XXXXXXXXXX
```

**Sample values for submission:**
- `{{1}}` → `https://elevatebox-demo.onrender.com`
- `{{2}}` → `https://github.com/username/elevatebox-voice-agent`
- `{{3}}` → `https://github.com/username/elevatebox-voice-agent/blob/main/NOTE.md`

**Submit this one last.** The three URLs are only known once we deploy. Once they are known,
**make them static text instead of variables** — static URLs are far less likely to be flagged as
vague variables, and these never change.

**The under-200-word note cannot go in the body.** 200 words is roughly 1,200 characters, over the
1,024 limit, and variables cannot contain line breaks. It goes as a link — or as free-form text if
the window is open (below).

---

## The free-form path — opportunistic ONLY, never solicited

If a customer-service window happens to be open (the recipient messaged us at some point in the last
24 hours), we can send free-form: any length, real formatting, images and PDFs, no template.

**We never ask for that, and it is never depended on.** Asking a lead to reply so a window opens
would defeat the assignment - the brief is a system that calls "on its own", and a pipeline that
needs a human to warm up each lead before the machine can message them is not autonomous. It also
would not survive contact with a real lead list.

So the rule in code is:

1. **Template is the design.** It must work cold, to someone who has never messaged us. Every scored
   requirement is satisfied by the template path alone.
2. If a window is *already* open, use free-form because the content is genuinely better.
3. The agent never mentions WhatsApp replies on the call, and nothing prompts the recipient to write
   back. Window state is observed, never engineered.

In a real inbound pipeline windows are open often, so this is worth having - but it is an upgrade on
a path that already works, not a path.

Free-form version of the post-call message (no 1024 limit, real formatting):

```
Thanks for your time just now — good to hear about the custom clothing business.

Recapping so I have it right:
• Around 50 to 100 t-shirt designs
• Live within a month
• Payments, delivery tracking and WhatsApp orders
• Budget: "around 1,000 to 2,000 US dollars"

Attached is the architecture of the system that just called you — dial, discovery,
intent classification, and the WhatsApp firing while we were still talking.

Also attached: my resume.
Live prototype: <url>
Repo: <url>

What works / what doesn't / what I'd build next:
<the under-200-word note, inline>

Call me back any time on +91 XXXXXXXXXX.
— Vamshidhar Thumula
```

---

## Submission order

1. **Templates 1 and 2 now.** They need no URLs, and they carry the 15-point mid-call row plus all
   four Section 06 elements. Approval is usually minutes.
2. **Template 3 after deploy**, with static URLs.

## If a template is rejected

The two likely causes and their fixes:

- **"Too promotional"** — remove anything that reads like selling. These drafts avoid it already;
  if rejected, cut the feature list from `{{4}}` and shorten.
- **"Vague variable"** — the fix is narrower slots and better sample values, not fewer words. Make
  sure the samples you submit are realistic, not `test` or `xxx`.

Meta may auto-recategorise Utility → Marketing. That is not a rejection; it costs slightly more per
conversation and is otherwise fine for our volume of one recipient.
