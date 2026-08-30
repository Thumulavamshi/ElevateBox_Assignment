#!/usr/bin/env python3
"""Measure slot extraction against the REAL call transcripts we already have.

    python backend/eval_extraction.py         integrity only - no key, no cost
    python backend/eval_extraction.py --llm   run the extractor for real

The audit (docs/audit.md Finding I) called the classification eval circular: we
wrote the cases, we set the bar, we graded ourselves. Extraction has a way out of
that, and it is the reason this harness exists.

**The integrity check needs no labels.** "Is this quote actually in the
transcript, on a line the LEAD spoke?" has an objective answer that nobody on
this project gets to influence. It is also the exact property the assignment
scores - "the follow up quotes something specific I said" - and the exact one a
language model quietly breaks by tidying up wording it was told to copy.

So the pass bar here is: **every stored quote is verbatim, on every transcript,
every time.** Slot *values* still need a human to read the table it prints; that
part is judgement and is presented, not scored.

Input is `agent/transcripts/*.json` - six real Soniox calls, noise and all.
"""

import argparse
import glob
import json
import os
import sys
import time

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)

from app import extraction      # noqa: E402
from app.config import load_env  # noqa: E402

ENV_FILE = load_env()

TRANSCRIPT_DIR = os.path.join(os.path.dirname(HERE), "agent", "transcripts")


def load_transcripts():
    """Real calls, as (name, transcript_text, turns) - the shape db.py produces."""
    out = []
    for path in sorted(glob.glob(os.path.join(TRANSCRIPT_DIR, "*.json"))):
        with open(path, encoding="utf-8") as fh:
            data = json.load(fh)
        messages = (data.get("artifact") or {}).get("messages") or []
        turns, seq = [], 0
        for m in messages:
            role = m.get("role")
            if role not in ("user", "bot", "assistant"):
                continue          # skips the system prompt message
            text = (m.get("message") or "").strip()
            if not text:
                continue
            turns.append({"seq": seq, "role": "user" if role == "user" else "assistant",
                          "text": text})
            seq += 1
        if not any(t["role"] == "user" for t in turns):
            continue              # a call nobody answered has nothing to extract
        transcript = "\n".join(f"{t['role']}: {t['text']}" for t in turns)
        out.append((os.path.basename(path)[:8], transcript, turns))
    return out


def check_integrity(name, turns, found):
    """The zero-label check. Returns (failures, quoted_count, filled_count).

    Runs the same `merge` the live lane runs, then re-verifies its output from
    scratch: anything that survived as a quote must appear, character for
    character modulo whitespace, in a line the lead actually spoke.
    """
    lead = extraction.lead_turns(turns)
    failures, quoted, filled = [], 0, 0

    for slot_name in extraction.SLOT_NAMES:
        change = extraction.merge({}, slot_name, getattr(found, slot_name), turns)
        if not change:
            continue
        filled += 1
        quote = change["raw_quote"]
        if quote is None:
            continue
        quoted += 1
        norm = extraction.normalise(quote)
        if not any(norm in extraction.normalise(text) for _, text in lead):
            failures.append((slot_name, quote))
        elif change["source_turn_seq"] is None:
            failures.append((slot_name, f"no source turn recorded for {quote!r}"))
    return failures, quoted, filled


def show(name, found, turns):
    print(f"\n  {name}")
    for slot_name in extraction.SLOT_NAMES:
        slot = getattr(found, slot_name)
        value = (slot.value or "").strip()
        if not value:
            print(f"    {slot_name:<15} -")
            continue
        change = extraction.merge({}, slot_name, slot, turns)
        quote = (change or {}).get("raw_quote")
        seq = (change or {}).get("source_turn_seq")
        mark = f'"{quote}" (turn {seq})' if quote else "[no verifiable quote]"
        print(f"    {slot_name:<15} {value}")
        print(f"    {'':<15} {mark}")


def run_offline(calls):
    """No model. Proves the verifier itself rejects what it should."""
    print("\nVERIFIER SELF-CHECK  (no API key, no cost)")
    print("-" * 60)
    ok = True
    for name, _, turns in calls:
        lead = extraction.lead_turns(turns)
        if not lead:
            continue
        seq, text = lead[0]
        # A real span of the lead's speech must verify.
        got_q, got_seq = extraction.attach_quote(text[:40], "", turns)
        if got_q is None or got_seq != seq:
            print(f"  [FAIL] {name}: a real lead phrase failed to verify")
            ok = False
        # Words nobody said must not.
        if extraction.attach_quote("we will pay you fifty lakhs today", "", turns)[0]:
            print(f"  [FAIL] {name}: invented text was accepted as a quote")
            ok = False
        # The agent's own words must not verify as the lead's.
        agent = [t["text"] for t in turns if t["role"] == "assistant"]
        if agent and extraction.attach_quote(agent[0][:40], "", turns)[0]:
            print(f"  [FAIL] {name}: the agent's words were accepted as the lead's")
            ok = False
    print(f"  {len(calls)} transcripts, verifier {'behaves' if ok else 'IS BROKEN'}")
    return ok


def run_llm(calls):
    ok, why = extraction.available()
    if not ok:
        print(f"\nLLM PASS SKIPPED: {why}")
        return None

    print(f"\nEXTRACTION  ({why})")
    print("-" * 60)
    all_failures, latencies, totals = [], [], [0, 0]
    for name, transcript, turns in calls:
        start = time.time()
        try:
            found = extraction.extract_from_transcript(transcript)
        except Exception as exc:
            print(f"  [FAIL] {name}: {exc}")
            all_failures.append((name, "extraction raised", str(exc)))
            continue
        latencies.append(time.time() - start)
        failures, quoted, filled = check_integrity(name, turns, found)
        totals[0] += quoted
        totals[1] += filled
        show(name, found, turns)
        for slot_name, detail in failures:
            print(f"    [FAIL] {slot_name}: quote is not in the lead's words - {detail}")
            all_failures.append((name, slot_name, detail))

    print("\n" + "-" * 60)
    if latencies:
        latencies.sort()
        print(f"  latency  median {latencies[len(latencies)//2]:.1f}s  "
              f"max {latencies[-1]:.1f}s   (off the speech path)")
    print(f"  slots filled {totals[1]}, of which {totals[0]} carry a verified quote")
    print(f"  quote integrity: {len(all_failures)} violation(s)")
    return not all_failures


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--llm", action="store_true", help="run the real extractor (costs money)")
    args = ap.parse_args()

    calls = load_transcripts()
    print(f"{len(calls)} real call transcripts from agent/transcripts/")
    if ENV_FILE:
        print(f"credentials from: {ENV_FILE}")

    offline_ok = run_offline(calls)
    llm_ok = run_llm(calls) if args.llm else None

    print("\n" + "=" * 60)
    verdict = "PASS" if offline_ok else "FAIL"
    llm_verdict = "not run" if llm_ok is None else ("PASS" if llm_ok else "FAIL")
    print(f"verifier: {verdict}   extraction: {llm_verdict}")
    if not args.llm:
        print("run with --llm to measure the real extractor against these calls")
    return 0 if offline_ok and llm_ok is not False else 1


if __name__ == "__main__":
    sys.exit(main())
