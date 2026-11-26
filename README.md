<p align="center">
  <img src="assets/logo.svg" width="112" height="112" alt="hfget logo">
</p>

<p align="center">
  <a href="README.md">English</a> ·
  <a href="README.zh-CN.md">简体中文</a>
</p>

# hfget

**Completed.** Verified GGUF selection, including complete shard groups and the live dry-run path. [Verification and limits](COMPLETION.md).

**Find the GGUF quantization you actually want, then download it — shards, mmproj and companions included.**

*A single-file Python CLI that searches Hugging Face under a parameter budget, ranks quantizations with rules you control, and downloads the winners in parallel.*

## Quick start

Requires Python 3.9+.

```sh
git clone https://github.com/ZisIsNotZis/hfget.git
cd hfget
python3 -m venv .venv && . .venv/bin/activate
pip install huggingface_hub requests
```

Edit the constants at the top of [`hfget.py`](hfget.py) — search term, parameter limit, quantization preferences, retry settings — then preview before downloading:

```sh
python3 hfget.py --dry-run
python3 hfget.py
```

`python3 hfget.py --help` lists the available flags. Files land in the standard Hugging Face cache; the script itself does not choose a destination directory.

If the Hugging Face client is missing, hfget stops with an error saying so; it never falls back to fake data on its own.

> Downloads can be many gigabytes. Check the dry-run output and your free disk space first.

## What it can do now

- **Search within a budget.** Query Hugging Face for `gguf` models filtered by `MAX_PARAM_FILTER` (default `max:36B`) and collect up to `--target` usable results.
- **Rank by your taste.** Ordered regex rules prefer quant families such as `gsq-rco`, `ud`, `i-quant` and `q4`, with a bonus for size suffixes like `xxs` / `xs` / `xl`.
- **Handle shards, completely.** Splits named `*-00001-of-00005.gguf` are grouped, sorted numerically, and only accepted when the set is whole. A group with a missing shard, a gap at the end, a repeated shard number, or shards that disagree about `of-NNNNN` is skipped with a printed reason instead of being half-downloaded — the complete lower-ranked quantization is used instead.
- **Skip the small half.** Among equally-ranked candidates it keeps those larger than the median size, falling back to all of them when none survive.
- **Pick companion files.** Selects `mtp`, `dspark2` and `mmproj` files with configurable preferences, and avoids a standalone MTP file when one is already bundled into the main quantization. Companions never take the main-model slot away from a real quantization.
- **Preview one by one.** `--dry-run` prints every accepted repository and its file list, plus why any shard set was rejected, without downloading anything.
- **Download politely.** API retries with delay, a pause between repositories, a confirmation prompt, and a thread pool (`--max-concurrent`, default 4).

## Architecture

Everything lives in one file on purpose:

```
hfget.py
├── CONFIG        search term, quant rules, size/MTP/mmproj preferences, retries
├── Discovery     list_models → pipeline-tag filter → model_info (with retry)
├── Selection     group_shards → group_problem → score_main_quant → median-size cut → companions
└── Download      dry-run report, confirmation, ThreadPoolExecutor
```

There is no package, install step or hidden entry point: the constants and the script are the whole program. [`docs/project-status.md`](docs/project-status.md) records its scope and boundaries.

## How to develop

Change the constants in [`hfget.py`](hfget.py), then check selection behavior offline — no network, no weights, no setup:

```sh
python3 selftest.py
```

It runs the real CLI (`hfget.py --dry-run --offline-fixtures <temp state>`) against synthetic repositories and prints one `PASS`/`FAIL` line per promise, including the reject reasons for incomplete shard sets. `hfget_offline.py` is a test-only stand-in for `huggingface_hub`; it is reachable solely through that flag, announces itself, and refuses downloads.

For a live check, keep it bounded:

```sh
python3 hfget.py --dry-run --target 5 --debug
```

There is no build step and no CI. When experimenting, keep `--target` small and use `--dry-run` so you are not downloading weights to test selection logic.

The offline suite covers file selection and missing-client behavior. The live dry-run spot check requires a Hugging Face request.

## How to contribute

Issues and pull requests are welcome — see [`CONTRIBUTING.md`](CONTRIBUTING.md) for scope, how to check a change, and what a reviewable PR looks like.

## Roadmap

### Implemented

- Model discovery with parameter and pipeline-tag filters.
- Quantization scoring, size-suffix ranking and median-size filtering.
- Shard grouping, complete-set validation and explicit reject reasons.
- MTP, dspark2 and mmproj companion selection.
- Dry-run preview, retries and parallel downloads.
- Offline acceptance suite (`selftest.py`) covering the selection promises.
- Explicit, documented configuration in the script header.

### Planned

No active milestones. This is a closed personal utility: the current behavior is the finished product, and changes are considered only when Hugging Face's API or the author's workflow changes.

### Future vision

If the project reopens, the direction stays the same: turn "which GGUF should I download?" into one confident command. That would mean better explanations for why a file was chosen, safer pre-download size reporting, and configuration that does not require editing source — without growing into a package manager or a general-purpose downloader.

## License

[AGPL-3.0](LICENSE.md).
