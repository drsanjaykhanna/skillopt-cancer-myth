from __future__ import annotations

import json
from collections import Counter
from pathlib import Path


ROOT = Path("/home/khannas4/ESMO AI 2026/ai-congress")


def load_jsonl(path: Path) -> list[dict]:
    with path.open("r", encoding="utf-8") as handle:
        return [json.loads(line) for line in handle if line.strip()]


def normalize(text: str) -> str:
    return " ".join(str(text).split()).strip()


def main() -> None:
    official = json.loads((ROOT / "cancer-myth/data/all_data.json").read_text(encoding="utf-8"))
    flat = load_jsonl(ROOT / "data/cancer_myth.jsonl")
    split = json.loads(
        (
            ROOT
            / "results/skillopt_v2_gpt4o/_generated_splits/cancermyth_2-1-7_seed42/test/items.json"
        ).read_text(encoding="utf-8")
    )

    official_by_qid = {str(item["QID"]): item for item in official}
    flat_by_qid = {str(item["QID"]): item for item in flat}
    official_by_question = {normalize(item["example_question"]): item for item in official}
    flat_by_question = {normalize(item["question"]): item for item in flat}

    split_qids = {str(item["id"]) for item in split}
    split_questions = {normalize(item["question"]) for item in split}

    question_overlap = set(official_by_question) & set(flat_by_question)
    qid_overlap = set(official_by_qid) & set(flat_by_qid)
    qid_question_agreement = sum(
        normalize(official_by_qid[qid]["example_question"]) == normalize(flat_by_qid[qid]["question"])
        for qid in qid_overlap
    )
    split_flat_qid_overlap = split_qids & set(flat_by_qid)
    split_flat_question_overlap = split_questions & set(flat_by_question)

    print(
        json.dumps(
            {
                "official": {
                    "n": len(official),
                    "unique_qids": len(official_by_qid),
                    "qid_min": min(int(qid) for qid in official_by_qid),
                    "qid_max": max(int(qid) for qid in official_by_qid),
                    "unique_questions": len(official_by_question),
                },
                "flat": {
                    "n": len(flat),
                    "unique_qids": len(flat_by_qid),
                    "qid_min": min(int(qid) for qid in flat_by_qid),
                    "qid_max": max(int(qid) for qid in flat_by_qid),
                    "unique_questions": len(flat_by_question),
                },
                "official_flat": {
                    "qid_overlap": len(qid_overlap),
                    "question_overlap": len(question_overlap),
                    "same_question_at_same_qid": qid_question_agreement,
                },
                "split": {
                    "n": len(split),
                    "unique_ids": len(split_qids),
                    "unique_questions": len(split_questions),
                    "flat_qid_overlap": len(split_flat_qid_overlap),
                    "flat_question_overlap": len(split_flat_question_overlap),
                },
                "flat_qid_prefixes": Counter(str(item["QID"]).split("_")[0] for item in flat),
            },
            indent=2,
        )
    )

    for relative in (
        "results/skillopt_v2_gpt4o/test_eval_baseline/results.jsonl",
        "results/skillopt_v2_gpt4o/test_eval/results.jsonl",
    ):
        path = ROOT / relative
        records = load_jsonl(path)
        print(f"\n{relative}")
        print(f"rows={len(records)} keys={sorted(records[0])}")
        print(f"first={json.dumps(records[0], ensure_ascii=False)[:1000]}")


if __name__ == "__main__":
    main()