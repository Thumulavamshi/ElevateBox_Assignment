#!/usr/bin/env python3
"""Measure the classifier against the labelled set before a live call costs us.

    python backend/eval_classifier.py            rules only - no key, no cost
    python backend/eval_classifier.py --llm      full pipeline (needs a key)

The rules pass runs with no API key and no spend, so the deterministic overlay
that protects the 15-point row is regression-tested on every change.
"""

import argparse
import json
import os
import re
import sys
import time

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)

from app import classifier      # noqa: E402
from app.config import load_env  # noqa: E402

# Without this the harness only sees the shell environment, so a key sitting in
# .env reads as "not set" and the eval refuses to run for no visible reason.
ENV_FILE = load_env()

CASES_PATH = os.path.join(HERE, "eval", "classification_cases.json")

# Thresholds are OURS, not the evaluator's (docs/audit.md). At n~40 the
# confidence interval is roughly +/-11 points, so treat a near miss as noise and
# the pdf-sourced gate as the real signal.
PDF_GATE = 1.00       # every phrase the assignment publishes must be right
OVERALL_TARGET = 0.85
BARRIER_TARGET = 0.80


def load_cases():
    with open(CASES_PATH, encoding="utf-8") as fh:
        return json.load(fh)["cases"]


def run_rules(cases):
    """The deterministic overlay in isolation. No model, no key, no spend."""
    print("\nRULES OVERLAY  (no API key, no cost)")
    print("-" * 60)
    wrong = []
    for c in cases:
        got = classifier.forced_hot_reason(c["transcript"]) is not None
        want = c["rule_forces"]
        if got != want:
            wrong.append((c, got, want))
    total = len(cases)
    print(f"  {total - len(wrong)}/{total} cases agree with the expected rule behaviour")
    for c, got, want in wrong:
        verb = "FIRED but should not have" if got else "did NOT fire but should have"
        print(f"  [FAIL] {c['id']}  {verb}")
        print(f"         {c['transcript'].splitlines()[-1][:90]}")
    forced = [c for c in cases if c["rule_forces"]]
    print(f"\n  the overlay is meant to fire on {len(forced)}/{total} cases "
          f"({len(forced)/total:.0%}) - if that fraction climbs, it is getting too greedy")
    return not wrong


