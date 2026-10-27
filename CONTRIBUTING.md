# Contributing to hfget

## Scope

hfget is deliberately one readable script, [`hfget.py`](hfget.py), plus its configuration constants at the top. Changes that fit:

- selection rules (quant scoring, size priority, shard grouping, companion files);
- resilience against Hugging Face API changes (retries, filters, response handling);
- clearer dry-run output and safer download behavior.

Changes that do not fit: turning the script into a package, adding a config file format, a plugin system, a GUI, or a general-purpose downloader. Open an issue first if you are unsure — a short discussion is cheaper than a rejected PR.

## Checking a change

There is no build step and no test suite. Verify behavior against the live Hugging Face API with a bounded dry run, which downloads nothing:

```sh
python3 -m venv .venv && . .venv/bin/activate
pip install huggingface_hub requests
python3 hfget.py --dry-run --target 5 --debug
```

Keep `--target` small. State in the PR what the selection produced before and after your change, and paste the relevant `DEBUG` lines — that output is the evidence a reviewer needs.

## Pull requests

- One concern per PR, with a message in Conventional Commit style (`fix: ...`, `feat: ...`, `docs: ...`).
- Never commit downloaded weights or caches; `.gguf` files and the usual Python artifacts are already ignored.
- If a change depends on new Hugging Face API behavior, describe the observed response (status, JSON shape) in the issue or PR.

## Issues

Include the command you ran, the repository id involved, and the debug output for that repository. Reports of a wrong pick are most useful with the file list from `--dry-run`, since the selection rules are the thing being judged.
