from __future__ import annotations

import csv
import hashlib
import json
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any


SOURCE_ROOT = Path("/home/khannas4/ESMO AI 2026/ai-congress")
RESULTS_ROOT = SOURCE_ROOT / "results"
BUILD_ROOT = Path("/mnt/c/Users/khannas4/Desktop/SkillOpt Publication Build")
AUDIT_ROOT = BUILD_ROOT / "audit"
TABLE_ROOT = BUILD_ROOT / "tables"
RAW_INVENTORY = AUDIT_ROOT / "raw_condition_inventory.csv"

NATIVE_RUNS = (
    "skillopt_v2_gpt4o",
    "skillopt_v2_gpt4o_replicate1",
    "skillopt_v2_gpt4o_replicate2",
    "skillopt_v2_gpt4o_compact",
    "skillopt_v2_gpt4o_selfopt",
    "skillopt_v2_gpt4o_luna_opt",
    "skillopt_v2_gpt54",
    "skillopt_v2_gemini_flash",
    "skillopt_v2_gemini35_flash",
    "skillopt_v2_llama8b",
    "skillopt_v2_llama70b",
    "skillopt_v2_luna",
)


def read_csv(path: Path) -> list[dict[str, str]]:
    with path.open("r", encoding="utf-8", newline="") as handle:
        return list(csv.DictReader(handle))


