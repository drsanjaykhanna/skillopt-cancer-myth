from __future__ import annotations

import csv
import hashlib
import json
import re
import shutil
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from docx import Document
from docx.enum.section import WD_ORIENT, WD_SECTION
from docx.enum.table import WD_CELL_VERTICAL_ALIGNMENT, WD_TABLE_ALIGNMENT
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.oxml import OxmlElement
from docx.oxml.ns import qn
from docx.shared import Inches, Pt


ROOT = Path("/mnt/c/Users/khannas4/Desktop/SkillOpt Publication Build")
FINAL = ROOT / "FINAL_REVIEW_2026-09-04"
TABLES = ROOT / "tables"
AUDIT = ROOT / "audit"
FIGURES = ROOT / "figures_final"
MANUSCRIPT = FINAL / "01_Manuscript.md"
APPENDIX = FINAL / "02_Appendix.md"

PACKAGE_SCRIPTS = (
    "audit_raw_results.py",
    "diagnose_dataset_mapping.py",
    "analyze_native_primary.py",
    "analyze_secondary.py",
    "build_evidence_matrix.py",
    "prepare_manuscript_data.py",
    "resolve_prompt_lineage.py",
    "generate_final_figures.py",
    "extract_word_comments.py",
    "build_final_review_package.py",
)

FIGURE_FILES = {
    "1": "figure_1_architecture.png",
    "2": "figure_2_native_efficacy.png",
    "3": "figure_5_skill_portability.png",
    "4": "figure_4_cross_model.png",
    "5": "figure_6_prompt_strategy.png",
    "6": "figure_7_generalisation.png",
    "S1": "figure_3_learning_dynamics.png",
}


def read_csv(path: Path) -> list[dict[str, str]]:
    with path.open("r", encoding="utf-8", newline="") as handle:
        return list(csv.DictReader(handle))


def fmt(value: str | None, digits: int = 1) -> str:
    if value in (None, ""):
        return "–"
    return f"{float(value):.{digits}f}"


def short_hash(value: str) -> str:
    return value if len(value) <= 15 else value[:12] + "…"


def set_cell_fill(cell: Any, fill: str) -> None:
    properties = cell._tc.get_or_add_tcPr()
    shading = properties.find(qn("w:shd"))
    if shading is None:
        shading = OxmlElement("w:shd")
        properties.append(shading)
    shading.set(qn("w:fill"), fill)


def prevent_row_split(row: Any) -> None:
    properties = row._tr.get_or_add_trPr()
    properties.append(OxmlElement("w:cantSplit"))


def repeat_header(row: Any) -> None:
    properties = row._tr.get_or_add_trPr()
    element = OxmlElement("w:tblHeader")
    element.set(qn("w:val"), "true")
    properties.append(element)


def configure(document: Document) -> None:
    section = document.sections[0]
    section.top_margin = Inches(0.7)
    section.bottom_margin = Inches(0.7)
    section.left_margin = Inches(0.75)
    section.right_margin = Inches(0.75)
    normal = document.styles["Normal"]
    normal.font.name = "Times New Roman"
    normal.font.size = Pt(10.5)
    normal.paragraph_format.line_spacing = 1.12
    normal.paragraph_format.space_after = Pt(5)
    for name, size in (("Title", 18), ("Heading 1", 14), ("Heading 2", 11.5), ("Heading 3", 10.5)):
        style = document.styles[name]
        style.font.name = "Arial"
        style.font.size = Pt(size)
        style.font.bold = True
        style.paragraph_format.keep_with_next = True
        style.paragraph_format.space_before = Pt(9)
        style.paragraph_format.space_after = Pt(4)
    footer = section.footer.paragraphs[0]
    footer.alignment = WD_ALIGN_PARAGRAPH.CENTER
    footer.add_run("SkillOpt manuscript review package · 4 September 2026").font.size = Pt(8)


def landscape(document: Document) -> None:
    section = document.add_section(WD_SECTION.NEW_PAGE)
    section.orientation = WD_ORIENT.LANDSCAPE
    section.page_width, section.page_height = section.page_height, section.page_width
    section.top_margin = Inches(0.55)
    section.bottom_margin = Inches(0.55)
    section.left_margin = Inches(0.55)
    section.right_margin = Inches(0.55)


