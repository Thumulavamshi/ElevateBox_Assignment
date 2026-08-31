"""Structured extraction - turning what the lead said into the five slots.

The assignment names them: "Budget, what I sell, how many products, timeline,
features I need." Reading them back is what separates a follow-up that quotes
the person from "a template with my name pasted in", which the PDF calls out by
name as the failure mode.

Two properties this module exists to guarantee:

**Nothing is invented.** A slot the lead never spoke about stays empty. The
handlers already have honest fallbacks ("the budget you mentioned"); a wrong
specific is far worse than a vague true one, because the evaluator knows what
they said.

**Every quote is really theirs.** A model asked for a verbatim quote will
happily tidy it up, and a tidied quote is not a quote. `attach_quote` checks the
words back against the transcript and refuses anything it cannot find. That
check needs no API key and no labels, which makes it the one part of extraction
quality we can measure without grading our own homework.

Runs in the understanding lane, never on the speech path.
"""

import logging
import re

from pydantic import BaseModel, Field

from . import classifier

log = logging.getLogger("elevatebox.extraction")

# The five the assignment names, in the order a real call tends to reveal them.
# This tuple stays exactly five: it drives discovery `coverage()` and the evals,
# and the assignment scores those five topics specifically.
SLOT_NAMES = ("products", "catalogue_size", "timeline", "features", "budget")

# Extracted and stored like a slot, but NOT part of discovery coverage - not
# knowing someone's name is not a gap in qualifying them. It exists so the
# follow-up can open "Hi Ravi" instead of "Hi", which is the difference between
# a message written to a person and one written to a record.
EXTRA_SLOT_NAMES = ("contact_name",)
ALL_SLOT_NAMES = SLOT_NAMES + EXTRA_SLOT_NAMES


class Slot(BaseModel):
    """One extracted field. Empty value means the lead has not said."""

    value: str = Field(
        description="A short, plain summary of what the lead said for this "
                    "field - a few words, not a sentence. Empty string if they "
                    "have not said anything about it yet."
    )
    quote: str = Field(
        description="The lead's own words that carry this fact, copied "
                    "character-for-character from one of the 'user:' lines. Do "
                    "not tidy the wording, fix the grammar or join two lines. "
                    "Empty string if there is nothing to quote."
    )
    confidence: float = Field(description="0.0 to 1.0, how sure you are.")


class ExtractedSlots(BaseModel):
    products: Slot = Field(description="What the lead sells.")
    catalogue_size: Slot = Field(description="Roughly how many products they carry.")
    timeline: Slot = Field(description="When they want the store live.")
    features: Slot = Field(description="Features they said they need.")
    budget: Slot = Field(description="What they are willing to spend.")
    contact_name: Slot = Field(
        description="The lead's own first name, ONLY if they clearly said it. "
                    "Empty if unsure, garbled, or never given.")


SYSTEM_PROMPT = """\
You pull structured facts out of a live sales-call transcript. The business \
sells custom e-commerce websites to small Indian businesses.

Extract these, and only from what the LEAD said. Lines beginning "user:" \
are the lead. Lines beginning "assistant:" are our own salesperson - never \
extract from those, even when the salesperson repeats a number back.

  products        what they sell
  catalogue_size  roughly how many products they carry
  timeline        when they want the store live
  features        the features they said they need
  budget          what they are willing to spend
  contact_name    the lead's own first name, if they clearly gave it

Rules:

- If the lead has not said anything about a field, leave value and quote as \
empty strings and set confidence to 0. Never guess, never infer from what the \
salesperson suggested, and never carry a number over from a different field.
- value is short and plain: "custom-made t-shirts", "300 to 1000", "one month", \
"cash on delivery, order tracking", "70,000 to 1.5 lakh". Not a sentence.
- quote is the lead's own words, copied exactly from a single "user:" line, \
including any transcription mess. Do not clean it up, do not fix punctuation, \
do not stitch two lines together. If no single line carries the fact, leave \
quote empty and still fill value.
- The transcript comes from live speech recognition, so it contains "uh", \
broken sentences, replacement characters and mis-heard words. Read through the \
noise for value; preserve it exactly in quote.
- **The lead may speak English, Hindi or Telugu, in native script or romanised, \
and will often mix English words into a Hindi or Telugu sentence.** Understand \
all of it. Indian number words count: "ek lakh", "ఒక లక్ష" and "one lakh" are the \
same budget; "do sau" and "200" are the same catalogue size.
- **value is always written in English**, because it goes into an English \
follow-up message: "one lakh", "custom-made sarees", "within a month". \
**quote stays in the lead's own language and script, exactly as they said it.** \
Translating the quote destroys the one thing it is for.
- A number the lead gives in reply to a question about one field belongs to \
that field. "3 to 2. 100." after a question about how many products is a \
catalogue size, not a budget.
- If the lead asks US for a price rather than naming one, budget stays empty. \
Being asked "give me a range" is not a stated budget.
- contact_name is the lead's OWN first name and nothing else. Not our \
salesperson's name, not a brand, not a shop name, not a relative they mention. \
Leave it empty unless they plainly gave it - a mis-heard name used back at \
someone is worse than using no name at all. Write it capitalised and alone: \
"Ravi", not "ravi garu" and not "My name is Ravi".\
"""

