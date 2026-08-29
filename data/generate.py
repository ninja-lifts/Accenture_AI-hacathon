"""Synthetic data generator for Meridian Electronics.

Seeded and deterministic: same seed -> byte-identical dataset -> reproducible
evaluation. The seed and the resulting file hashes are recorded in
data/injection_manifest.yaml.

Design rules that keep the benchmark honest (see docs/05_DATA_STRATEGY.md §4):

  1. Effects are RAMPS, not clean steps. A perfect step is trivially detectable
     and makes difference-in-differences unfalsifiable.
  2. Planted causes have PARTIAL SPILLOVER into neighbouring segments, so
     "control" segments are not perfectly clean. Without this, the parallel-
     trends assumption is constructed rather than tested.
  3. The pre-period is CONTAMINATED with unrelated small movements.
  4. At least one scenario has a CONFOUNDED RIVAL cause co-timed with the true
     one. The engine must demote it, not pick it.
  5. Negative controls exist and are not marked in the data in any way the
     engine could exploit.

TODO(Phase 1).
"""

from __future__ import annotations

import argparse


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--seed", type=int, default=20260829)
    parser.add_argument("--out", default="data/generated")
    parser.add_argument("--manifest", default="data/injection_manifest.yaml")
    args = parser.parse_args()
    raise NotImplementedError("Phase 1")


if __name__ == "__main__":
    main()
