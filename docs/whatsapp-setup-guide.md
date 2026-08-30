# WhatsApp Cloud API — setup walkthrough

Everything you do in Meta's dashboards, and the specific options to pick. Meta renames things
often, so where a label may have shifted I describe what the step *does* as well as what it is
called.

**Time:** about 45–60 minutes, plus template approval (usually minutes).
**Cost:** nothing to set up.

---

## Before you start — the one thing that trips people up

**You need a phone number that does NOT have WhatsApp on it.**

Once a number becomes a Cloud API sender it can no longer be used in the normal WhatsApp or
WhatsApp Business app. If the number already has an account, you must delete that account first
(WhatsApp → Settings → Account → Delete my account) and wait a few minutes.

- **Do not use your personal number.** It becomes the business sender permanently, and your personal
  number is also the one going in the message body as "call me back on".
- A spare SIM, a second number, or a landline that can receive a voice call all work.
- You only need to receive **one** SMS or voice call on it, during verification.

---

## Step 1 — Meta Business portfolio

Go to **business.facebook.com**.

Create a business portfolio if you do not have one. Name it something real (your own name is fine).
You will be asked for a business email — use one you can access.

**You do NOT need Business Verification.** Unverified portfolios can message **250 unique recipients
per 24 hours**. We need one. Skip any prompt pushing you to verify — it takes days and buys us
nothing.

---

## Step 2 — Create a developer app

Go to **developers.facebook.com** → *My Apps* → *Create App*.

| Prompt | Choose |
|---|---|
| What do you want your app to do / use case | **Other** |
| App type | **Business** |
| Business portfolio | the one from Step 1 |

Name it something recognisable, e.g. `elevatebox-voice-agent`.

---

## Step 3 — Add the WhatsApp product

On the app dashboard, find **WhatsApp** in the product list and click *Set up*.

It will create or ask you to link a **WhatsApp Business Account (WABA)**. Let it create one.

You now land on the **API Setup** page. This page has most of what I need. Leave it open.

---

## Step 4 — Add your real sender number

The API Setup page starts you on a **Meta test number**. **Do not use it** — the test number can
only message up to five recipients who each verify themselves with a code, which is impossible for
the evaluator's number.

Click **Add phone number** and register the number from "Before you start".

- Display name: your name or business name (Meta reviews this; keep it honest, no "Official" or
  emoji, or it gets rejected)
- Category: pick the closest, e.g. *Professional Services*
- Verify by SMS or voice call

When it shows as **Connected**, you are done with this step.

---

## Step 5 — Collect three of the four values I need

Back on **API Setup**, with your real number selected in the dropdown:

| What | Where |
|---|---|
| **Phone number ID** | Shown directly under the number. A long numeric string — **not** the phone number itself |
| **WhatsApp Business Account ID** | Shown on the same page, usually just below |
| **Sender number** | The number you registered, in `+91...` form |

---

## Step 6 — The permanent access token (do not skip this)

The token shown on API Setup is **temporary and expires in 24 hours.** If we use it, the demo dies
mid-week. You need a System User token instead, which does not expire.

In **business.facebook.com** → *Settings* (gear icon) → **Users → System Users**:

1. **Add** → name it e.g. `elevatebox-sender` → role **Admin**
2. On the new system user, click **Assign assets**
   - Asset type: **WhatsApp Accounts**
   - Select your WABA
   - Permission: **Full control** (or at minimum *Manage*)
3. Click **Generate new token**
   - App: the app from Step 2
   - Token expiration: **Never**
   - Permissions — tick exactly these two:
     - `whatsapp_business_messaging`
     - `whatsapp_business_management`
4. **Copy the token now.** It is shown once and never again.

That token is the fourth value I need.

---

## Step 6b — Webhooks: SKIP for now

The setup flow asks for a **Callback URL** and **Verify token**. You do not need either yet.

Webhooks are strictly for **receiving** - inbound messages and delivery/read receipts. Sending is a
plain outbound POST to Meta's API and needs nothing hosted. Skip this card and carry on.

Two things to note for when we come back to it:

**Meta's own warning on that screen matters:** *"Apps will only be able to receive test webhooks
while the app is unpublished."* So even once the URL is configured, real delivery receipts will not
flow until the app is published. That is the thing that eventually forces publishing - not sending.

