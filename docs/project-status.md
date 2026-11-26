# hfget project status

## Classification

Closed utility: a single Python script that discovers and downloads selected
GGUF quantizations (and companion `mmproj` files) from Hugging Face model
repositories.

## Status

The current utility scope is [completed](../COMPLETION.md).

Selection rules reworked on 2026-11-26 after two acceptance failures were
found: a high-ranked two-shard quantization with only its first shard present
was selected, and shards from different manifests (`00001-of-00002` next to
`00002-of-00003`) were treated as one complete set.

Current behavior: a shard group is accepted only when it is whole — every
shard number from 1 to the declared total, no duplicates, and consistent
`of-NNNNN` totals across the group. Incomplete groups are skipped with a
printed reason, so a complete lower-ranked quantization is used instead. If
nothing complete exists, the repository is refused rather than half-downloaded.
Companion files (`mtp` / `mmproj` / `dspark2`) no longer compete for the
main-model slot.

## Evidence

- Implementation: [`../hfget.py`](../hfget.py).
- Offline acceptance: `python3 selftest.py` — 10 checks through the real CLI
  against synthetic fixtures, no network, no downloads. Runs from a clean
  checkout with no setup. Covers incomplete shard sets (missing shard, gap at
  the end, duplicate number, disagreeing totals), fallback to a complete
  lower-ranked quant, refusal when nothing is complete, median-size cut,
  companion-vs-substring naming, the fixture banner, and the loud failure when
  the Hugging Face client is missing.
- Live spot check: `hfget.py --dry-run --target 1` against Hugging Face,
  printed one public repository and its 3 files, downloaded nothing.
  This is a spot check of the network path, not a regression suite.
- Requirements: Python 3.9+, `huggingface_hub` and `requests` for real use.
  Without them the CLI exits with an error; it never substitutes fake data.

## Boundaries

Search term, parameter filter, quantization preferences, and retry settings are
constants edited in-file before running. The script contacts the network and may
download very large files. `hfget_offline.py` is a test-only stand-in reachable
only through `--offline-fixtures`; it is not a shipping backend. There is no
package, config file format, or CI.

## Next uncertainty

Whether real repositories routinely ship shards whose `of-NNNNN` totals
disagree. The rule is deliberately strict (skip rather than guess), so a
frequent real-world occurrence would show up as repos being refused, and the
skip lines in `--dry-run` are where to look for it.
