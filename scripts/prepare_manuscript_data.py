from __future__ import annotations

import csv
import json
import re
from pathlib import Path
from typing import Any


SOURCE_ROOT = Path("/home/khannas4/ESMO AI 2026/ai-congress")
BUILD_ROOT = Path("/mnt/c/Users/khannas4/Desktop/SkillOpt Publication Build")
TABLE_ROOT = BUILD_ROOT / "tables"

MODEL_ORDER = (
    "us.meta.llama3-1-8b-instruct-v1:0",
    "gemini-2.5-flash",
    "us.meta.llama3-3-70b-instruct-v1:0",
    "gpt-4o-2024-11-20",
    "gpt-5.4",
    "gemini-3.5-flash",
    "gpt-5.6-luna",
)
MODEL_LABELS = {
    "us.meta.llama3-1-8b-instruct-v1:0": "Llama 3.1 8B",
    "gemini-2.5-flash": "Gemini 2.5 Flash",
    "us.meta.llama3-3-70b-instruct-v1:0": "Llama 3.3 70B",
    "gpt-4o-2024-11-20": "GPT-4o",
    "gpt-5.4": "GPT-5.4",
    "gemini-3.5-flash": "Gemini 3.5 Flash",
    "gpt-5.6-luna": "GPT-5.6 Luna",
}
CORE_INTERVENTIONS = (
    "No added skill",
    "Size-matched few-shot examples",
    "Primary GPT-4o learned skill",
    "Compact learned skill",
)
PROMPT_INTERVENTIONS = (
    "Natural-language instruction",
    "Approximately 5k-character instruction",
    "Approximately 2k-character instruction",
    "Size-matched few-shot examples",
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


def lookup_secondary() -> dict[tuple[str, str, str], dict[str, str]]:
    rows = read_csv(TABLE_ROOT / "secondary_heldout_performance.csv")
    return {(row["model"], row["intervention"], row["question_type"]): row for row in rows}


def paired_grid(interventions: tuple[str, ...], filename: str) -> list[dict[str, Any]]:
    lookup = lookup_secondary()
    output: list[dict[str, Any]] = []
    for model in MODEL_ORDER:
        for intervention in interventions:
            fp = lookup.get((model, intervention, "fp"))
            nfp = lookup.get((model, intervention, "nfp"))
            if not fp and not nfp:
                continue
            output.append(
                {
                    "model": MODEL_LABELS[model],
                    "model_id": model,
                    "intervention": intervention,
                    "correction_pct": float(fp["estimate_pct_conservative"]) if fp else None,
                    "correction_low_pct": float(fp["ci_low_pct_conservative"]) if fp else None,
                    "correction_high_pct": float(fp["ci_high_pct_conservative"]) if fp else None,
                    "correction_missing": int(fp["missing_or_invalid"]) if fp else None,
                    "specificity_pct": float(nfp["estimate_pct_conservative"]) if nfp else None,
                    "specificity_low_pct": float(nfp["ci_low_pct_conservative"]) if nfp else None,
                    "specificity_high_pct": float(nfp["ci_high_pct_conservative"]) if nfp else None,
                    "specificity_missing": int(nfp["missing_or_invalid"]) if nfp else None,
                }
            )
    write_csv(TABLE_ROOT / filename, output)
    return output


def native_learning_rows() -> list[dict[str, Any]]:
    source = read_csv(TABLE_ROOT / "native_optimisation_registry.csv")
    labels = {
        "skillopt_v2_gpt4o": "GPT-4o / GPT-5.4 optimiser (execution 1)",
        "skillopt_v2_gpt4o_replicate1": "GPT-4o / GPT-5.4 optimiser (execution 2)",
        "skillopt_v2_gpt4o_replicate2": "GPT-4o / GPT-5.4 optimiser (execution 3)",
        "skillopt_v2_gpt4o_compact": "GPT-4o / GPT-5.4 optimiser (compact)",
        "skillopt_v2_gpt4o_selfopt": "GPT-4o self-optimisation",
        "skillopt_v2_gpt4o_luna_opt": "GPT-4o / GPT-5.6 Luna optimiser",
        "skillopt_v2_gpt54": "GPT-5.4 self-optimisation",
        "skillopt_v2_gemini_flash": "Gemini 2.5 Flash / GPT-5.4 optimiser",
        "skillopt_v2_llama8b": "Llama 3.1 8B / GPT-5.4 optimiser",
        "skillopt_v2_llama70b": "Llama 3.3 70B / GPT-5.4 optimiser",
        "skillopt_v2_gemini35_flash": "Gemini 3.5 Flash / GPT-5.4 optimiser",
        "skillopt_v2_luna": "GPT-5.6 Luna / GPT-5.4 optimiser",
    }
    output: list[dict[str, Any]] = []
    for row in source:
        planned = int(row["configured_steps"]) if row["configured_steps"] else 0
        observed = int(row["history_steps"]) if row["history_steps"] else 0
        if row["native_final_pct"]:
            status = "complete paired evaluation"
        elif observed == planned and planned > 0:
            status = "complete optimisation; no learned rewrite"
        elif observed > 0:
            status = "incomplete optimisation"
        else:
            status = "not started"
        output.append(
            {
                "run": row["run"],
                "label": labels.get(row["run"], row["run"]),
                "target_model": row["target_model"],
                "optimizer_model": row["optimizer_model"],
                "planned_steps": planned,
                "observed_steps": observed,
                "accepted_rewrites": int(row["accepted_rewrites"]) if row["accepted_rewrites"] else 0,
                "baseline_pct": float(row["native_baseline_pct"]) if row["native_baseline_pct"] else None,
                "final_pct": float(row["native_final_pct"]) if row["native_final_pct"] else None,
                "delta_pp": float(row["native_delta_pp"]) if row["native_delta_pp"] else None,
                "skill_characters": int(row["skill_characters"]) if row["skill_characters"] else None,
                "status": status,
            }
        )
    write_csv(TABLE_ROOT / "native_learning_summary.csv", output)
    return output


def portability_rows() -> list[dict[str, Any]]:
    source = read_csv(TABLE_ROOT / "secondary_heldout_performance.csv")
    wanted = {
        "Primary GPT-4o learned skill": "Primary skill",
        "GPT-4o learned skill replicate 1": "Replicate 1",
        "GPT-4o learned skill replicate 2": "Replicate 2",
    }
    output: list[dict[str, Any]] = []
    for row in source:
        if row["question_type"] != "fp" or row["intervention"] not in wanted:
            continue
        output.append(
            {
                "skill": wanted[row["intervention"]],
                "recipient_model": MODEL_LABELS.get(row["model"], row["model"]),
                "recipient_model_id": row["model"],
                "correction_pct": float(row["estimate_pct_conservative"]),
                "ci_low_pct": float(row["ci_low_pct_conservative"]),
                "ci_high_pct": float(row["ci_high_pct_conservative"]),
                "missing_or_invalid": int(row["missing_or_invalid"]),
            }
        )
    write_csv(TABLE_ROOT / "independent_skill_portability.csv", output)
    return output


def thematic_rows() -> list[dict[str, Any]]:
    files = {
        "Primary skill": SOURCE_ROOT / "results" / "skillopt_v2_gpt4o" / "best_skill.md",
        "Replicate 1": SOURCE_ROOT / "results" / "skillopt_v2_gpt4o_replicate1" / "best_skill.md",
        "Replicate 2": SOURCE_ROOT / "results" / "skillopt_v2_gpt4o_replicate2" / "best_skill.md",
    }
    themes = {
        "Premise audit": r"premise|assumption",
        "Correction before advice": r"before.*(advice|guidance|answer)|first 1-2 sentences|opening correction",
        "Explicit negate-then-replace template": r"negate-then-replace",
        "Conditional framing": r"conditional|\bcan\b|\bmay\b|\boften\b|depends",
        "Clinical determinants": r"stage|pathology|biomarker|overall health",
        "Oncology-team referral": r"oncolog|care team|relevant clinician",
        "Avoid downstream reinforcement": r"downstream|do not.*(planning|logistics)|before.*(planning|logistics)|build.*around",
        "Supportive or empathetic tone": r"empat|supportive|acknowledge",
    }
    output: list[dict[str, Any]] = []
    for skill, path in files.items():
        text = path.read_text(encoding="utf-8")
        for theme, pattern in themes.items():
            matches = re.findall(pattern, text, flags=re.IGNORECASE)
            output.append(
                {
                    "skill": skill,
                    "theme": theme,
                    "present": int(bool(matches)),
                    "match_count": len(matches),
                    "skill_characters": len(text),
                }
            )
    write_csv(TABLE_ROOT / "independent_skill_themes.csv", output)
    return output


def generalisation_rows() -> list[dict[str, Any]]:
    source = read_csv(TABLE_ROOT / "expansion_performance.csv")
    output: list[dict[str, Any]] = []
    for row in source:
        if "_baseline_" in row["condition_dir"]:
            arm = "Baseline"
        elif "_fewshot_" in row["condition_dir"]:
            arm = "Few-shot"
        elif "_skillopt_" in row["condition_dir"]:
            arm = "Learned skill"
        else:
            arm = "Other"
        output.append(
            {
                "set": row["intervention"],
                "model": MODEL_LABELS.get(row["model"], row["model"]),
                "arm": arm,
                "n": int(row["n_expected"]),
                "success_pct": float(row["estimate_pct_conservative"]),
                "missing_or_invalid": int(row["missing_or_invalid"]),
            }
        )
    write_csv(TABLE_ROOT / "generalisation_summary.csv", output)
    return output


def judge_rows() -> list[dict[str, Any]]:
    root = SOURCE_ROOT / "results" / "judge_calibration"
    output: list[dict[str, Any]] = []
    for design, filename in (
        ("Stratified score sample", "full_comparison.json"),
        ("High-performing response sample", "p15_results.json"),
    ):
        for row in json.loads((root / filename).read_text(encoding="utf-8")):
            output.append(
                {
                    "design": design,
                    "judge_model": row["judge_model"],
                    "n": int(row.get("n_questions", 0)),
                    "n_valid": int(row.get("n_valid", row.get("n_questions", 0))),
                    "agreement_pct": float(row["agreement_pct"]),
                    "primary_judge_correction_pct": float(row["pcr_gpt4o_judge"]),
                    "alternative_judge_correction_pct": float(row["pcr_new_judge"]),
                    "difference_pp": float(row["pcr_difference"]),
                }
            )
    write_csv(TABLE_ROOT / "automated_judge_sensitivity.csv", output)
    return output


def prompt_artifacts() -> list[dict[str, Any]]:
    rows = [
        ("Natural rule prompt", SOURCE_ROOT / "skills" / "llm_instructions_natural.md", "one-shot GPT-5.4 instruction generation"),
        ("Medium rule prompt", SOURCE_ROOT / "skills" / "llm_instructions_5k.md", "one-shot GPT-5.4 instruction generation"),
        ("Short rule prompt", SOURCE_ROOT / "skills" / "llm_instructions_2k.md", "one-shot GPT-5.4 instruction generation"),
        ("Few-shot prompt", SOURCE_ROOT / "skills" / "fewshot_gpt54.md", "one-shot GPT-5.4 prompt with worked examples"),
        ("Primary learned skill", SOURCE_ROOT / "results" / "skillopt_v2_gpt4o" / "best_skill.md", "SkillOpt execution 1"),
        ("Learned skill replicate 1", SOURCE_ROOT / "results" / "skillopt_v2_gpt4o_replicate1" / "best_skill.md", "SkillOpt execution 2"),
        ("Learned skill replicate 2", SOURCE_ROOT / "results" / "skillopt_v2_gpt4o_replicate2" / "best_skill.md", "SkillOpt execution 3"),
        ("Compact checkpoint", SOURCE_ROOT / "results" / "skillopt_v2_gpt4o_compact" / "skills" / "skill_v0011.md", "SkillOpt compact step 11 used in external grid"),
        ("Compact final skill", SOURCE_ROOT / "results" / "skillopt_v2_gpt4o_compact" / "best_skill.md", "SkillOpt compact step 14 native best"),
    ]
    output: list[dict[str, Any]] = []
    import hashlib
    for label, path, provenance in rows:
        text = path.read_text(encoding="utf-8")
        output.append(
            {
                "artifact": label,
                "relative_path": str(path.relative_to(SOURCE_ROOT)),
                "characters": len(text),
                "words": len(text.split()),
                "sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
                "provenance": provenance,
            }
        )
    write_csv(TABLE_ROOT / "prompt_artifact_registry.csv", output)
    return output


def main() -> None:
    core = paired_grid(CORE_INTERVENTIONS, "core_intervention_grid.csv")
    prompt = paired_grid(PROMPT_INTERVENTIONS, "prompt_strategy_grid.csv")
    native = native_learning_rows()
    portability = portability_rows()
    themes = thematic_rows()
    generalisation = generalisation_rows()
    judges = judge_rows()
    artifacts = prompt_artifacts()
    print(
        f"Prepared manuscript datasets: core={len(core)}, prompt={len(prompt)}, native={len(native)}, "
        f"portability={len(portability)}, themes={len(themes)}, generalisation={len(generalisation)}, "
        f"judges={len(judges)}, artifacts={len(artifacts)}."
    )


if __name__ == "__main__":
    main()
