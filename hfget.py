#!/usr/bin/env python3
import re
import argparse
import time
import statistics
from typing import List, Optional, Dict, Tuple
from huggingface_hub import list_models, hf_hub_download, HfApi
from requests.exceptions import RequestException

# -------------------------- CONFIG --------------------------
MAX_PARAM_FILTER = "max:36B"
SEARCH_TERM = "gguf"
QUANT_RULES = [
    ("gsq-rco", re.compile(r"gsq[-_]rco", re.IGNORECASE), 100),
    ("ud", re.compile(r"ud", re.IGNORECASE), 90),
    ("_p", re.compile(r"p(?!\w)", re.IGNORECASE), 80),
    ("i-quant", re.compile(r"iq\d", re.IGNORECASE), 70),
    ("q4", re.compile(r"q4", re.IGNORECASE), 60),
]
SIZE_PRIORITY = {
    "xxs": 5,
    "xs": 4,
    "x": 3,
    "nl": 2,
    "xl": 1,
}
MTP_PREFER = "q4"
DSPARK2_PREFER = "q4"
MMPROJ_PRIORITY = {"q8": 10, "bf16": 9, "fp16": 8}
REQUIRE_MAIN_QUANT = True
ALLOWED_PIPELINE_TAGS = {"text-generation", "image-text-to-text", None}
API_RETRY_COUNT = 2
API_RETRY_DELAY = 1.0
API_INTER_REPO_DELAY = 0.4
# -------------------------------------------------------------
api = HfApi()
SHARD_PATTERN = re.compile(r"(.*)-(\d{5})-of-(\d{5})\.gguf", re.IGNORECASE)

def score_main_quant(filename: str) -> tuple[int, str]:
    fn = filename.lower()
    quant_score = 0
    matched_tag = ""
    for tag, rx, s in QUANT_RULES:
        if rx.search(fn):
            quant_score = s
            matched_tag = tag
            break
    size_bonus = 0
    for sz, b in SIZE_PRIORITY.items():
        if sz in fn:
            size_bonus = b
            break
    total = quant_score + size_bonus
    return total, matched_tag

def group_shards(siblings) -> List[dict]:
    shard_groups: Dict[str, dict] = {}
    single_gguf = []
    for f in siblings:
        rn = f.rfilename
        m = SHARD_PATTERN.match(rn)
        if m:
            prefix, idx_str, total_str = m.groups()
            prefix_key = prefix.lower()
            if prefix_key not in shard_groups:
                shard_groups[prefix_key] = {
                    "prefix": prefix,
                    "files": [],
                    "total_shards": int(total_str),
                    "sum_size": 0,
                }
            shard_groups[prefix_key]["files"].append(f)
            shard_groups[prefix_key]["sum_size"] += f.size if f.size is not None else 0
        elif rn.lower().endswith(".gguf"):
            single_gguf.append(f)
    # sort shard files numerically
    groups_out = []
    for g in shard_groups.values():
        g["files"].sort(key=lambda ff: int(SHARD_PATTERN.match(ff.rfilename).groups()[1]))
        groups_out.append(g)
    # convert single gguf into singleton group
    for f in single_gguf:
        groups_out.append({
            "prefix": f.rfilename,
            "files": [f],
            "total_shards": 1,
            "sum_size": f.size if f.size is not None else 0,
        })
    return groups_out

def select_best_main_quant(siblings) -> List[str]:
    groups = group_shards(siblings)
    scored_groups = []
    for g in groups:
        sample_name = g["files"][0].rfilename
        score, tag = score_main_quant(sample_name)
        sum_sz = g["sum_size"] if g["sum_size"] is not None else 0
        scored_groups.append((score, sum_sz, g))
    if not scored_groups:
        return []
    max_score = max(item[0] for item in scored_groups)
    top_group_list = [item for item in scored_groups if item[0] == max_score]

    sizes = [x[1] for x in top_group_list]
    median_size = statistics.median(sizes)

    final_selected_groups = [item for item in top_group_list if item[1] > median_size]
    if not final_selected_groups:
        final_selected_groups = top_group_list

    out_filenames = []
    for _, _, g in final_selected_groups:
        for f in g["files"]:
            out_filenames.append(f.rfilename)
    return out_filenames

def select_file_by_pref(files: List[str], prefix: str, prefer: str) -> Optional[str]:
    candidates = [f for f in files if prefix.lower() in f.lower()]
    if not candidates:
        return None
    for f in candidates:
        if prefer.lower() in f.lower():
            return f
    return candidates[0]

def select_mmproj(files: List[str]) -> Optional[str]:
    proj_files = [f for f in files if "mmproj" in f.lower()]
    scored = []
    for f in proj_files:
        fn = f.lower()
        sc = 0
        for tag, s in MMPROJ_PRIORITY.items():
            if tag in fn:
                sc = s
                break
        scored.append((sc, f))
    if not scored:
        return None
    scored.sort(reverse=True)
    return scored[0][1]

def get_model_info_with_retry(repo_id: str):
    for attempt in range(API_RETRY_COUNT + 1):
        try:
            return api.model_info(repo_id)
        except RequestException as e:
            if attempt >= API_RETRY_COUNT:
                raise
            print(f"Retry {attempt+1}/{API_RETRY_COUNT} for {repo_id}, err: {e}")
            time.sleep(API_RETRY_DELAY)

