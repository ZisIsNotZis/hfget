"""Offline acceptance check for hfget's selection rules.

Runs the real CLI entry point (`hfget.py --dry-run --offline-fixtures ...`)
against synthetic repo fixtures. The fake backend is only reachable through
that explicit flag; it prints a banner and refuses downloads.

    python3 selftest.py

Exit code 0 means the selection promises hold on the fixtures below. No
network, no model weights, and no prep work: fixtures live in a temp dir.
"""
import os
import subprocess
import sys
import tempfile

import hfget_offline as fake

STATE = os.path.join(tempfile.mkdtemp(prefix="hfget-selftest-"), "offline-state.json")
REPO_ID = "synthetic/Tiny-Mistral-GGUF"
CHECK_COUNT = 0


def repo(files, repo_id=REPO_ID):
    """files: list of (rfilename, size). num_parameters is synthetic."""
    return {
        "id": repo_id,
        "pipeline_tag": "text-generation",
        "num_parameters": 7_000_000_000,
        "siblings": [{"rfilename": name, "size": size} for name, size in files],
    }


def case_partial_best_is_skipped():
    # gsq-rco (score 100) outranks iq4_nl (70+2) but only shard 1 of 2 exists.
    return repo([
        ("Tiny-Mistral-GSQ-RCO-00001-of-00002.gguf", 2_000_000_000),
        ("Tiny-Mistral-iq4_nl-00001-of-00002.gguf", 2_000_000_000),
        ("Tiny-Mistral-iq4_nl-00002-of-00002.gguf", 2_000_000_000),
        ("Tiny-Mistral-iq4_nl-mtp.gguf", 100_000_000),
        ("mmproj-Tiny-Mistral-f16.gguf", 120_000_000),
    ])


def case_duplicate_shard_is_skipped():
    # Shard 1 appears twice; that is not a complete two-shard set.
    return repo([
        ("Tiny-Mistral-ud-q4_k_xl-00001-of-00002.gguf", 2_000_000_000),
        ("Tiny-Mistral-ud-q4_k_xl-00001-of-00002.gguf", 2_000_000_000),
        ("Tiny-Mistral-q4_k_m.gguf", 4_000_000_000),
    ])


def case_mixed_totals_is_skipped():
    # 00001-of-00002 + 00002-of-00003: two different manifests, numbers 1..2
    # look contiguous but the set is not a whole. Must not be accepted.
    return repo([
        ("Tiny-Mistral-GSQ-RCO-00001-of-00002.gguf", 2_000_000_000),
        ("Tiny-Mistral-GSQ-RCO-00002-of-00003.gguf", 2_000_000_000),
        ("Tiny-Mistral-q5_k_m-00001-of-00002.gguf", 2_500_000_000),
        ("Tiny-Mistral-q5_k_m-00002-of-00002.gguf", 2_500_000_000),
    ])


def case_healthy_pick_is_unchanged():
    # No traps: the top-ranked complete set wins, shards in numeric order.
    return repo([
        ("Tiny-Mistral-GSQ-RCO-00001-of-00002.gguf", 2_000_000_000),
        ("Tiny-Mistral-GSQ-RCO-00002-of-00002.gguf", 2_000_000_000),
        ("Tiny-Mistral-q4_k_m.gguf", 4_000_000_000),
        ("mmproj-Tiny-Mistral-q8.gguf", 120_000_000),
    ])


def case_only_partial_available():
    # Nothing complete to fall back to: refuse the repo instead of half a model.
    return repo([("Tiny-Mistral-GSQ-RCO-00001-of-00002.gguf", 2_000_000_000)])


def case_last_shard_missing():
    # 1 and 2 of 3 exist: numbers are contiguous but the set stops early.
    return repo([
        ("Tiny-Mistral-GSQ-RCO-00001-of-00003.gguf", 1_500_000_000),
        ("Tiny-Mistral-GSQ-RCO-00002-of-00003.gguf", 1_500_000_000),
        ("Tiny-Mistral-ud-q4_k_xl.gguf", 4_000_000_000),
    ])


def case_median_cut_keeps_larger():
    # Two complete quantizations score the same; the smaller half is dropped.
    return repo([
        ("Tiny-Mistral-UD-Q4_K_S.gguf", 3_000_000_000),
        ("Tiny-Mistral-UD-Q4_K_M.gguf", 5_000_000_000),
    ])

def case_substring_name_is_not_companion():
    # 'mpt' appears inside a model name; that is a real quant, not a companion.
    return repo([("Tiny-Mistral-mpt-7b-q4_k_m.gguf", 4_000_000_000)])