def inline_markdown(paragraph: Any, text: str) -> None:
    parts = re.split(r"(\*\*.+?\*\*|`.+?`)", text)
    for part in parts:
        if not part:
            continue
        if part.startswith("**") and part.endswith("**"):
            run = paragraph.add_run(part[2:-2])
            run.bold = True
        elif part.startswith("`") and part.endswith("`"):
            run = paragraph.add_run(part[1:-1])
            run.font.name = "Consolas"
            run.font.size = Pt(8.5)
        else:
            paragraph.add_run(part)


def add_table(document: Document, headers: list[str], data: list[list[Any]], font_size: float = 7.2) -> None:
    table = document.add_table(rows=1, cols=len(headers))
    table.style = "Table Grid"
    table.alignment = WD_TABLE_ALIGNMENT.CENTER
    table.autofit = True
    repeat_header(table.rows[0])
    for column, header in enumerate(headers):
        cell = table.rows[0].cells[column]
        cell.text = header
        set_cell_fill(cell, "D9E2F3")
        for run in cell.paragraphs[0].runs:
            run.bold = True
            run.font.name = "Arial"
            run.font.size = Pt(font_size)
    for index, values in enumerate(data):
        row = table.add_row()
        prevent_row_split(row)
        if index % 2:
            for cell in row.cells:
                set_cell_fill(cell, "F3F3F3")
        for column, value in enumerate(values):
            cell = row.cells[column]
            cell.text = str(value)
            cell.vertical_alignment = WD_CELL_VERTICAL_ALIGNMENT.CENTER
            for paragraph in cell.paragraphs:
                paragraph.paragraph_format.space_after = Pt(0)
                for run in paragraph.runs:
                    run.font.name = "Arial"
                    run.font.size = Pt(font_size)


def main_table(number: str) -> tuple[list[str], list[list[Any]], float]:
    if number == "1":
        return ["Component", "Role", "Data / models"], [
            ["Benchmark", "Training and evaluation", "Cancer-Myth: 585 FP questions; 150 NFP controls"],
            ["Primary SkillOpt", "Automated skill learning", "Target: GPT-4o; optimiser: GPT-5.4; judge: GPT-4o"],
            ["Primary test", "Repeated FP evaluation", "Three runs; same 410-question test set"],
            ["Conventional prompts", "Comparators", "No correction instruction; few-shot; rule prompts of three lengths"],
            ["Portability", "Cross-model evaluation", "Seven OpenAI, Google and Meta LLMs"],
            ["Additional tests", "Generalisation and restraint", "New FP questions; valid clinical assumptions"],
        ], 7.5
    if number == "2":
        rows = read_csv(TABLES / "gpt4o_paired_comparisons.csv")
        headers = ["Run", "Baseline, %", "SkillOpt, %", "Difference, pp (95% CI)", "Improved / worsened", "Holm p"]
        data = [[str(index + 1), fmt(row["baseline_pct"]), fmt(row["post_optimisation_pct"]), f"{fmt(row['paired_difference_pp'])} ({fmt(row['bootstrap_ci_low_pp'])} to {fmt(row['bootstrap_ci_high_pp'])})", f"{row['improved_pairs']} / {row['worsened_pairs']}", f"{float(row['holm_adjusted_p']):.2g}"] for index, row in enumerate(rows)]
        return headers, data, 7.2
    if number == "3":
        rows = read_csv(TABLES / "core_intervention_grid.csv")
        by_model: dict[str, dict[str, dict[str, str]]] = {}
        for row in rows:
            by_model.setdefault(row["model"], {})[row["intervention"]] = row
        interventions = ["No added skill", "Size-matched few-shot examples", "Primary GPT-4o learned skill", "Compact learned skill"]
        labels = ["No instruction", "Few-shot", "Full SkillOpt", "Compact SkillOpt"]
        headers = ["Model"] + [f"{label}\nFP / NFP" for label in labels]
        data = []
        for model in ["Llama 3.1 8B", "Gemini 2.5 Flash", "Llama 3.3 70B", "GPT-4o", "GPT-5.4", "Gemini 3.5 Flash", "GPT-5.6 Luna"]:
            values = [model]
            for intervention in interventions:
                row = by_model.get(model, {}).get(intervention)
                values.append("–" if not row or not row["correction_pct"] else f"{fmt(row['correction_pct'])} / {fmt(row['specificity_pct'])}")
            data.append(values)
        return headers, data, 7.0
    raise KeyError(number)


