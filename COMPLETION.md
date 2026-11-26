# Completion

**Status:** Completed on 2026-11-26.

**Accepted scope:** Search public Hugging Face repositories, select complete GGUF quantization sets and their companion files, and show the files before any downloads are confirmed.

**Verification:** `python3 selftest.py` passed 10 checks from a clean copy on Python 3.9 and 3.14. The checks reject missing and duplicate shards and incompatible shard totals, exercise fallback and companion selection, and verify that a missing client is reported. With the real client installed, `python3 hfget.py --dry-run --target 1` selected a public repository and listed three files without creating a model cache.

**Limits:** The live acceptance used dry-run. No model weights were transferred.
