from __future__ import annotations

import csv
import json
import math
import random
from pathlib import Path
from typing import Any


SOURCE_ROOT = Path("/home/khannas4/ESMO AI 2026/ai-congress")
RESULTS_ROOT = SOURCE_ROOT / "results"
BUILD_ROOT = Path("/mnt/c/Users/khannas4/Desktop/SkillOpt Publication Build")
AUDIT_ROOT = BUILD_ROOT / "audit"
TABLE_ROOT = BUILD_ROOT / "tables"
REGISTRY_PATH = TABLE_ROOT / "complete_ledger_registry.csv"
PRIMARY_RUN = RESULTS_ROOT / "skillopt_v2_gpt4o"


def read_csv(path: Path) -> list[dict[str, str]]:
    with path.open("r", encoding="utf-8", newline="") as handle:
        return list(csv.DictReader(handle))


def write_csv(path: Path, rows: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)


def read_jsonl(path: Path) -> list[dict[str, Any]]:
    with path.open("r", encoding="utf-8") as handle:
        return [json.loads(line) for line in handle if line.strip()]


def valid_score(value: Any) -> int | None:
    try:
        score = int(value)
    except (TypeError, ValueError):
        return None
    return score if score in (-1, 0, 1) else None


def wilson_interval(successes: int, total: int, z: float = 1.959963984540054) -> tuple[float, float]:
    if total == 0:
        return math.nan, math.nan
    proportion = successes / total
    denominator = 1 + z**2 / total
    centre = (proportion + z**2 / (2 * total)) / denominator
    half_width = z * math.sqrt(
        proportion * (1 - proportion) / total + z**2 / (4 * total**2)
    ) / denominator
    return 100 * (centre - half_width), 100 * (centre + half_width)


def heldout_ids() -> tuple[set[str], set[str]]:
    split_path = PRIMARY_RUN / "_generated_splits" / "cancermyth_2-1-7_seed42" / "test" / "items.json"
    split_items = json.loads(split_path.read_text(encoding="utf-8"))
    original_test_ids = {str(item["id"]) for item in split_items}
    flat_records = read_jsonl(SOURCE_ROOT / "data" / "cancer_myth.jsonl")
    original_to_external = {str(item["QID"]): str(index) for index, item in enumerate(flat_records)}
    fp_ids = {original_to_external[record_id] for record_id in original_test_ids}
    nfp_items = json.loads((SOURCE_ROOT / "cancer-myth" / "data" / "nfp.json").read_text(encoding="utf-8"))
    nfp_ids = [str(index) for index in range(len(nfp_items))]
    random.Random(42).shuffle(nfp_ids)
    return fp_ids, set(nfp_ids[30:])


def score_population(records: list[dict[str, Any]], expected_ids: set[str]) -> dict[str, Any]:
    by_id: dict[str, dict[str, Any]] = {}
    duplicates = 0
    for record in records:
        record_id = str(record.get("qid", ""))
        if record_id in by_id:
            duplicates += 1
        by_id[record_id] = record
    if duplicates:
        raise RuntimeError("Duplicate IDs reached secondary analysis")

    scores = [valid_score(by_id[record_id].get("judge_score")) if record_id in by_id else None for record_id in sorted(expected_ids)]
    successes = sum(score == 1 for score in scores)
    available = [score for score in scores if score is not None]
    low, high = wilson_interval(successes, len(expected_ids))
    available_successes = sum(score == 1 for score in available)
    available_low, available_high = wilson_interval(available_successes, len(available))
    return {
        "n_expected": len(expected_ids),
        "n_present": sum(record_id in by_id for record_id in expected_ids),
        "n_available": len(available),
        "missing_or_invalid": len(expected_ids) - len(available),
        "successes_conservative": successes,
        "estimate_pct_conservative": round(100 * successes / len(expected_ids), 3),
        "ci_low_pct_conservative": round(low, 3),
        "ci_high_pct_conservative": round(high, 3),
        "estimate_pct_available": round(100 * available_successes / len(available), 3) if available else None,
        "ci_low_pct_available": round(available_low, 3),
        "ci_high_pct_available": round(available_high, 3),
    }


def complete_population(records: list[dict[str, Any]]) -> dict[str, Any]:
    scores = [valid_score(record.get("judge_score")) for record in records]
    available = [score for score in scores if score is not None]
    successes = sum(score == 1 for score in available)
    low, high = wilson_interval(successes, len(records))
    return {
        "n_expected": len(records),
        "n_present": len(records),
        "n_available": len(available),
        "missing_or_invalid": len(records) - len(available),
        "successes_conservative": successes,
        "estimate_pct_conservative": round(100 * successes / len(records), 3),
        "ci_low_pct_conservative": round(low, 3),
        "ci_high_pct_conservative": round(high, 3),
        "estimate_pct_available": round(100 * successes / len(available), 3) if available else None,
        "ci_low_pct_available": None,
        "ci_high_pct_available": None,
    }


def main() -> None:
    fp_ids, nfp_ids = heldout_ids()
    registry = read_csv(REGISTRY_PATH)
    output: list[dict[str, Any]] = []
    expansion: list[dict[str, Any]] = []
    for metadata in registry:
        if metadata["status"].startswith("exclude"):
            continue
        path = SOURCE_ROOT / metadata["relative_path"]
        records = read_jsonl(path)
        if metadata["family"] == "Generalisation":
            result = complete_population(records)
            destination = expansion
            population = metadata["population"]
        elif metadata["rows"] == "585" and metadata["question_type"] == "fp":
            result = score_population(records, fp_ids)
            destination = output
            population = "Locked FP test partition"
        elif metadata["rows"] == "150" and metadata["question_type"] == "nfp":
            result = score_population(records, nfp_ids)
            destination = output
            population = "Locked NFP specificity partition"
        else:
            continue
        destination.append(
            {
                "family": metadata["family"],
                "intervention": metadata["intervention"],
                "condition_dir": metadata["condition_dir"],
                "model": metadata["model"],
                "question_type": metadata["question_type"],
                "outcome": "Correction rate" if metadata["question_type"] == "fp" else "Negative-control specificity",
                "population": population,
                **result,
                "prompt_provenance": metadata["prompt_provenance"],
                "status": metadata["status"],
                "sha256": metadata["sha256"],
            }
        )

    write_csv(TABLE_ROOT / "secondary_heldout_performance.csv", output)
    write_csv(TABLE_ROOT / "expansion_performance.csv", expansion)
    by_family: dict[str, int] = {}
    for row in output:
        by_family[row["family"]] = by_family.get(row["family"], 0) + 1
    lines = [
        "# Secondary held-out reconstruction",
        "",
        "Every eligible 585-question FP ledger was restricted to the same persisted 410-question test partition.",
        "Every eligible 150-question NFP ledger was restricted to the same 120 questions not used in the mixed validation gate.",
        "Missing and invalid scores count as failures in the conservative estimate; available-case estimates are retained as sensitivity analyses.",
        "Expansion-set results retain their complete native populations.",
        "",
        "## Coverage",
        "",
    ]
    for family, count in sorted(by_family.items()):
        lines.append(f"- {family}: {count} held-out condition-outcome cells.")
    lines.extend(["", f"- Expansion/generalisation cells: {len(expansion)}.", ""])
    (AUDIT_ROOT / "secondary_heldout_reconstruction.md").write_text("\n".join(lines), encoding="utf-8")
    print(f"Reconstructed {len(output)} held-out secondary cells and {len(expansion)} expansion cells.")


if __name__ == "__main__":
    main()
