from __future__ import annotations

import csv
import json
import xml.etree.ElementTree as ET
from pathlib import Path
from zipfile import ZipFile


DOCX = Path("/home/khannas4/SkillOpt Publication Build/output_full/SkillOpt_full_manuscript.docx")
OUTPUT_ROOT = Path("/mnt/c/Users/khannas4/Desktop/SkillOpt Publication Build/audit")
W = "{http://schemas.openxmlformats.org/wordprocessingml/2006/main}"


def comment_records(zip_file: ZipFile) -> dict[str, dict[str, str]]:
    root = ET.fromstring(zip_file.read("word/comments.xml"))
    records: dict[str, dict[str, str]] = {}
    for comment in root.findall(f"{W}comment"):
        comment_id = comment.attrib[f"{W}id"]
        text = "".join(node.text or "" for node in comment.iter(f"{W}t")).strip()
        records[comment_id] = {
            "comment_id": comment_id,
            "author": comment.attrib.get(f"{W}author", ""),
            "date": comment.attrib.get(f"{W}date", ""),
            "comment": text,
            "anchor": "",
            "paragraph": "",
            "paragraph_number": "",
        }
    return records


def paragraph_text(paragraph: ET.Element) -> str:
    return "".join(node.text or "" for node in paragraph.iter(f"{W}t")).strip()


def collect_anchors(document_root: ET.Element, records: dict[str, dict[str, str]]) -> None:
    active: set[str] = set()
    paragraph_number = 0

    def walk(element: ET.Element, anchors: dict[str, list[str]]) -> None:
        for child in element:
            if child.tag == f"{W}commentRangeStart":
                active.add(child.attrib[f"{W}id"])
            elif child.tag == f"{W}commentRangeEnd":
                active.discard(child.attrib[f"{W}id"])
            elif child.tag == f"{W}t":
                for comment_id in active:
                    anchors.setdefault(comment_id, []).append(child.text or "")
            else:
                walk(child, anchors)

    for paragraph in document_root.iter(f"{W}p"):
        paragraph_number += 1
        text = paragraph_text(paragraph)
        anchors: dict[str, list[str]] = {}
        active_at_start = set(active)
        walk(paragraph, anchors)
        referenced = active_at_start | set(anchors)
        for comment_id in referenced:
            if comment_id not in records:
                continue
            anchor_piece = "".join(anchors.get(comment_id, [])).strip()
            if anchor_piece:
                existing = records[comment_id]["anchor"]
                records[comment_id]["anchor"] = f"{existing} {anchor_piece}".strip()
            if text and not records[comment_id]["paragraph"]:
                records[comment_id]["paragraph"] = text
                records[comment_id]["paragraph_number"] = str(paragraph_number)


def write_outputs(records: list[dict[str, str]]) -> None:
    OUTPUT_ROOT.mkdir(parents=True, exist_ok=True)
    csv_path = OUTPUT_ROOT / "reviewed_manuscript_comments.csv"
    with csv_path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(records[0]))
        writer.writeheader()
        writer.writerows(records)

    json_path = OUTPUT_ROOT / "reviewed_manuscript_comments.json"
    json_path.write_text(json.dumps(records, indent=2, ensure_ascii=False), encoding="utf-8")

    lines = [
        "# Reviewed manuscript comments",
        "",
        f"Source: `{DOCX}`",
        f"Comments extracted: **{len(records)}**",
        "",
    ]
    for index, record in enumerate(records, start=1):
        lines.extend(
            [
                f"## {index}. Comment {record['comment_id']}",
                "",
                f"- **Author:** {record['author'] or 'Unknown'}",
                f"- **Date:** {record['date'] or 'Not recorded'}",
                f"- **Paragraph:** {record['paragraph_number'] or 'Not resolved'}",
                f"- **Selected text:** {record['anchor'] or '[No range text recovered]'}",
                "",
                f"> {record['comment']}",
                "",
                "**Paragraph context**",
                "",
                record["paragraph"] or "[No paragraph context recovered]",
                "",
            ]
        )
    (OUTPUT_ROOT / "reviewed_manuscript_comments.md").write_text("\n".join(lines), encoding="utf-8")


def main() -> None:
    with ZipFile(DOCX) as zip_file:
        records_by_id = comment_records(zip_file)
        document_root = ET.fromstring(zip_file.read("word/document.xml"))
    collect_anchors(document_root, records_by_id)
    records = sorted(records_by_id.values(), key=lambda row: int(row["comment_id"]))
    if not records:
        raise RuntimeError("No comments found")
    write_outputs(records)
    print(f"Extracted {len(records)} comments from {DOCX}")
    print(f"Anchors recovered: {sum(bool(record['anchor']) for record in records)}/{len(records)}")


if __name__ == "__main__":
    main()