def appendix_table(name: str) -> tuple[list[str], list[list[Any]], float]:
    if name == "TABLE_COMPLETE_LEDGER_REGISTRY":
        rows = read_csv(TABLES / "complete_ledger_registry.csv")
        return ["Family", "Condition", "Type", "Model", "Rows / scored", "Status", "Finding", "SHA-256"], [[r["family"], r["condition_dir"], r["question_type"], r["model"], f"{r['rows']} / {r['scored_rows']}", r["status"], r["integrity_findings"], short_hash(r["sha256"])] for r in rows], 5.2
    if name == "TABLE_SOURCE_REGISTRY":
        rows = read_csv(AUDIT / "locked_source_registry.csv")
        return ["Run", "Condition", "Rows", "Result SHA-256", "Summary SHA-256"], [[r["run"], r["condition"], r["rows"], short_hash(r["results_sha256"]), short_hash(r["summary_sha256"])] for r in rows], 6.4
    if name == "TABLE_NATIVE_LEARNING":
        rows = read_csv(TABLES / "native_learning_summary.csv")
        return ["Experiment", "Target", "Optimiser", "Steps", "Accepted", "Baseline", "Final", "Change", "Skill chars", "Status"], [[r["label"], r["target_model"], r["optimizer_model"], f"{r['observed_steps']}/{r['planned_steps']}", r["accepted_rewrites"], fmt(r["baseline_pct"]), fmt(r["final_pct"]), fmt(r["delta_pp"]), r["skill_characters"] or "–", r["status"]] for r in rows], 5.7
    if name == "TABLE_PRIMARY_PERFORMANCE":
        rows = read_csv(TABLES / "primary_performance.csv")
        return ["Run", "Condition", "Success / N", "% (95% CI)"], [[r["run"], r["condition"], f"{r['successes']} / {r['n_total']}", f"{fmt(r['estimate_pct'])} ({fmt(r['ci_low_pct'])}–{fmt(r['ci_high_pct'])})"] for r in rows], 7.2
    if name == "TABLE_PRIMARY_COMPARISONS":
        return main_table("2")
    if name == "TABLE_CATEGORY_PERFORMANCE":
        rows = read_csv(TABLES / "category_performance.csv")
        return ["Category", "Run", "N", "Baseline %", "SkillOpt %", "Difference, pp (95% CI)"], [[r["category"], r["run"], r["n"], fmt(r["baseline_pct"]), fmt(r["post_pct"]), f"{fmt(r['difference_pp'])} ({fmt(r['difference_ci_low_pp'])} to {fmt(r['difference_ci_high_pp'])})"] for r in rows], 6.1
    if name == "TABLE_ITEM_CONSISTENCY":
        rows = read_csv(TABLES / "item_consistency_matrix.csv")
        return ["Successful baseline runs", "Successful SkillOpt runs", "Questions"], [[r["baseline_successes_across_3"], r["post_successes_across_3"], r["questions"]] for r in rows], 7.5
    if name == "TABLE_PROMPT_ARTIFACTS":
        rows = read_csv(TABLES / "prompt_artifact_registry.csv")
        return ["Artifact", "Path", "Characters", "Words", "SHA-256", "Provenance"], [[r["artifact"], r["relative_path"], r["characters"], r["words"], short_hash(r["sha256"]), r["provenance"]] for r in rows], 6.2
    if name == "TABLE_PROMPT_LINEAGE":
        rows = read_csv(TABLES / "prompt_lineage_registry.csv")
        return ["Condition", "Model", "Type", "Full artifact", "Chars", "Lineage", "Ledger SHA-256"], [[r["condition_dir"], r["model"], r["question_type"], r["full_artifact"], r["full_artifact_characters"] or "–", r["lineage_status"], short_hash(r["ledger_sha256"])] for r in rows], 5.2
    if name == "TABLE_SECONDARY_HELDOUT":
        rows = read_csv(TABLES / "secondary_heldout_performance.csv")
        return ["Family", "Intervention", "Model", "Outcome", "N", "Success", "Conservative % (95% CI)", "Available %", "Missing", "SHA-256"], [[r["family"], r["intervention"], r["model"], r["outcome"], r["n_expected"], r["successes_conservative"], f"{fmt(r['estimate_pct_conservative'])} ({fmt(r['ci_low_pct_conservative'])}–{fmt(r['ci_high_pct_conservative'])})", fmt(r["estimate_pct_available"]), r["missing_or_invalid"], short_hash(r["sha256"])] for r in rows], 5.0
    if name in {"TABLE_CORE_INTERVENTION", "TABLE_PROMPT_STRATEGY"}:
        filename = "core_intervention_grid.csv" if name == "TABLE_CORE_INTERVENTION" else "prompt_strategy_grid.csv"
        rows = read_csv(TABLES / filename)
        return ["Model", "Intervention", "FP correction % (95% CI)", "NFP accuracy % (95% CI)", "Missing FP / NFP"], [[r["model"], r["intervention"], f"{fmt(r['correction_pct'])} ({fmt(r['correction_low_pct'])}–{fmt(r['correction_high_pct'])})" if r["correction_pct"] else "–", f"{fmt(r['specificity_pct'])} ({fmt(r['specificity_low_pct'])}–{fmt(r['specificity_high_pct'])})" if r["specificity_pct"] else "–", f"{r['correction_missing'] or '0'} / {r['specificity_missing'] or '0'}"] for r in rows], 6.1
    if name == "TABLE_COMPOSITE":
        rows = [r for r in read_csv(TABLES / "secondary_heldout_performance.csv") if r["family"] == "Composite intervention"]
        return ["Model", "Outcome", "Success / N", "% (95% CI)", "Missing"], [[r["model"], r["outcome"], f"{r['successes_conservative']} / {r['n_expected']}", f"{fmt(r['estimate_pct_conservative'])} ({fmt(r['ci_low_pct_conservative'])}–{fmt(r['ci_high_pct_conservative'])})", r["missing_or_invalid"]] for r in rows], 7.0
    if name == "TABLE_SKILL_THEMES":
        rows = read_csv(TABLES / "independent_skill_themes.csv")
        return ["Skill", "Feature", "Present", "Matches", "Characters"], [[r["skill"], r["theme"], "Yes" if r["present"] == "1" else "No", r["match_count"], r["skill_characters"]] for r in rows], 7.0
    if name == "TABLE_SKILL_PORTABILITY":
        rows = read_csv(TABLES / "independent_skill_portability.csv")
        return ["Skill", "Model", "FP correction % (95% CI)", "Missing"], [[r["skill"], r["recipient_model"], f"{fmt(r['correction_pct'])} ({fmt(r['ci_low_pct'])}–{fmt(r['ci_high_pct'])})", r["missing_or_invalid"]] for r in rows], 7.0
    if name == "TABLE_GENERALISATION":
        rows = read_csv(TABLES / "generalisation_summary.csv")
        return ["Set", "Model", "Condition", "N", "Correct %", "Missing"], [[r["set"], r["model"], r["arm"], r["n"], fmt(r["success_pct"]), r["missing_or_invalid"]] for r in rows], 6.6
    if name == "TABLE_JUDGE_SENSITIVITY":
        rows = read_csv(TABLES / "automated_judge_sensitivity.csv")
        return ["Sample", "Alternative judge", "N", "Agreement %", "GPT-4o %", "Alternative %", "Difference, pp"], [[r["design"], r["judge_model"], r["n_valid"], fmt(r["agreement_pct"]), fmt(r["primary_judge_correction_pct"]), fmt(r["alternative_judge_correction_pct"]), fmt(r["difference_pp"])] for r in rows], 6.6
    raise KeyError(name)


