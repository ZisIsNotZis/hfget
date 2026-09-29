# hfget

> **Status: closed (milestone, 2026-09-29).** A complete small personal utility
> for fetching HF GGUF quantizations. No further development is planned unless
> the project's inputs or goals change.

A Python helper for discovering and downloading selected GGUF quantizations from Hugging Face model repositories. It ranks candidate main-model files and companion `mmproj` files using configurable quantization preferences, then downloads the chosen files with the Hugging Face Hub client.

## Requirements

Python 3 and the `huggingface_hub` and `requests` packages.

## Configuration and use

The search term, parameter filter, quantization preferences, and retry settings are constants near the top of [`hfget.py`](hfget.py). Review and adjust these values for your needs before running:

```sh
python3 hfget.py --help
```

The script contacts Hugging Face and downloads model files, which can be very large. Confirm the selected repository and available disk space before downloading. See [`docs/project-status.md`](docs/project-status.md).