def run_llm(cases, provider=None):
    provider = provider or classifier.resolve_provider()
    ok, why = classifier.available(provider)
    if not ok:
        print(f"\nLLM PASS SKIPPED for {provider}: {why}")
        return None

    print(f"\nFULL PIPELINE  (model + overlay)  "
          f"provider={provider}  model={classifier.model_for(provider)}")
    print("-" * 60)
    label_hits, barrier_hits, barrier_total, pdf_hits, pdf_total = 0, 0, 0, 0, 0
    confusion, failures, by_lang = {}, [], {}

    # Gemini's free tier is 5 requests/minute/model (verified from a real 429:
    # quotaId GenerateRequestsPerMinutePerProjectPerModel-FreeTier, limit 5 -
    # NOT the 10-15 RPM third-party blogs claim). Without throttling, 34 of 44
    # cases fail on quota and the run is worthless.
    # Pace at 4/min, not 5. Running exactly at the limit means any jitter trips
    # it, and a first attempt at 12.0s gaps lost 36 of 44 cases to 429s.
    rpm = float(os.environ.get("EVAL_RPM", "4" if provider == "gemini" else "60"))
    gap = 60.0 / rpm if rpm > 0 else 0.0
    if gap:
        print(f"  throttled to {rpm:g} req/min ({gap:.1f}s apart) - "
              f"about {len(cases) * gap / 60:.0f} min for {len(cases)} cases\n")
    last = [0.0]
    ATTEMPTS = 4

    def throttled(transcript):
        """Paced, with retries for quota AND transient network loss.

        A previous run lost its last 19 cases to `getaddrinfo failed` - the
        machine's network dropped mid-run. A multi-minute eval has to survive
        that, or a blip silently invalidates the whole result.
        """
        for attempt in range(1, ATTEMPTS + 1):
            wait = gap - (time.time() - last[0])
            if wait > 0:
                time.sleep(wait)
            last[0] = time.time()
            try:
                return classifier.classify_transcript(transcript, provider=provider)
            except Exception as exc:
                msg = str(exc)
                if attempt == ATTEMPTS:
                    raise
                if "429" in msg or "RESOURCE_EXHAUSTED" in msg:
                    m = re.search(r"retry in ([\d.]+)s", msg) or re.search(r"'(\d+)s'", msg)
                    delay = float(m.group(1)) + 3 if m else 40.0
                elif any(s in msg for s in ("getaddrinfo", "Errno 11001", "Connection",
                                            "timeout", "Temporary failure")):
                    delay = 15.0 * attempt
                    print(f"       network blip, waiting {delay:.0f}s")
                else:
                    raise
                time.sleep(delay)

    for c in cases:
        try:
            read = throttled(c["transcript"])
        except Exception as exc:
            print(f"  [ERROR] {c['id']}: {str(exc)[:110]}")
            failures.append((c, None))
            continue

        correct = read.label == c["label"]
        label_hits += correct
        confusion[(c["label"], read.label)] = confusion.get((c["label"], read.label), 0) + 1
        if c["source"] == "pdf":
            pdf_total += 1
            pdf_hits += correct
        lang = c.get("lang", "en")
        by_lang[lang] = (by_lang.get(lang, (0, 0))[0] + correct,
                         by_lang.get(lang, (0, 0))[1] + 1)
        if c["label"] == "warm":
            barrier_total += 1
            barrier_hits += (read.barrier == c["barrier"])
        if not correct:
            failures.append((c, read))
        print(f"  {'ok  ' if correct else 'MISS'} {c['id']}  "
              f"want={c['label']:<4} got={read.label:<4} conf={read.confidence:.2f}"
              f"{'  barrier=' + read.barrier if read.label == 'warm' else ''}")

    n = len(cases)
    print("\n  " + "-" * 56)
    print(f"  overall label accuracy : {label_hits}/{n} = {label_hits/n:.0%}"
          f"   (target {OVERALL_TARGET:.0%})")
    if pdf_total:
        print(f"  assignment's own phrases: {pdf_hits}/{pdf_total} = {pdf_hits/pdf_total:.0%}"
              f"   (must be {PDF_GATE:.0%})")
    if barrier_total:
        print(f"  warm barrier accuracy  : {barrier_hits}/{barrier_total} = "
              f"{barrier_hits/barrier_total:.0%}   (target {BARRIER_TARGET:.0%})")

    # Reported separately because it is a different scored row (10 pts) and a
    # different failure mode: an aggregate dominated by 44 English cases would
    # hide a classifier that cannot read Telugu at all.
    if len(by_lang) > 1:
        print("\n  by language (the 10-pt row):")
        for lang in ("en", "hi", "te", "mixed"):
            if lang not in by_lang:
                continue
            hits, tot = by_lang[lang]
            print(f"    {lang:<6} {hits}/{tot} = {hits/tot:.0%}")

    print("\n  confusion (want -> got):")
    for want in classifier.LABELS:
        row = "  ".join(f"{got}:{confusion.get((want, got), 0)}" for got in classifier.LABELS)
        print(f"    {want:<5} {row}")

    if failures:
        print("\n  misses worth reading:")
        for c, read in failures[:6]:
            print(f"    {c['id']} want={c['label']} got={read.label if read else 'ERROR'}")
            print(f"      {c['transcript'].splitlines()[-1][:88]}")
            if read:
                print(f"      model said: {read.reasoning[:88]}")

    passed = (label_hits / n >= OVERALL_TARGET
              and (not pdf_total or pdf_hits == pdf_total)
              and (not barrier_total or barrier_hits / barrier_total >= BARRIER_TARGET))
    return passed


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--llm", action="store_true", help="also run the model pass")
    ap.add_argument("--provider", choices=sorted(classifier.PROVIDERS),
                    help="which provider to evaluate (default: whichever key is set)")
    args = ap.parse_args()

    cases = load_cases()
    counts = {}
    for c in cases:
        counts[c["label"]] = counts.get(c["label"], 0) + 1
    print(f"\n{len(cases)} labelled cases: "
          + ", ".join(f"{k}={v}" for k, v in sorted(counts.items()))
          + f"  ({sum(1 for c in cases if c['source'] == 'pdf')} from the assignment itself)")

    rules_ok = run_rules(cases)
    if not args.llm:
        print(f"\n  provider readiness   (credentials from: {ENV_FILE or 'shell env only'})")
        for name, st in classifier.providers_status().items():
            if name == "selected":
                continue
            print(f"    {name:<10} {'ready' if st['ready'] else 'not ready'}  "
                  f"({st['detail']})")
    llm_ok = run_llm(cases, args.provider) if args.llm else None

    print("\n" + "=" * 60)
    print(f"rules: {'PASS' if rules_ok else 'FAIL'}", end="")
    print(f"   llm: {'PASS' if llm_ok else 'FAIL' if llm_ok is False else 'not run'}")
    return 0 if rules_ok and llm_ok is not False else 1


if __name__ == "__main__":
    sys.exit(main())
