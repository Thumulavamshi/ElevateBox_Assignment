#!/usr/bin/env python3
"""Measure the callback time resolver against a frozen clock.

    python backend/eval_timeparse.py            all cases
    python backend/eval_timeparse.py -v         also print what the agent says back

No API key, no network, no spend - the resolver is deterministic on purpose, so
the 10-point row can be regression-tested on every change instead of hoped at.

The clock is frozen at **Thursday 27 August 2026, 14:00 IST**. Every expectation
below is relative to that instant, which is the only way "next Monday" has a
right answer at all.

Cases marked `vague` are the ones the scorecard singles out ("including vague
phrasing"): the phrase does not name a time, so OUR convention resolves it. Those
conventions are ours, not the evaluator's - what makes them safe is that the
agent speaks the result back for correction.
"""

import argparse
import os
import sys
from datetime import datetime

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)

# The Windows console defaults to cp1252, which cannot print Devanagari or
# Telugu - the eval would die on its own test data rather than on a failure.
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

from app import timeparse            # noqa: E402
from app.db import IST               # noqa: E402

NOW = datetime(2026, 8, 27, 14, 0, tzinfo=IST)      # a Thursday

# (phrase, expected "YYYY-MM-DD HH:MM" IST or None, vague?)
CASES = [
    # --- the assignment's own example, and its neighbours
    ("call me back tomorrow morning",        "2026-08-28 10:00", True),
    ("tomorrow evening",                     "2026-08-28 18:00", True),
    ("tomorrow afternoon",                   "2026-08-28 15:00", True),
    ("call me tomorrow",                     "2026-08-28 10:00", True),
    ("day after tomorrow",                   "2026-08-29 10:00", True),

    # --- explicit clock times
    ("call me at 5 pm",                      "2026-08-27 17:00", False),
    ("give me a call at 9 am tomorrow",      "2026-08-28 09:00", False),
    ("tomorrow at 4:30 pm",                  "2026-08-28 16:30", False),
    ("around 11 tomorrow",                   "2026-08-28 11:00", False),
    ("6 o'clock",                            "2026-08-27 18:00", False),
    ("half past four",                       "2026-08-27 16:30", False),
    ("monday 4 pm",                          "2026-08-31 16:00", False),

    # --- bare hours, read for business hours
    ("call me at 5",                         "2026-08-27 17:00", False),
    ("at 11",                                "2026-08-28 11:00", False),   # 11am has passed
    ("today at 3",                           "2026-08-27 15:00", False),

    # --- "after N" -> N:30, because they said after
    ("call me after 6",                      "2026-08-27 18:30", False),
    ("after 7 pm",                           "2026-08-27 19:30", False),

    # --- weekdays
    ("next monday",                          "2026-08-31 10:00", True),
    ("monday",                               "2026-08-31 10:00", True),
    ("friday afternoon",                     "2026-08-28 15:00", True),
    ("saturday morning",                     "2026-08-29 10:00", True),
    ("on thursday",                          "2026-09-03 10:00", True),    # today -> a week

    # --- vague windows, resolved by our stated conventions
    ("sometime next week",                   "2026-08-31 10:00", True),
    ("next week tuesday",                    "2026-09-01 10:00", True),
    ("this evening",                         "2026-08-27 18:00", True),
    ("tonight",                              "2026-08-27 20:00", True),

    # --- relative offsets
    ("in an hour",                           "2026-08-27 15:00", False),
    ("in half an hour",                      "2026-08-27 14:30", False),
    ("in 30 minutes",                        "2026-08-27 14:30", False),
    ("in two hours",                         "2026-08-27 16:00", False),
    ("call me back in 3 days",               "2026-08-30 10:00", True),
    # From a real call: "after 5 minutes" booked 17:30 because the o'clock
    # branch matched "after 5" and discarded the unit. "after 5" alone must
    # still mean 5pm, so both readings need to survive side by side.
    ("after 5 minutes",                      "2026-08-27 14:05", False),
    ("just after 5 minutes",                 "2026-08-27 14:05", False),
    ("can you call me again in 5 minutes",   "2026-08-27 14:05", False),
    ("after an hour",                        "2026-08-27 15:00", False),

    # --- explicit dates
    ("september 3",                          "2026-09-03 10:00", True),

    # --- Hindi, script and romanised
    ("kal subah",                            "2026-08-28 10:00", True),
    ("कल सुबह",                               "2026-08-28 10:00", True),
    ("kal shaam ko call karna",              "2026-08-28 18:00", True),
    ("परसों",                                 "2026-08-29 10:00", True),
    ("aaj shaam",                            "2026-08-27 18:00", True),

    # --- Telugu, script and romanised
    ("repu udayam",                          "2026-08-28 10:00", True),
    ("రేపు ఉదయం",                             "2026-08-28 10:00", True),
    ("repu sayantram call cheyandi",         "2026-08-28 18:00", True),
    ("ఎల్లుండి",                                "2026-08-29 10:00", True),

    # --- FROM A REAL CALL, 29 Aug. Every one of these was wrong in production.
    #     "कल दो बजे" resolved to the 10:00 default because neither the Hindi
    #     number nor "बजे" (o'clock) was known, so a callback was booked four
    #     hours from what the lead asked for - and the agent said it aloud.
    ("कल दो बजे",                             "2026-08-28 14:00", False),
    ("कल शाम 8 बजे",                          "2026-08-28 20:00", False),
    ("कल सुबह 10 बजे",                        "2026-08-28 10:00", False),
    ("कल शाम के आसपास",                       "2026-08-28 18:00", True),
    ("repu 4 gantalaku",                     "2026-08-28 16:00", False),
    ("రేపు 2 గంటలకు",                          "2026-08-28 14:00", False),

    # --- must NOT resolve. The agent has to ask again rather than invent a time,
    #     and a stray number in an ordinary sentence must never book a callback.
    ("call me back later",                   None, False),
    ("whenever suits you",                   None, False),
    ("I have about 200 products",            None, False),
    ("around 120 designs",                   None, False),
    ("my budget is 50000",                   None, False),
    ("",                                     None, False),
]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("-v", "--verbose", action="store_true")
    args = ap.parse_args()

    print(f"\nCALLBACK TIME RESOLVER  (frozen clock: {NOW:%A %d %B %Y, %H:%M} IST)")
    print("-" * 70)

    failures, vague_total, vague_ok = [], 0, 0
    for phrase, expected, is_vague in CASES:
        got = timeparse.resolve(phrase, now=NOW)
        actual = f"{got.when_ist:%Y-%m-%d %H:%M}" if got else None
        ok = actual == expected
        if is_vague:
            vague_total += 1
            vague_ok += int(ok)
        if not ok:
            failures.append((phrase, expected, actual))
            print(f"  [FAIL] {phrase!r}")
            print(f"         expected {expected}, got {actual}"
                  f"{' via ' + got.rule if got else ''}")
        elif args.verbose:
            said = f'  ->  "{got.spoken()}"' if got else "  ->  (asks again)"
            print(f"  [ok]   {phrase!r:<40} {actual or '-'}{said}")

    total = len(CASES)
    passed = total - len(failures)
    print("-" * 70)
    print(f"  {passed}/{total} phrasings resolved correctly")
    print(f"  {vague_ok}/{vague_total} of them vague - the case the scorecard "
          f"calls out by name")
    print(f"  {sum(1 for _, e, _ in CASES if e is None)} cases must NOT resolve "
          f"(the agent asks again rather than inventing a time)")

    print("\n" + "=" * 70)
    print("resolver: " + ("PASS" if not failures else f"FAIL ({len(failures)})"))
    return 0 if not failures else 1


if __name__ == "__main__":
    sys.exit(main())
