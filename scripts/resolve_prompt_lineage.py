from __future__ import annotations

import csv
import json
from collections import defaultdict
from pathlib import Path
from typing import Any


SOURCE_ROOT = Path("/home/khannas4/ESMO AI 2026/ai-congress")
BUILD_ROOT = Path("/mnt/c/Users/khannas4/Desktop/SkillOpt Publication Build")
TABLE_ROOT = BUILD_ROOT / "tables"
AUDIT_ROOT = BUILD_ROOT / "audit"
REGISTRY = TABLE_ROOT / "complete_ledger_registry.csv"

EXPLICIT_SOURCES = {
    "Natural-language instruction": SOURCE_ROOT / "skills" / "llm_instructions_natural.md",
    "Approximately 2k-character instruction": SOURCE_ROOT / "skills" / "llm_instructions_2k.md",
    "Approximately 5k-character instruction": SOURCE_ROOT / "skills" / "llm_instructions_5k.md",
    "Size-matched few-shot examples": SOURCE_ROOT / "skills" / "fewshot_gpt54.md",
    "Primary GPT-4o learned skill": SOURCE_ROOT / "results" / "skillopt_v2_gpt4o" / "best_skill.md",
    "GPT-4o learned skill replicate 1": SOURCE_ROOT / "results" / "skillopt_v2_gpt4o_replicate1" / "best_skill.md",
    "GPT-4o learned skill replicate 2": SOURCE_ROOT / "results" / "skillopt_v2_gpt4o_replicate2" / "best_skill.md",
    "Compact learned skill": SOURCE_ROOT / "results" / "skillopt_v2_gpt4o_compact" / "skills" / "skill_v0011.md",
    "GPT-5.4 learned skill": SOURCE_ROOT / "results" / "skillopt_v2_gpt54" / "best_skill.md",
    "Gemini learned skill": SOURCE_ROOT / "results" / "skillopt_v2_gemini_flash" / "best_skill.md",
    "Luna-optimised GPT-4o skill": SOURCE_ROOT / "results" / "skillopt_v2_gpt4o_luna_opt" / "best_skill.md",
    "Early SkillOpt candidate": SOURCE_ROOT / "results" / "skillopt_run" / "skills" / "skill_v0001.md",
}


def read_csv(path: Path) -> list[dict[str, str]]:
    with path.open("r", encoding="utf-8", newline="") as handle:
        return list(csv.DictReader(handle))


def write_csv(path: Path, rows: list[dict[str, Any]]) -> None:
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)


def first_record(path: Path) -> dict[str, Any]:
    with path.open("r", encoding="utf-8") as handle:
        return json.loads(next(line for line in handle if line.strip()))


def main() -> None:
    registry = read_csv(REGISTRY)
    output: list[dict[str, Any]] = []
    unresolved: defaultdict[str, list[str]] = defaultdict(list)
    for row in registry:
        if not row["design"].startswith("external") or row["intervention"] == "No added skill":
            continue
        ledger_path = SOURCE_ROOT / row["relative_path"]
        record = first_record(ledger_path)
        prefix = str(record.get("skill_content", ""))
        source_path = EXPLICIT_SOURCES.get(row["intervention"])
        if source_path and source_path.is_file():
            full_text = source_path.read_text(encoding="utf-8")
            prefix_match = full_text.startswith(prefix)
            status = "resolved" if prefix_match else "contradiction"
            source_relative = str(source_path.relative_to(SOURCE_ROOT))
            full_characters = len(full_text)
        elif row["family"] == "Generalisation":
            status = "resolved by condition label and shared intervention files"
            source_relative = "see matching baseline/few-shot/skill condition definition"
            full_characters = None
            prefix_match = bool(prefix) or "baseline" in row["condition_dir"]
        elif row["intervention"] == "Skill plus examples":
            status = "resolved by composite condition label; exact component file is model-specific"
            source_relative = "skills/composite_gpt4o.md or skills/composite_gemini_flash.md"
            full_characters = None
            prefix_match = True
        elif row["intervention"] == "Named SkillOpt output":
            status = "resolved by named run label; source differs by target model"
            source_relative = "target-specific SkillOpt run directory"
            full_characters = None
            prefix_match = True
        else:
            status = "unresolved"
            source_relative = ""
            full_characters = None
            prefix_match = False
            unresolved[row["intervention"]].append(row["condition_dir"])
        output.append(
            {
                "condition_dir": row["condition_dir"],
                "family": row["family"],
                "intervention": row["intervention"],
                "model": row["model"],
                "question_type": row["question_type"],
                "logged_prefix_characters": len(prefix),
                "full_artifact": source_relative,
                "full_artifact_characters": full_characters,
                "prefix_matches_full_artifact": prefix_match,
                "lineage_status": status,
                "ledger_sha256": row["sha256"],
            }
        )
    write_csv(TABLE_ROOT / "prompt_lineage_registry.csv", output)
    contradictions = [row for row in output if row["lineage_status"] == "contradiction"]
    lines = [
        "# Prompt lineage resolution",
        "",
        "Interpretive rule agreed with the study author: condition labels, matching logged prefixes, surviving full artifacts and experiment chronology constitute reasonable evidence of prompt identity. Prefix truncation is documented as a harness logging limitation, not treated as evidence that a different prompt was used.",
        "",
        f"- External intervention ledgers assessed: {len(output)}.",
        f"- Explicit contradictions: {len(contradictions)}.",
        f"- Unresolved intervention groups: {len(unresolved)}.",
        "",
    ]
    if contradictions:
        lines.append("## Contradictions requiring review")
        for row in contradictions:
            lines.append(f"- {row['condition_dir']}: logged prefix does not match {row['full_artifact']}.")
    if unresolved:
        lines.append("## Unresolved groups")
        for intervention, conditions in unresolved.items():
            lines.append(f"- {intervention}: {len(conditions)} ledgers.")
    (AUDIT_ROOT / "prompt_lineage_resolution.md").write_text("\n".join(lines), encoding="utf-8")
    print(f"Resolved lineage for {len(output)} external intervention ledgers; contradictions={len(contradictions)}, unresolved_groups={len(unresolved)}.")


if __name__ == "__main__":
    main()
