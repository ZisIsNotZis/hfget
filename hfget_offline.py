"""Test-only stand-in for `huggingface_hub`, used by `selftest.py`.

Not importable by the product path: hfget.py only enters this backend when it
is started with the explicit `--offline-fixtures STATE_JSON` flag, and it prints
a banner saying results are synthetic. Downloads are refused, so acceptance
evidence never touches weights.
"""
import json
from types import SimpleNamespace

STATE_FILE = ""  # set by hfget.py --offline-fixtures


class RequestException(Exception):
    pass


def _load():
    with open(STATE_FILE, "r", encoding="utf-8") as fh:
        return json.load(fh)


def _save(state):
    with open(STATE_FILE, "w", encoding="utf-8") as fh:
        json.dump(state, fh)


def reset(repos, state_file):
    global STATE_FILE
    STATE_FILE = state_file
    _save({"repos": repos, "blocked": [], "downloads": []})


def reset_downloads():
    state = _load()
    state["downloads"] = []
    _save(state)


def download_calls():
    return _load()["downloads"]


def list_models(search=None, num_parameters=None, full=False, limit=None):
    repos = []
    for raw in _load()["repos"]:
        repos.append(SimpleNamespace(
            id=raw["id"],
            pipeline_tag=raw["pipeline_tag"],
            card_data={"num_parameters": raw["num_parameters"]},
        ))
    return repos[: limit or None]


class HfApi:
    def model_info(self, repo_id):
        for raw in _load()["repos"]:
            if raw["id"] == repo_id:
                return SimpleNamespace(
                    id=repo_id,
                    pipeline_tag=raw["pipeline_tag"],
                    siblings=[SimpleNamespace(rfilename=s["rfilename"], size=s["size"])
                              for s in raw["siblings"]],
                )
        raise RequestException(f"offline: no such repo {repo_id}")


def hf_hub_download(repo_id=None, filename=None, **kwargs):
    state = _load()
    state["downloads"].append(f"{repo_id}:{filename}")
    _save(state)
    raise RequestException(f"offline: download refused for {repo_id}:{filename}")