USER_TEMPLATE = "Transcript so far:\n\n{transcript}\n\nExtract the five fields."


# --- quote verification ----------------------------------------------------
#
# Pure functions below this line. No API key, no network - so the eval harness
# and the smoke test can exercise the part most likely to be quietly wrong.

# Soniox emits U+FFFD where it is unsure, and spacing around it is unstable.
_NOISE = re.compile(r"[�​]+")
# Punctuation is stripped by listing it, not by negating \w. Python's \w excludes
# Unicode combining marks, so `[^\w\s]` silently deletes the vowel signs out of
# every Hindi and Telugu word - it turned "ఎల్లుండి" into "ఎల ల డ". Symmetric
# mangling still matched here, but it would quietly weaken quote verification the
# moment the transcriber stops being English-only. Same bug bit timeparse.py.
_PUNCT = re.compile(r"[!\"#$%&'()*+,\-./:;<=>?@\[\\\]^_`{|}~।॥]+")
_SPACES = re.compile(r"\s+")


def normalise(text):
    """Loose form for comparison: case, punctuation and spacing all forgiven.

    Deliberately generous. We are asking "did they say this", not "did the model
    reproduce the punctuation" - and the punctuation in a Soniox transcript is
    not the lead's anyway.
    """
    text = _NOISE.sub(" ", str(text or ""))
    text = _PUNCT.sub(" ", text)
    return _SPACES.sub(" ", text).strip().lower()


def lead_turns(turns):
    """[(seq, text)] for the lead only. The agent's words are never evidence."""
    return [(t["seq"], t["text"]) for t in turns if t.get("role") == "user"]


def attach_quote(quote, value, turns):
    """Tie a quote to a real lead turn. Returns (quote, source_seq).

    Three outcomes, in descending order of tightness:

    1. The model's quote is genuinely in one of the lead's turns -> keep it.
    2. It is not, but the extracted value is -> quote that whole turn instead.
       Less tight, still literally the lead's words, and it keeps provenance.
    3. Neither -> no quote at all. The value survives on its own and the
       handlers fall back to phrasing that does not claim to quote anyone.

    Never returns words the lead did not say, which is the entire point.
    """
    candidates = lead_turns(turns)
    if not candidates:
        return None, None

    norm_quote = normalise(quote)
    if norm_quote:
        for seq, text in candidates:
            if norm_quote in normalise(text):
                return str(quote).strip(), seq

    norm_value = normalise(value)
    if norm_value:
        for seq, text in candidates:
            if norm_value in normalise(text):
                log.info("quote %r not found in the transcript; falling back to "
                         "turn %s verbatim", (quote or "")[:60], seq)
                return text.strip(), seq

    log.info("dropping unverifiable quote %r", (quote or "")[:60])
    return None, None


def merge(existing, name, slot, turns):
    """Decide what to store for one slot. Returns a dict of columns, or None.

    Returns None - meaning leave the row alone - when the model found nothing
    this pass. It sees the whole transcript every time, so a later pass is
    better informed than an earlier one; but an EMPTY later pass means "not
    mentioned again", not "retract what they said". Forgetting a fact the lead
    stated once would be worse than being one turn stale.
    """
    value = (slot.value or "").strip()
    if not value:
        return None

    quote, source_seq = attach_quote(slot.quote, value, turns)
    prior = existing.get(name) or {}
    if prior.get("value") == value and (prior.get("raw_quote") or None) == quote:
        return None  # nothing changed; do not churn updated_at

    return {
        "value": value,
        "raw_quote": quote,
        "source_turn_seq": source_seq,
        "confidence": slot.confidence,
    }


# --- the model call --------------------------------------------------------

def available(provider=None):
    """Extraction rides the classifier's provider. One key, one config."""
    return classifier.available(provider)


def extract_from_transcript(transcript, provider=None):
    """Run the model over a transcript. Returns ExtractedSlots. Blocking.

    max_tokens is higher than the classifier's because five quotes from a noisy
    transcript are simply more output than one label and one quote.
    """
    return classifier.run_structured(
        SYSTEM_PROMPT,
        USER_TEMPLATE.format(transcript=transcript),
        ExtractedSlots,
        provider=provider,
        max_tokens=2000,
    )
