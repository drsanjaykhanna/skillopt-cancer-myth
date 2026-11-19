from __future__ import annotations

import csv
import hashlib
import json
import math
from pathlib import Path
from typing import Any

import numpy as np
from scipy.stats import binomtest


SOURCE_ROOT = Path("/home/khannas4/ESMO AI 2026/ai-congress")
RESULTS_ROOT = SOURCE_ROOT / "results"
BUILD_ROOT = Path("/mnt/c/Users/khannas4/Desktop/SkillOpt Publication Build")
DATA_ROOT = BUILD_ROOT / "data"
TABLE_ROOT = BUILD_ROOT / "tables"
AUDIT_ROOT = BUILD_ROOT / "audit"

RUNS = (
    "skillopt_v2_gpt4o",
    "skillopt_v2_gpt4o_replicate1",
    "skillopt_v2_gpt4o_replicate2",
)
CONDITIONS = (
    ("Baseline", "test_eval_baseline"),
    ("Post-optimisation", "test_eval"),
)


def read_jsonl(path: Path) -> list[dict[str, Any]]:
    records: list[dict[str, Any]] = []
    with path.open("r", encoding="utf-8") as handle:
        for line_number, line in enumerate(handle, start=1):
            if not line.strip():
                continue
            value = json.loads(line)
            if not isinstance(value, dict):
                raise TypeError(f"{path}:{line_number} is not a JSON object")
            records.append(value)
    return records


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


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


def valid_hard_score(value: Any) -> int:
    if isinstance(value, bool):
        return int(value)
    try:
        score = int(value)
    except (TypeError, ValueError) as error:
        raise ValueError(f"Invalid hard score: {value!r}") from error
    if score not in (0, 1):
        raise ValueError(f"Hard score must be 0 or 1, found {value!r}")
    return score


def persisted_test_ids() -> set[str]:
    path = RESULTS_ROOT / RUNS[0] / "_generated_splits" / "cancermyth_2-1-7_seed42" / "test" / "items.json"
    items = json.loads(path.read_text(encoding="utf-8"))
    ids = {str(item["id"]) for item in items}
    if len(ids) != 410:
        raise RuntimeError(f"Expected 410 persisted test IDs; found {len(ids)}")
    return ids


def load_native_ledger(
    run: str,
    condition: str,
    directory: str,
    expected_ids: set[str],
) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    path = RESULTS_ROOT / run / directory / "results.jsonl"
    records = read_jsonl(path)
    by_id: dict[str, dict[str, Any]] = {}
    for record in records:
        record_id = str(record.get("id", ""))
        if not record_id:
            raise RuntimeError(f"Missing record ID in {path}")
        if record_id in by_id:
            raise RuntimeError(f"Duplicate record ID {record_id} in {path}")
        by_id[record_id] = record

    observed_ids = set(by_id)
    if observed_ids != expected_ids:
        missing = sorted(expected_ids - observed_ids)
        unexpected = sorted(observed_ids - expected_ids)
        raise RuntimeError(
            f"Held-out ID mismatch in {path}: missing={missing[:5]}, unexpected={unexpected[:5]}"
        )

    rows: list[dict[str, Any]] = []
    for record_id in sorted(expected_ids):
        record = by_id[record_id]
        rows.append(
            {
                "run": run,
                "condition": condition,
                "id": record_id,
                "hard": valid_hard_score(record.get("hard")),
                "category": str(record.get("category", "")),
                "cancer_type": str(record.get("cancer_type", "")),
                "question": str(record.get("question", "")),
                "agent_ok": bool(record.get("agent_ok", False)),
                "fail_reason": str(record.get("fail_reason", "")),
                "source_ledger": str(path.relative_to(SOURCE_ROOT)),
            }
        )

    summary_path = RESULTS_ROOT / run / directory / "summary.json"
    persisted_summary = json.loads(summary_path.read_text(encoding="utf-8"))
    reported_total = int(persisted_summary["cancer_myth"]["total"])
    reported_rate = float(persisted_summary["cancer_myth"]["hard_acc"])
    calculated_rate = sum(row["hard"] for row in rows) / len(rows)
    if reported_total != len(rows) or not math.isclose(reported_rate, calculated_rate, abs_tol=1e-12):
        raise RuntimeError(f"Persisted summary disagrees with result ledger in {path.parent}")

    metadata = {
        "run": run,
        "condition": condition,
        "results_path": str(path.relative_to(SOURCE_ROOT)),
        "results_sha256": sha256(path),
        "summary_path": str(summary_path.relative_to(SOURCE_ROOT)),
        "summary_sha256": sha256(summary_path),
        "rows": len(rows),
        "unique_ids": len(observed_ids),
        "invalid_scores": 0,
        "reported_rate_pct": round(100 * reported_rate, 3),
    }
    return rows, metadata


