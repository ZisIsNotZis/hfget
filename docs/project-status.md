# hfget project status

## Classification

Closed utility: a single Python script that discovers and downloads selected
GGUF quantizations (and companion `mmproj` files) from Hugging Face model
repositories.

## Status

Closed as a milestone (2026-09-29). This is a small personal helper; no further
development is planned unless the project's inputs or goals change.

## Evidence

- Implementation: [`../hfget.py`](../hfget.py).
- Behavior: ranks candidate main-model and `mmproj` files by configurable
  quantization preferences, then downloads the chosen files via
  `huggingface_hub`.
- Requirements: Python 3 plus `huggingface_hub` and `requests`.

## Boundaries

Search term, parameter filter, quantization preferences, and retry settings are
constants edited in-file before running. The script contacts the network and may
download very large files; it owns no CLI packaging, tests, or CI.