**Generate your verify token now while you are here.** It is just a random string you invent; Meta
echoes it back once to prove the endpoint is yours. Any long random value works:

```
python -c "import secrets; print(secrets.token_urlsafe(32))"
```

Put it in `.env` as `WHATSAPP_VERIFY_TOKEN=` and we will paste the same value into Meta when the
backend is deployed. Callback URL will be `https://<our-host>/whatsapp/webhook`.

**Unverified:** whether *sending* to an arbitrary number requires the app to be published is not
stated in Meta's docs and third-party sources conflict. It is 30 seconds to test once you have
credentials - we send to your own number and find out. If it is blocked, publishing needs a privacy
policy URL, so have one ready as a contingency.

---

## Step 7 — Submit templates 1 and 2

**business.facebook.com** → *WhatsApp Manager* → **Message Templates** → *Create template*.

Bodies, sample values and headers are in [`whatsapp-templates.md`](whatsapp-templates.md).

For each:

| Field | Choose |
|---|---|
| Category | **Utility** |
| Name | exactly as in the templates doc (lowercase, underscores) |
| Language | **English** — pick one variant and use the same for both |
| Header | Template 1: **None**. Template 2: **Media → Image** |
| Body | paste from the doc |
| Footer / Buttons | leave empty |

**Before pasting, replace `Vamshidhar Thumula, +91 XXXXXXXXXX` with your real name and mobile
number.** That text is static and gets baked into the approved template — changing it later needs
re-approval.

For Template 2 you will be asked to upload a **sample image** for the header. Upload your
architecture diagram (or any placeholder image if it is not drawn yet — the sample is only for
review, the real image is chosen per-message at send time).

Meta will ask for **sample values** for each `{{n}}`. Use the realistic ones in the doc, not `test`
or `xxx` — vague samples are a documented rejection cause.

Submit both. Status goes *Pending* → *Approved*, usually within minutes.

**Template 3 comes later**, once we have deployed and know the URLs.

---

## Step 8 — Host two files

Meta's servers fetch header media by URL, so both must be publicly reachable **direct file links**.

- Your **résumé** as PDF
- Your **architecture diagram** as an image (hand-drawn on paper and photographed is explicitly fine
  per the assignment)

Google Drive and Dropbox *share* links do **not** work — they return a preview page, not the file.
Options that do: a GitHub repo raw URL, GitHub Releases, Cloudflare R2, or any static host.

Easiest: commit both to the repo and use the `raw.githubusercontent.com` URL.

---

## What to send me

Put these in `experiments/voice-feasibility/.env` — **not in chat**:

```
WHATSAPP_PHONE_NUMBER_ID=
WHATSAPP_BUSINESS_ACCOUNT_ID=
WHATSAPP_ACCESS_TOKEN=
WHATSAPP_SENDER_NUMBER=+91...
WHATSAPP_RESUME_URL=
WHATSAPP_ARCHITECTURE_IMAGE_URL=
YOUR_MOBILE_NUMBER=+91...
```

And tell me in chat (no secrets in these):
- the exact **template names** as approved, and their **status**
- whether Meta kept them as **Utility** or moved them to **Marketing**
- your real **pricing** so I can replace the `EDIT ME` placeholders in `agent/prompt.md`

---

## Things that will waste your time if nobody warns you

| Symptom | Cause |
|---|---|
| Cannot register the number | It still has a WhatsApp account. Delete it in the app first. |
| Token works today, 401 tomorrow | You used the temporary API Setup token. Redo Step 6. |
| Template rejected: display name | Display names with "Official", emoji, or a mismatch with your business get rejected |
| Template rejected: too promotional | Ours are written to avoid it; if it happens, shorten rather than rewrite |
| Message never arrives, no error | You are still on the Meta **test number**. It only reaches pre-verified test recipients. |
| Header image fails at send | The URL is a share page, not a direct file link |

---

## What I still cannot do until we deploy

**Delivery receipts and window detection need a webhook**, which needs a public HTTPS URL. Until the
backend is deployed, sending works but we cannot automatically prove *when* a message was delivered.

That matters because the mid-call row is scored on the message arriving **before the call ends**, and
the delivery timestamp is our evidence. So the deploy step is not optional polish — it is what makes
the 15-point row provable.

I will build the sender to work without the webhook, and wire receipts when we deploy.