def add_figure(document: Document, key: str) -> None:
    paragraph = document.add_paragraph()
    paragraph.alignment = WD_ALIGN_PARAGRAPH.CENTER
    paragraph.paragraph_format.keep_with_next = True
    paragraph.add_run().add_picture(str(FIGURES / FIGURE_FILES[key]), width=Inches(6.65 if key != "S1" else 9.3))


def render(document: Document, text: str, appendix: bool = False) -> None:
    lines = text.splitlines()
    index = 0
    skipped_title = False
    while index < len(lines):
        stripped = lines[index].strip()
        if not stripped:
            index += 1
            continue
        figure_match = re.fullmatch(r"<!-- INSERT FIGURE (\d+) HERE -->", stripped)
        appendix_figure = re.fullmatch(r"\[\[INSERT_FIGURE_(S\d+)\]\]", stripped)
        table_match = re.fullmatch(r"<!-- INSERT TABLE (\d+) HERE -->", stripped)
        placeholder = re.fullmatch(r"\[\[(TABLE_[A-Z0-9_]+)\]\]", stripped)
        if figure_match:
            add_figure(document, figure_match.group(1))
        elif appendix_figure:
            add_figure(document, appendix_figure.group(1))
        elif table_match:
            add_table(document, *main_table(table_match.group(1)))
        elif placeholder:
            add_table(document, *appendix_table(placeholder.group(1)))
        elif stripped.startswith("<!--"):
            pass
        elif stripped.startswith("# "):
            if not skipped_title:
                skipped_title = True
            else:
                document.add_heading(stripped[2:], level=1)
        elif stripped.startswith("## "):
            document.add_heading(stripped[3:], level=1)
        elif stripped.startswith("### "):
            document.add_heading(stripped[4:], level=2)
        elif stripped.startswith("- "):
            paragraph = document.add_paragraph(style="List Bullet")
            inline_markdown(paragraph, stripped[2:])
        elif stripped.startswith("|"):
            table_lines = []
            while index < len(lines) and lines[index].strip().startswith("|"):
                table_lines.append(lines[index].strip())
                index += 1
            if len(table_lines) >= 3:
                headers = [cell.strip() for cell in table_lines[0].strip("|").split("|")]
                data = [[cell.strip() for cell in row.strip("|").split("|")] for row in table_lines[2:]]
                add_table(document, headers, data, 7.0)
            continue
        elif stripped.startswith("> "):
            paragraph = document.add_paragraph()
            run = paragraph.add_run(stripped[2:])
            run.italic = True
        else:
            paragraph = document.add_paragraph()
            if stripped.startswith("**Figure") or stripped.startswith("**Table") or stripped.startswith("**Legend"):
                paragraph.paragraph_format.keep_with_next = False
                paragraph.paragraph_format.space_after = Pt(8)
            inline_markdown(paragraph, stripped)
        index += 1