def write_csv(path: Path, rows: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def as_int(row: dict[str, str], key: str) -> int:
    value = row.get(key, "")
    return int(value) if value else 0


def as_float(row: dict[str, str], key: str) -> float | None:
    value = row.get(key, "")
    return float(value) if value else None


def classify_condition(name: str) -> tuple[str, str, str]:
    rules = (
        (("exp_a_",), "Generalisation", "Near-transfer expansion A", "external expansion set"),
        (("exp_b2_",), "Generalisation", "Adversarial true-premise controls B2", "external adversarial control set"),
        (("exp_b_",), "Generalisation", "Far-transfer expansion B1", "external expansion set"),
        (("llm_natural_",), "Prompt strategy", "Natural-language instruction", "external full-dataset harness"),
        (("llm_2k_",), "Prompt strategy", "Approximately 2k-character instruction", "external full-dataset harness"),
        (("llm_5k_",), "Prompt strategy", "Approximately 5k-character instruction", "external full-dataset harness"),
        (("fewshot_gpt54_", "gpt54_fewshot_", "luna_fewshot_"), "Prompt strategy", "Size-matched few-shot examples", "external full-dataset harness"),
        (("compact_skill_",), "Compression", "Compact learned skill", "external full-dataset harness"),
        (("comp_",), "Composite intervention", "Skill plus examples", "external full-dataset harness"),
        (("port_rep1_skill_",), "Skill portability", "GPT-4o learned skill replicate 1", "external full-dataset harness"),
        (("port_rep2_skill_",), "Skill portability", "GPT-4o learned skill replicate 2", "external full-dataset harness"),
        (("port_gpt4o_skill_", "gpt54_gpt4o_skill_", "luna_gpt4o_skill_"), "Skill portability", "Primary GPT-4o learned skill", "external full-dataset harness"),
        (("port_gpt54_skill_",), "Skill portability", "GPT-5.4 learned skill", "external full-dataset harness"),
        (("port_gemini_skill_",), "Skill portability", "Gemini learned skill", "external full-dataset harness"),
        (("luna_opt_skill_",), "Skill portability", "Luna-optimised GPT-4o skill", "external full-dataset harness"),
        (("skillopt_v0001_",), "Legacy optimisation", "Early SkillOpt candidate", "external full-dataset harness"),
        (("skillopt_v2_",), "Skill evaluation", "Named SkillOpt output", "external full-dataset harness"),
        (("baseline_",), "Baseline capability", "No added skill", "external full-dataset harness"),
    )
    for prefixes, family, intervention, design in rules:
        if name.startswith(prefixes):
            return family, intervention, design
    return "Unclassified", "Unclassified", "unknown"


def infer_population(row: dict[str, str]) -> str:
    rows = as_int(row, "rows")
    question_types = row.get("question_types", "")
    if rows == 585 and question_types == "fp":
        return "Cancer-Myth full FP corpus (n=585)"
    if rows == 150 and question_types == "nfp":
        return "Cancer-Myth-NFP full corpus (n=150)"
    if rows == 50:
        return "Expansion set (n=50)"
    if rows == 25:
        return "Adversarial control set (n=25)"
    return f"Non-standard or partial population (rows={rows})"


def ledger_status(row: dict[str, str]) -> tuple[str, str]:
    findings = []
    for field in ("parse_errors", "duplicate_qids", "target_errors", "judge_errors", "blank_responses", "invalid_scores"):
        value = as_int(row, field)
        if value:
            findings.append(f"{field}={value}")
    rows = as_int(row, "rows")
    if rows not in (25, 50, 150, 585):
        findings.append(f"nonstandard_rows={rows}")
    if as_int(row, "parse_errors") or as_int(row, "duplicate_qids"):
        return "exclude pending repair", "; ".join(findings)
    if findings:
        return "usable with conservative missing-as-failure analysis", "; ".join(findings)
    return "usable", "no record-level integrity findings"


def build_ledger_registry() -> list[dict[str, Any]]:
    output: list[dict[str, Any]] = []
    for row in read_csv(RAW_INVENTORY):
        name = row["condition_dir"]
        family, intervention, design = classify_condition(name)
        status, findings = ledger_status(row)
        output.append(
            {
                "family": family,
                "intervention": intervention,
                "condition_dir": name,
                "question_type": row.get("question_types", ""),
                "model": row.get("models", ""),
                "label": row.get("labels", ""),
                "population": infer_population(row),
                "rows": as_int(row, "rows"),
                "scored_rows": as_int(row, "scored_rows"),
                "success_pct_available": as_float(row, "success_pct"),
                "design": design,
                "prompt_provenance": "prefix only (first 200 characters persisted)" if design.startswith("external") and intervention != "No added skill" else "not applicable" if intervention == "No added skill" else "requires native artifact linkage",
                "status": status,
                "integrity_findings": findings,
                "relative_path": row["relative_path"],
                "sha256": row["sha256"],
            }
        )
    return output


def test_summary(run_root: Path, directory: str) -> tuple[int | None, float | None, str]:
    path = run_root / directory / "summary.json"
    if not path.is_file():
        return None, None, ""
    summary = json.loads(path.read_text(encoding="utf-8"))
    cancer_myth = summary.get("cancer_myth", {})
    total = cancer_myth.get("total")
    hard = cancer_myth.get("hard_acc")
    return int(total) if total is not None else None, 100 * float(hard) if hard is not None else None, sha256(path)


def build_native_registry() -> list[dict[str, Any]]:
    output: list[dict[str, Any]] = []
    for run in NATIVE_RUNS:
        root = RESULTS_ROOT / run
        if not root.is_dir():
            continue
        config_path = root / "config.json"
        summary_path = root / "summary.json"
        history_path = root / "history.json"
        skill_path = root / "best_skill.md"
        config = json.loads(config_path.read_text(encoding="utf-8")) if config_path.is_file() else {}
        summary = json.loads(summary_path.read_text(encoding="utf-8")) if summary_path.is_file() else {}
        baseline_n, baseline_pct, baseline_sha = test_summary(root, "test_eval_baseline")
        final_n, final_pct, final_sha = test_summary(root, "test_eval")
        history = json.loads(history_path.read_text(encoding="utf-8")) if history_path.is_file() else []
        output.append(
            {
                "run": run,
                "target_model": config.get("target_model", ""),
                "optimizer_model": config.get("optimizer_model", ""),
                "environment": config.get("env", ""),
                "split_mode": config.get("split_mode", ""),
                "split_ratio": config.get("split_ratio", ""),
                "split_seed": config.get("split_seed", ""),
                "training_seed": config.get("seed", ""),
                "epochs": config.get("num_epochs", ""),
                "configured_steps": config.get("batches_per_epoch", 0) * config.get("num_epochs", 0) if config else "",
                "history_steps": len(history),
                "total_steps": summary.get("total_steps", ""),
                "accepted_rewrites": summary.get("total_accepts", ""),
                "best_step": summary.get("best_step", ""),
                "best_validation_hard_pct": 100 * float(summary["best_selection_hard"]) if summary.get("best_selection_hard") is not None else None,
                "native_baseline_n": baseline_n,
                "native_baseline_pct": baseline_pct,
                "native_final_n": final_n,
                "native_final_pct": final_pct,
                "native_delta_pp": final_pct - baseline_pct if final_pct is not None and baseline_pct is not None else None,
                "skill_characters": len(skill_path.read_text(encoding="utf-8")) if skill_path.is_file() else None,
                "skill_sha256": sha256(skill_path) if skill_path.is_file() else "",
                "config_sha256": sha256(config_path) if config_path.is_file() else "",
                "summary_sha256": sha256(summary_path) if summary_path.is_file() else "",
                "history_sha256": sha256(history_path) if history_path.is_file() else "",
                "baseline_summary_sha256": baseline_sha,
                "final_summary_sha256": final_sha,
            }
        )
    return output


def write_report(ledgers: list[dict[str, Any]], native: list[dict[str, Any]]) -> None:
    families: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for row in ledgers:
        families[row["family"]].append(row)
    lines = [
        "# Complete evidence inventory",
        "",
        "This registry inventories raw experimental evidence without deciding the final manuscript narrative.",
        "Human-review artifacts are intentionally out of scope and remain the final validation task.",
        "",
        "## Evaluation ledgers",
        "",
        f"- Total JSONL ledgers: {len(ledgers)}.",
        f"- Experiment families: {len(families)}.",
        f"- Usable without integrity findings: {sum(row['status'] == 'usable' for row in ledgers)}.",
        f"- Usable with conservative missing-as-failure handling: {sum(row['status'].startswith('usable with') for row in ledgers)}.",
        f"- Excluded pending repair: {sum(row['status'].startswith('exclude') for row in ledgers)}.",
        "- External harness ledgers persist only the first 200 prompt characters; exact prompt identity requires linkage to launch records or immutable manifests.",
        "",
        "## Family coverage",
        "",
        "| Family | Ledgers | Models | FP | NFP | Status summary |",
        "|---|---:|---:|---:|---:|---|",
    ]
    for family in sorted(families):
        rows = families[family]
        status_counts = Counter(row["status"] for row in rows)
        lines.append(
            f"| {family} | {len(rows)} | {len({row['model'] for row in rows if row['model']})} | "
            f"{sum(row['question_type'] == 'fp' for row in rows)} | {sum(row['question_type'] == 'nfp' for row in rows)} | "
            f"{'; '.join(f'{count} {status}' for status, count in status_counts.items())} |"
        )
    lines.extend(
        [
            "",
            "## Native optimisation runs",
            "",
            "| Run | Target | Optimiser | Steps | Accepted | Native baseline | Native final | Delta | Skill chars |",
            "|---|---|---|---:|---:|---:|---:|---:|---:|",
        ]
    )
    for row in native:
        def pct(value: Any) -> str:
            return "-" if value is None else f"{float(value):.1f}%"
        lines.append(
            f"| {row['run']} | {row['target_model'] or '-'} | {row['optimizer_model'] or '-'} | "
            f"{row['total_steps'] or row['history_steps'] or '-'} | {row['accepted_rewrites'] if row['accepted_rewrites'] != '' else '-'} | "
            f"{pct(row['native_baseline_pct'])} | {pct(row['native_final_pct'])} | {pct(row['native_delta_pp'])} | "
            f"{row['skill_characters'] or '-'} |"
        )
    lines.extend(
        [
            "",
            "## Manuscript-relevant experimental layers",
            "",
            "1. Native repeated optimisation efficacy and item-level reproducibility.",
            "2. Optimiser-target capability and self- versus externally optimised learning curves.",
            "3. Cross-provider and cross-scale skill portability.",
            "4. Portability differences among independently learned skill formulations.",
            "5. Rules versus examples across recipient-model capability.",
            "6. Prompt-length response surfaces across model families.",
            "7. Full versus compact learned-skill efficacy-specificity trade-offs.",
            "8. Composite skill-plus-example interventions.",
            "9. Near-transfer, far-transfer and adversarial true-premise controls.",
            "10. Alternative automated-judge sensitivity analysis.",
            "11. Thematic convergence and divergence of independently learned skills.",
            "12. Human validation (deferred final task; not included in the current evidence base).",
            "",
        ]
    )
    (AUDIT_ROOT / "complete_evidence_inventory.md").write_text("\n".join(lines), encoding="utf-8")


def main() -> None:
    ledgers = build_ledger_registry()
    native = build_native_registry()
    write_csv(TABLE_ROOT / "complete_ledger_registry.csv", ledgers)
    write_csv(TABLE_ROOT / "native_optimisation_registry.csv", native)
    write_report(ledgers, native)
    print(f"Classified {len(ledgers)} evaluation ledgers across {len({row['family'] for row in ledgers})} families.")
    print(f"Registered {len(native)} native optimisation runs.")


if __name__ == "__main__":
    main()
