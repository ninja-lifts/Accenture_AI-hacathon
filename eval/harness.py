"""Scenario harness. Runs every scenario in the injection manifest through the
real pipeline and scores the output against ground truth.

Runs in CI on every push. The scorecard it emits is committed, misses included -
a scorecard that only ever shows wins is not evidence, it is marketing.

Usage:
    python -m eval.harness --scenarios all --out eval/scorecard.md
    python -m eval.harness --scenarios SC-01,SC-08 --verbose

TODO(Phase 6).
"""

from __future__ import annotations

import argparse


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--scenarios", default="all")
    parser.add_argument("--out", default="eval/scorecard.md")
    parser.add_argument("--baseline", action="store_true",
                        help="Run the baselines instead of GlassBox (see eval/baselines/).")
    parser.add_argument("--verbose", action="store_true")
    args = parser.parse_args()
    raise NotImplementedError("Phase 6")


if __name__ == "__main__":
    main()