def build_document(source: Path, destination: Path, is_appendix: bool) -> None:
    document = Document()
    configure(document)
    source_text = source.read_text(encoding="utf-8")
    source_lines = source_text.splitlines()
    title = source_lines[0].removeprefix("# ")
    title_paragraph = document.add_paragraph(style="Title")
    title_paragraph.alignment = WD_ALIGN_PARAGRAPH.CENTER
    title_paragraph.add_run(title)
    if is_appendix:
        paper_title = document.add_paragraph(source_lines[2].removeprefix("## "))
        paper_title.alignment = WD_ALIGN_PARAGRAPH.CENTER
        paper_title.runs[0].bold = True
        document.add_paragraph(source_lines[4]).alignment = WD_ALIGN_PARAGRAPH.CENTER
        document.add_page_break()
        landscape(document)
        source_text = "\n".join([source_lines[0], *source_lines[6:]])
    render(document, source_text, appendix=is_appendix)
    destination.parent.mkdir(parents=True, exist_ok=True)
    document.save(destination)


def file_sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def package_supporting_materials() -> None:
    shutil.copytree(FIGURES, FINAL / "05_Figures", dirs_exist_ok=True)
    shutil.copytree(TABLES, FINAL / "06_Tables_CSV", dirs_exist_ok=True)
    script_destination = FINAL / "07_Reproducibility_Scripts"
    script_destination.mkdir(exist_ok=True)
    for filename in PACKAGE_SCRIPTS:
        shutil.copy2(ROOT / "scripts" / filename, script_destination / filename)
    shutil.copytree(AUDIT, FINAL / "08_Audit", dirs_exist_ok=True)

    manuscript_document = Document(FINAL / "SkillOpt_Manuscript_REVIEW.docx")
    appendix_document = Document(FINAL / "SkillOpt_Appendix_REVIEW.docx")
    citation_tags = sorted(set(re.findall(r"\[REF-[^]]+\]", MANUSCRIPT.read_text(encoding="utf-8"))))
    validation = {
        "generated_utc": datetime.now(timezone.utc).isoformat(),
        "manuscript": {
            "tables": len(manuscript_document.tables),
            "figures": len(manuscript_document.inline_shapes),
            "citation_tags": citation_tags,
        },
        "appendix": {
            "tables": len(appendix_document.tables),
            "figures": len(appendix_document.inline_shapes),
        },
        "supporting_materials": {
            "figure_files": sum(path.is_file() for path in (FINAL / "05_Figures").rglob("*")),
            "table_files": sum(path.is_file() for path in (FINAL / "06_Tables_CSV").rglob("*")),
            "script_files": sum(path.is_file() for path in script_destination.rglob("*")),
            "audit_files": sum(path.is_file() for path in (FINAL / "08_Audit").rglob("*")),
        },
        "unresolved_before_submission": [
            "Reconcile 250 human-review records and agreement calculation.",
            "Replace citation tags with live Zotero citations.",
            "Complete funding, competing-interest and ethics statements.",
        ],
    }
    (FINAL / "09_Validation_Report.json").write_text(json.dumps(validation, indent=2) + "\n", encoding="utf-8")

    readme = """# SkillOpt final review package

## Start here

- `SkillOpt_Manuscript_REVIEW.docx`: review manuscript with six figures and three tables embedded at first mention.
- `SkillOpt_Appendix_REVIEW.docx`: comprehensive appendix with one supplementary figure and 17 tables.
- `01_Manuscript.md` and `02_Appendix.md`: editable source text.
- `03_Comment_Response_Log.md`: disposition of all Word and Markdown review comments.
- `04_Zotero_Citation_Register.md`: verified lookup targets for every citation tag.

## Supporting material

- `05_Figures/`: seven figures in PDF, SVG, PNG and TIFF, exact source CSVs and SHA-256 manifest.
- `06_Tables_CSV/`: all 20 analytical tables used by the manuscript and appendix.
- `07_Reproducibility_Scripts/`: controlling audit, analysis, figure and document-generation scripts.
- `08_Audit/`: evidence inventory, locked-source registry, provenance decisions and preserved review snapshots.
- `09_Validation_Report.json`: document and package checks.
- `10_Package_Manifest.csv`: SHA-256 hash and size for every packaged file except the manifest itself.

## Status

This is review-ready, not submission-final. Citation tags remain visible for Zotero insertion. Human-review records are excluded until their labels and agreement denominator are reconciled. Funding, competing-interest and ethics statements require author completion.

The original source project was not modified.
"""
    (FINAL / "00_README.md").write_text(readme, encoding="utf-8")

    manifest_path = FINAL / "10_Package_Manifest.csv"
    paths = sorted(path for path in FINAL.rglob("*") if path.is_file() and path != manifest_path)
    with manifest_path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.writer(handle)
        writer.writerow(["relative_path", "bytes", "sha256"])
        for path in paths:
            writer.writerow([path.relative_to(FINAL).as_posix(), path.stat().st_size, file_sha256(path)])


def main() -> None:
    build_document(MANUSCRIPT, FINAL / "SkillOpt_Manuscript_REVIEW.docx", False)
    build_document(APPENDIX, FINAL / "SkillOpt_Appendix_REVIEW.docx", True)
    package_supporting_materials()
    print("Built final review documents")


if __name__ == "__main__":
    main()