CASES = [
    ("partial best is skipped",
     case_partial_best_is_skipped,
     ["Tiny-Mistral-iq4_nl-00001-of-00002.gguf",
      "Tiny-Mistral-iq4_nl-00002-of-00002.gguf",
      "Tiny-Mistral-iq4_nl-mtp.gguf",
      "mmproj-Tiny-Mistral-f16.gguf"],
     "1 shard(s) missing, 1 of 2 present"),
    ("duplicate shard is skipped",
     case_duplicate_shard_is_skipped,
     ["Tiny-Mistral-q4_k_m.gguf"],
     "1 duplicate shard(s), 1 distinct of 2"),
    ("mixed totals is skipped",
     case_mixed_totals_is_skipped,
     ["Tiny-Mistral-q5_k_m-00001-of-00002.gguf",
      "Tiny-Mistral-q5_k_m-00002-of-00002.gguf"],
     "shards mix different totals (of-00002, of-00003)"),
    ("healthy pick is unchanged",
     case_healthy_pick_is_unchanged,
     ["Tiny-Mistral-GSQ-RCO-00001-of-00002.gguf",
      "Tiny-Mistral-GSQ-RCO-00002-of-00002.gguf",
      "mmproj-Tiny-Mistral-q8.gguf"],
     None),
    ("only partial available is refused",
     case_only_partial_available,
     [],
     "no valid main GGUF quant"),
    ("last shard missing is skipped",
     case_last_shard_missing,
     ["Tiny-Mistral-ud-q4_k_xl.gguf"],
     "1 shard(s) missing, 2 of 3 present"),
    ("median cut keeps the larger of equal scores",
     case_median_cut_keeps_larger,
     ["Tiny-Mistral-UD-Q4_K_M.gguf"],
     None),
    ("substring name is not a companion",
     case_substring_name_is_not_companion,
     ["Tiny-Mistral-mpt-7b-q4_k_m.gguf"],
     None),
]


def parse_selected(stdout):
    files, inside = [], False
    for line in stdout.splitlines():
        if line.startswith("Files ("):
            inside = True
            continue
        if line.startswith("===="):
            inside = False
        elif inside and line.startswith("  - "):
            files.append(line[4:].replace(" [SHARD]", ""))
    return files


def check(name, ok, detail=""):
    global CHECK_COUNT
    CHECK_COUNT += 1
    print(f"[{'PASS' if ok else 'FAIL'}] {name}")
    if not ok and detail:
        print(detail)
    return [] if ok else [name]


def run_cli(state, repo_list):
    fake.reset(repo_list, state)
    return subprocess.run(
        [sys.executable, "hfget.py", "--dry-run", "--target", "1",
         "--offline-fixtures", state],
        capture_output=True, text=True,
    )


def main():
    failures = []

    for name, make_repo, expected, expect_reason in CASES:
        proc = run_cli(STATE, [make_repo()])
        selected = parse_selected(proc.stdout)
        detail = ""
        ok = selected == expected
        if not ok:
            detail += f"   expected files: {expected}\n   selected files: {selected}\n"
        if expect_reason and expect_reason not in proc.stdout:
            ok = False
            detail += f"   expected skip reason: {expect_reason}\n"
        if fake.download_calls():
            ok = False
            detail += "   dry-run attempted a download\n"
        if not ok:
            detail += proc.stdout[-1000:].rstrip() + "\n" + proc.stderr[-600:].rstrip()
        failures += check(name, ok, detail)
        for line in proc.stdout.splitlines():
            if "incomplete shard set" in line:
                print(f"   {line.strip()}")

    # The fake backend must be announced, never silent.
    proc = run_cli(STATE, [case_healthy_pick_is_unchanged()])
    failures += check("offline fixtures run is announced",
                      "OFFLINE FIXTURES" in proc.stdout)

    # Without the flag and without the real client, the CLI must fail loudly.
    env = dict(os.environ)
    env.pop("PYTHONPATH", None)
    proc = subprocess.run([sys.executable, "hfget.py", "--dry-run", "--target", "1"],
                          capture_output=True, text=True, env=env)
    failures += check("missing client fails loudly instead of faking",
                      proc.returncode == 2 and "refusing to query a fake backend" in proc.stderr,
                      f"   rc={proc.returncode}\n   stderr={proc.stderr.strip()}")

    print(f"\n{CHECK_COUNT - len(failures)}/{CHECK_COUNT} checks passed; "
          f"downloads attempted: {len(fake.download_calls())}")
    return 1 if failures else 0


if __name__ == "__main__":
    sys.exit(main())
