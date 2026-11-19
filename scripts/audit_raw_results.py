from __future__ import annotations

import csv
import hashlib
import json
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable


SOURCE_ROOT = Path("/home/khannas4/ESMO AI 2026/ai-congress")
RESULTS_ROOT = SOURCE_ROOT / "results"
MANUSCRIPT_ROOT = SOURCE_ROOT / "manuscript"
BUILD_ROOT = Path("/mnt/c/Users/khannas4/Desktop/SkillOpt Publication Build")
AUDIT_ROOT = BUILD_ROOT / "audit"

CONSOLIDATED_FILES = (
    MANUSCRIPT_ROOT / "DEFINITIVE_DATA.json",
    MANUSCRIPT_ROOT / "GROUND_TRUTH_v2.json",
    MANUSCRIPT_ROOT / "human_eval_results.json",
    MANUSCRIPT_ROOT / "human_eval_200_results.json",
    MANUSCRIPT_ROOT / "test_only_portability.json",
)


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def read_jsonl(path: Path) -> tuple[list[dict[str, Any]], list[str]]:
    records: list[dict[str, Any]] = []
    errors: list[str] = []
    with path.open("r", encoding="utf-8") as handle:
        for line_number, line in enumerate(handle, start=1):
            if not line.strip():
                continue
            try:
                value = json.loads(line)
            except json.JSONDecodeError as exc:
                errors.append(f"line {line_number}: {exc}")
                continue
            if not isinstance(value, dict):
                errors.append(f"line {line_number}: expected object, got {type(value).__name__}")
                continue
            records.append(value)
    return records, errors


def unique_values(records: Iterable[dict[str, Any]], key: str) -> list[str]:
    return sorted({str(record.get(key, "")) for record in records if record.get(key) not in (None, "")})


def score_summary(records: list[dict[str, Any]]) -> dict[str, Any]:
    scores: list[int] = []
    invalid_scores = 0
    for record in records:
        value = record.get("judge_score")
        try:
            score = int(value)
        except (TypeError, ValueError):
            invalid_scores += 1
            continue
        if score not in (-1, 0, 1):
            invalid_scores += 1
            continue
        scores.append(score)

    distribution = Counter(scores)
    return {
        "scored_rows": len(scores),
        "invalid_scores": invalid_scores,
        "score_minus_1": distribution[-1],
        "score_0": distribution[0],
        "score_plus_1": distribution[1],
        "success_pct": round(100 * distribution[1] / len(scores), 6) if scores else None,
        "mean_score": round(sum(scores) / len(scores), 6) if scores else None,
    }


def audit_result_file(path: Path) -> tuple[dict[str, Any], set[str]]:
    records, parse_errors = read_jsonl(path)
    all_keys = {key for record in records for key in record}
    qids = [str(record.get("qid", "")) for record in records if record.get("qid") not in (None, "")]
    duplicate_qids = sum(count - 1 for count in Counter(qids).values() if count > 1)
    target_errors = sum(bool(record.get("target_error")) for record in records)
    judge_errors = sum(bool(record.get("judge_error")) for record in records)
    blank_responses = sum(not str(record.get("target_response", "")).strip() for record in records)
    summary = score_summary(records)

    row = {
        "condition_dir": path.parent.name,
        "relative_path": str(path.relative_to(SOURCE_ROOT)),
        "sha256": sha256(path),
        "bytes": path.stat().st_size,
        "modified_utc": datetime.fromtimestamp(path.stat().st_mtime, tz=timezone.utc).isoformat(),
        "rows": len(records),
        "unique_qids": len(set(qids)),
        "duplicate_qids": duplicate_qids,
        "parse_errors": len(parse_errors),
        "target_errors": target_errors,
        "judge_errors": judge_errors,
        "blank_responses": blank_responses,
        "question_types": " | ".join(unique_values(records, "question_type")),
        "models": " | ".join(unique_values(records, "model")),
        "labels": " | ".join(unique_values(records, "label")),
        **summary,
    }
    return row, all_keys


def write_csv(path: Path, rows: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    if not rows:
        raise RuntimeError(f"No rows available for {path}")
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)