def summarize(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    output: list[dict[str, Any]] = []
    for run in RUNS:
        for condition, _ in CONDITIONS:
            selected = [row for row in rows if row["run"] == run and row["condition"] == condition]
            successes = sum(row["hard"] for row in selected)
            low, high = wilson_interval(successes, len(selected))
            output.append(
                {
                    "run": run,
                    "condition": condition,
                    "outcome": "false-presupposition correction rate",
                    "n_total": len(selected),
                    "successes": successes,
                    "estimate_pct": round(100 * successes / len(selected), 3),
                    "ci_low_pct": round(low, 3),
                    "ci_high_pct": round(high, 3),
                }
            )
    return output


def paired_comparison(rows: list[dict[str, Any]], run: str, seed: int) -> dict[str, Any]:
    baseline = {
        row["id"]: row for row in rows if row["run"] == run and row["condition"] == "Baseline"
    }
    final = {
        row["id"]: row for row in rows if row["run"] == run and row["condition"] == "Post-optimisation"
    }
    if set(baseline) != set(final):
        raise RuntimeError(f"Baseline and post-optimisation ID sets differ for {run}")
    for record_id in baseline:
        if baseline[record_id]["question"] != final[record_id]["question"]:
            raise RuntimeError(f"Question text differs for {run}, ID {record_id}")

    ids = sorted(baseline)
    before = np.array([baseline[record_id]["hard"] for record_id in ids], dtype=float)
    after = np.array([final[record_id]["hard"] for record_id in ids], dtype=float)
    differences = 100 * (after - before)
    rng = np.random.default_rng(seed)
    indices = rng.integers(0, len(ids), size=(10000, len(ids)))
    bootstrap = differences[indices].mean(axis=1)
    improved = int(np.sum((after == 1) & (before == 0)))
    worsened = int(np.sum((after == 0) & (before == 1)))
    discordant = improved + worsened
    p_value = (
        binomtest(min(improved, worsened), discordant, p=0.5, alternative="two-sided").pvalue
        if discordant
        else 1.0
    )
    return {
        "run": run,
        "n_pairs": len(ids),
        "baseline_pct": round(100 * float(before.mean()), 3),
        "post_optimisation_pct": round(100 * float(after.mean()), 3),
        "paired_difference_pp": round(float(differences.mean()), 3),
        "bootstrap_ci_low_pp": round(float(np.quantile(bootstrap, 0.025)), 3),
        "bootstrap_ci_high_pp": round(float(np.quantile(bootstrap, 0.975)), 3),
        "improved_pairs": improved,
        "worsened_pairs": worsened,
        "mcnemar_exact_p": p_value,
    }


def holm_adjust(rows: list[dict[str, Any]]) -> None:
    order = sorted(range(len(rows)), key=lambda index: rows[index]["mcnemar_exact_p"])
    running = 0.0
    total = len(rows)
    adjusted = [0.0] * total
    for rank, index in enumerate(order):
        candidate = min(1.0, (total - rank) * rows[index]["mcnemar_exact_p"])
        running = max(running, candidate)
        adjusted[index] = running
    for index, value in enumerate(adjusted):
        rows[index]["holm_adjusted_p"] = value


def run_provenance() -> list[dict[str, Any]]:
    output: list[dict[str, Any]] = []
    for run in RUNS:
        run_root = RESULTS_ROOT / run
        config_path = run_root / "config.json"
        summary_path = run_root / "summary.json"
        skill_path = run_root / "best_skill.md"
        config = json.loads(config_path.read_text(encoding="utf-8"))
        summary = json.loads(summary_path.read_text(encoding="utf-8"))
        output.append(
            {
                "run": run,
                "target_model": config.get("target_model"),
                "optimizer_model": config.get("optimizer_model"),
                "split_mode": config.get("split_mode"),
                "split_ratio": config.get("split_ratio"),
                "split_seed": config.get("split_seed"),
                "training_seed": config.get("seed"),
                "num_epochs": config.get("num_epochs"),
                "total_steps": summary.get("total_steps"),
                "accepted_rewrites": summary.get("total_accepts"),
                "best_step": summary.get("best_step"),
                "best_selection_hard": summary.get("best_selection_hard"),
                "skill_characters": len(skill_path.read_text(encoding="utf-8")),
                "skill_sha256": sha256(skill_path),
                "config_sha256": sha256(config_path),
                "summary_sha256": sha256(summary_path),
            }
        )
    return output


def write_csv(path: Path, rows: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)


def write_report(
    summaries: list[dict[str, Any]],
    comparisons: list[dict[str, Any]],
    provenance: list[dict[str, Any]],
) -> None:
    lookup = {(row["run"], row["condition"]): row for row in summaries}
    baseline_values = [lookup[(run, "Baseline")]["estimate_pct"] for run in RUNS]
    final_values = [lookup[(run, "Post-optimisation")]["estimate_pct"] for run in RUNS]
    delta_values = [row["paired_difference_pp"] for row in comparisons]
    lines = [
        "# Locked Native Primary Analysis",
        "",
        "## Analysis population",
        "",
        "- Population: 410 false-presupposition questions in the persisted 2:1:7 split test partition.",
        "- Design: within-execution paired comparison of each native baseline ledger with that execution's post-optimisation ledger.",
        "- Outcome: false-presupposition correction rate, defined as a hard judge score of 1.",
        "- Every ledger contains exactly the same 410 unique IDs; binary scores, question text and persisted summaries were validated before analysis.",
        "- The three executions use the same split and recorded training seed. They quantify execution-to-execution variability but are not independent random-seed replications.",
        "",
        "## Results by execution",
        "",
    ]
    for run, comparison in zip(RUNS, comparisons, strict=True):
        baseline = lookup[(run, "Baseline")]
        final = lookup[(run, "Post-optimisation")]
        lines.append(
            f"- `{run}`: baseline {baseline['estimate_pct']:.1f}% "
            f"(95% CI {baseline['ci_low_pct']:.1f}-{baseline['ci_high_pct']:.1f}); "
            f"post-optimisation {final['estimate_pct']:.1f}% "
            f"(95% CI {final['ci_low_pct']:.1f}-{final['ci_high_pct']:.1f}); "
            f"paired change {comparison['paired_difference_pp']:+.1f} percentage points "
            f"(bootstrap 95% CI {comparison['bootstrap_ci_low_pp']:+.1f} to "
            f"{comparison['bootstrap_ci_high_pp']:+.1f}); exact McNemar p={comparison['mcnemar_exact_p']:.4g}, "
            f"Holm-adjusted p={comparison['holm_adjusted_p']:.4g}."
        )
    lines.extend(
        [
            "",
            "## Across-execution description",
            "",
            f"- Baseline mean {np.mean(baseline_values):.1f}% "
            f"(range {min(baseline_values):.1f}-{max(baseline_values):.1f}%).",
            f"- Post-optimisation mean {np.mean(final_values):.1f}% "
            f"(range {min(final_values):.1f}-{max(final_values):.1f}%).",
            f"- Paired improvement mean {np.mean(delta_values):.1f} percentage points "
            f"(range {min(delta_values):.1f}-{max(delta_values):.1f}).",
            "- These means and ranges are descriptive; no pooled item-level confidence interval treats the 1,230 observations as independent.",
            "",
            "## Artifact lineage",
            "",
        ]
    )
    for row in provenance:
        lines.append(
            f"- `{row['run']}`: best step {row['best_step']}, {row['accepted_rewrites']} accepted rewrites, "
            f"skill length {row['skill_characters']} characters, SHA-256 `{row['skill_sha256']}`."
        )
    lines.extend(
        [
            "",
            "## Interpretation guardrails",
            "",
            "- This is the primary efficacy analysis because the baseline and post-optimisation records arise from the native run structure and use the same held-out population.",
            "- The external harness passed the full prompt to the target model but persisted only its first 200 characters. The ledger named `skillopt_v2_gpt4o_best` has a logged prefix that does not match the current native best skill, so its exact prompt identity and 93.2% result are excluded from primary SkillOpt inference.",
            "- Native post-optimisation ledgers do not include the NFP negative controls. Specificity must therefore be reported from separate, prompt-verified external evaluations and cannot be represented as a native co-primary endpoint.",
            "- The current gate optimised one aggregate hard score over a mixed FP/NFP validation set. It was not a strict dual-objective non-regression gate.",
            "",
        ]
    )
    (AUDIT_ROOT / "locked_primary_analysis.md").write_text("\n".join(lines), encoding="utf-8")


def main() -> None:
    DATA_ROOT.mkdir(parents=True, exist_ok=True)
    TABLE_ROOT.mkdir(parents=True, exist_ok=True)
    AUDIT_ROOT.mkdir(parents=True, exist_ok=True)
    expected_ids = persisted_test_ids()

    all_rows: list[dict[str, Any]] = []
    registry: list[dict[str, Any]] = []
    for run in RUNS:
        for condition, directory in CONDITIONS:
            rows, metadata = load_native_ledger(run, condition, directory, expected_ids)
            all_rows.extend(rows)
            registry.append(metadata)

    summaries = summarize(all_rows)
    comparisons = [
        paired_comparison(all_rows, run, seed=20260901 + index)
        for index, run in enumerate(RUNS)
    ]
    holm_adjust(comparisons)
    provenance = run_provenance()

    write_csv(DATA_ROOT / "locked_primary_records.csv", all_rows)
    write_csv(AUDIT_ROOT / "locked_source_registry.csv", registry)
    write_csv(TABLE_ROOT / "primary_performance.csv", summaries)
    write_csv(TABLE_ROOT / "gpt4o_paired_comparisons.csv", comparisons)
    write_csv(TABLE_ROOT / "skillopt_training_replicates.csv", provenance)
    write_report(summaries, comparisons, provenance)
    print(f"Locked {len(all_rows)} native records from {len(registry)} matched ledgers.")
    print(f"Primary comparisons: {len(comparisons)} paired execution-level analyses.")


if __name__ == "__main__":
    main()