def fetch_model_candidates(target_count: int, dry_run: bool, debug: bool = False) -> List[dict]:
    candidates = []
    print(f"Searching HF models: search={SEARCH_TERM}, num_parameters={MAX_PARAM_FILTER}, api_limit={target_count}")
    models_iter = list_models(
        search=SEARCH_TERM,
        num_parameters=MAX_PARAM_FILTER,
        full=False,
        limit=target_count
    )

    for idx, m in enumerate(models_iter):
        repo_id = m.id
        print(f"\nRaw result {idx+1}: {repo_id}, pipeline_tag={m.pipeline_tag}")
        if m.pipeline_tag not in ALLOWED_PIPELINE_TAGS:
            print(f"Skip {repo_id}: pipeline_tag disallowed")
            continue
        time.sleep(API_INTER_REPO_DELAY)
        try:
            info = get_model_info_with_retry(repo_id)
            siblings = info.siblings
            filenames = [f.rfilename for f in siblings]
        except Exception as e:
            print(f"Skip {repo_id}: failed fetch siblings, err: {e}")
            continue

        main_set = select_best_main_quant(siblings)

        # MTP rule: any main file contains mtp → skip standalone mtp
        has_combined_mtp = any("mtp" in fname.lower() for fname in main_set)
        if has_combined_mtp:
            mtp = None
        else:
            mtp = select_file_by_pref(filenames, "mtp", MTP_PREFER)

        dspark2 = select_file_by_pref(filenames, "dspark2", DSPARK2_PREFER)
        mmproj = select_mmproj(filenames)

        if debug:
            print(f"DEBUG | {repo_id} -> main_set={main_set}, mtp={mtp}, dspark2={dspark2}, mmproj={mmproj}")

        if REQUIRE_MAIN_QUANT and len(main_set) == 0:
            print(f"Skip {repo_id}: no valid main GGUF quant")
            continue
        if not any([main_set, mtp, dspark2, mmproj]):
            continue

        params_raw = m.card_data.get("num_parameters") if m.card_data else None
        entry = {
            "repo": repo_id,
            "params_raw": params_raw,
            "main_quant_files": main_set,
            "mtp": mtp,
            "dspark2": dspark2,
            "mmproj": mmproj,
        }
        candidates.append(entry)

        # Dry run one-by-one print
        if dry_run:
            if params_raw and str(params_raw).isnumeric():
                p_display = f"{float(params_raw)/1e9:.2f}B"
            else:
                p_display = "unknown"
            all_download = []
            all_download.extend(entry["main_quant_files"])
            if entry["mtp"]: all_download.append(entry["mtp"])
            if entry["dspark2"]: all_download.append(entry["dspark2"])
            if entry["mmproj"]: all_download.append(entry["mmproj"])

            print("\n==== DRY RUN | ACCEPTED MODEL ====")
            print(f"Repo: {repo_id} | Params: {p_display}")
            print(f"Files ({len(all_download)}):")
            for fname in all_download:
                if SHARD_PATTERN.match(fname):
                    print(f"  - {fname} [SHARD]")
                else:
                    print(f"  - {fname}")
            print("==================================\n")

        if len(candidates) >= target_count:
            print(f"\nReached target {target_count} valid models, stop scanning.")
            break

    # Safe sort key: None param maps to 0.0
    def param_sort_key(item):
        p = item["params_raw"]
        try:
            return float(p)/1e9
        except (ValueError, TypeError):
            return 0.0
    candidates.sort(key=param_sort_key, reverse=True)
    candidates = candidates[:target_count]
    print(f"\n✅ Total valid collected: {len(candidates)}")
    return candidates

def download_repo_files(item):
    from huggingface_hub import hf_hub_download
    repo_id = item["repo"]
    files = []
    files.extend(item["main_quant_files"])
    if item["mtp"]: files.append(item["mtp"])
    if item["dspark2"]: files.append(item["dspark2"])
    if item["mmproj"]: files.append(item["mmproj"])
    for fname in files:
        try:
            local_path = hf_hub_download(repo_id=repo_id, filename=fname)
            print(f"[DONE] {repo_id}:{fname} -> {local_path}")
        except Exception as e:
            print(f"[FAIL] {repo_id}:{fname} -> {str(e)}")

def start_downloads(candidates, max_concurrent: int):
    from concurrent.futures import ThreadPoolExecutor
    print(f"\nStarting download pool, max concurrent repos: {max_concurrent}")
    with ThreadPoolExecutor(max_workers=max_concurrent) as executor:
        executor.map(download_repo_files, candidates)
    print("\nAll download tasks completed.")

def main():
    parser = argparse.ArgumentParser(description="HF GGUF downloader with shard(00001-of) support, median size filtering, dry-run one-by-one")
    parser.add_argument("--dry-run", action="store_true", help="List files ONE BY ONE immediately, NO DOWNLOAD")
    parser.add_argument("--target", type=int, default=20, help="Target valid models, api-limit = target")
    parser.add_argument("--max-concurrent", type=int, default=4)
    parser.add_argument("--debug", action="store_true")
    args = parser.parse_args()

    candidates = fetch_model_candidates(args.target, dry_run=args.dry_run, debug=args.debug)

    if not args.dry_run:
        confirm = input("\nStart downloads? [y/N] ")
        if confirm.strip().lower() == "y":
            start_downloads(candidates, args.max_concurrent)

if __name__ == "__main__":
    main()