def audit_consolidated_file(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if isinstance(value, dict):
        top_keys = sorted(value)
        value_type = "object"
        item_count = len(value)
    elif isinstance(value, list):
        top_keys = sorted(value[0]) if value and isinstance(value[0], dict) else []
        value_type = "array"
        item_count = len(value)
    else:
        top_keys = []
        value_type = type(value).__name__
        item_count = 1
    return {
        "relative_path": str(path.relative_to(SOURCE_ROOT)),
        "sha256": sha256(path),
        "bytes": path.stat().st_size,
        "value_type": value_type,
        "item_count": item_count,
        "top_keys": " | ".join(top_keys),
    }


def write_report(rows: list[dict[str, Any]], schema_groups: dict[str, list[str]]) -> None:
    report_path = AUDIT_ROOT / "raw_results_audit.md"
    incomplete = [row for row in rows if row["rows"] not in (25, 45, 50, 120, 150, 410, 585)]
    problematic = [
        row
        for row in rows
        if row["parse_errors"]
        or row["duplicate_qids"]
        or row["target_errors"]
        or row["judge_errors"]
        or row["blank_responses"]
        or row["invalid_scores"]
    ]
    question_type_counts: defaultdict[str, int] = defaultdict(int)
    for row in rows:
        question_type_counts[row["question_types"] or "<missing>"] += 1

    lines = [
        "# Raw Results Audit",
        "",
        f"Generated: {datetime.now(timezone.utc).isoformat()}",
        f"Source: `{SOURCE_ROOT}` (read-only)",
        f"Result ledgers found: **{len(rows)}**",
        f"Distinct record schemas: **{len(schema_groups)}**",
        f"Ledgers with parse/duplicate/error/blank/invalid-score findings: **{len(problematic)}**",
        f"Ledgers with non-standard row counts requiring review: **{len(incomplete)}**",
        "",
        "## Question-type coverage",
        "",
    ]
    lines.extend(f"- `{key}`: {count} ledgers" for key, count in sorted(question_type_counts.items()))
    lines.extend(["", "## Problematic ledgers", ""])
    if problematic:
        for row in problematic:
            lines.append(
                "- `{condition_dir}`: rows={rows}, parse={parse_errors}, duplicates={duplicate_qids}, "
                "target_errors={target_errors}, judge_errors={judge_errors}, blank={blank_responses}, "
                "invalid_scores={invalid_scores}".format(**row)
            )
    else:
        lines.append("- None")
    lines.extend(["", "## Non-standard row counts", ""])
    if incomplete:
        lines.extend(f"- `{row['condition_dir']}`: {row['rows']} rows" for row in incomplete)
    else:
        lines.append("- None")
    lines.extend(
        [
            "",
            "## Interpretation",
            "",
            "This audit does not decide which ledgers belong in the publication analysis. It establishes the available raw conditions, their schemas, integrity signals, hashes and record-derived scores. Condition inclusion will be locked explicitly in the next stage.",
            "",
        ]
    )
    report_path.write_text("\n".join(lines), encoding="utf-8")


def main() -> None:
    if not RESULTS_ROOT.is_dir():
        raise FileNotFoundError(f"Missing source results directory: {RESULTS_ROOT}")

    AUDIT_ROOT.mkdir(parents=True, exist_ok=True)
    result_files = sorted(RESULTS_ROOT.glob("*/results.jsonl"))
    if not result_files:
        raise RuntimeError(f"No results.jsonl files found under {RESULTS_ROOT}")

    rows: list[dict[str, Any]] = []
    schemas: defaultdict[str, list[str]] = defaultdict(list)
    for path in result_files:
        row, keys = audit_result_file(path)
        rows.append(row)
        schema_id = hashlib.sha256("\n".join(sorted(keys)).encode("utf-8")).hexdigest()[:12]
        schemas[schema_id].append(row["condition_dir"])

    write_csv(AUDIT_ROOT / "raw_condition_inventory.csv", rows)
    schema_payload = {
        schema_id: {"conditions": conditions}
        for schema_id, conditions in sorted(schemas.items())
    }
    (AUDIT_ROOT / "schema_groups.json").write_text(
        json.dumps(schema_payload, indent=2, sort_keys=True), encoding="utf-8"
    )

    consolidated_rows = [audit_consolidated_file(path) for path in CONSOLIDATED_FILES]
    write_csv(AUDIT_ROOT / "consolidated_source_manifest.csv", consolidated_rows)
    write_report(rows, schemas)

    print(f"Audited {len(rows)} raw result ledgers across {len(schemas)} schemas.")
    print(f"Outputs: {AUDIT_ROOT}")


if __name__ == "__main__":
    main()