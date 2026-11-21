"""Local harness for measuring source selection and answer keyword coverage."""

import argparse
import json
import logging
import math
import statistics
import time
from pathlib import Path
from typing import Any

from app.rag.workflow import ask

logger = logging.getLogger(__name__)


def evaluate_dataset(dataset_path: Path) -> dict[str, Any]:
    cases = [
        json.loads(line)
        for line in dataset_path.read_text(encoding="utf-8").splitlines()
        if line.strip() and not line.lstrip().startswith("#")
    ]
    results = []
    durations = []
    for case in cases:
        started = time.perf_counter()
        try:
            response = ask(case["question"])
            duration = time.perf_counter() - started
            durations.append(duration)
            answer = str(response.get("answer", ""))
            expected_terms = [str(term) for term in case.get("expected_terms", [])]
            matched_terms = [term for term in expected_terms if term.casefold() in answer.casefold()]
            results.append({
                "id": case.get("id", ""),
                "source_expected": case["expected_source"],
                "source_actual": response.get("source_used", ""),
                "source_correct": response.get("source_used") == case["expected_source"],
                "expected_terms": expected_terms,
                "matched_terms": matched_terms,
                "term_recall": len(matched_terms) / len(expected_terms) if expected_terms else None,
                "has_citation": bool(response.get("citations")),
                "duration_seconds": round(duration, 3),
            })
        except Exception as exc:
            logger.exception("Evaluation case failed: id=%s", case.get("id", ""))
            results.append({"id": case.get("id", ""), "error": type(exc).__name__})

    successful = [item for item in results if "error" not in item]
    source_accuracy = (
        sum(bool(item["source_correct"]) for item in successful) / len(successful)
        if successful else 0.0
    )
    term_scores = [item["term_recall"] for item in successful if item["term_recall"] is not None]
    sorted_durations = sorted(durations)
    return {
        "dataset": str(dataset_path),
        "case_count": len(cases),
        "successful_cases": len(successful),
        "failed_cases": len(cases) - len(successful),
        "source_accuracy": round(source_accuracy, 4),
        "mean_expected_term_recall": round(statistics.mean(term_scores), 4) if term_scores else None,
        "citation_rate": round(sum(bool(item["has_citation"]) for item in successful) / len(successful), 4) if successful else 0.0,
        "mean_latency_seconds": round(statistics.mean(durations), 3) if durations else None,
        "p95_latency_seconds": round(sorted_durations[max(0, math.ceil(len(sorted_durations) * 0.95) - 1)], 3) if sorted_durations else None,
        "results": results,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--dataset",
        type=Path,
        default=Path("data/evaluations/stage2.jsonl"),
        help="JSONL dataset with id, question, expected_source, and optional expected_terms",
    )
    parser.add_argument("--output", type=Path, help="Optional path to write the JSON report")
    args = parser.parse_args()
    report = evaluate_dataset(args.dataset)
    rendered = json.dumps(report, indent=2, ensure_ascii=False)
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(rendered + "\n", encoding="utf-8")
        print(f"Evaluation report written to {args.output}")
    else:
        print(rendered)


if __name__ == "__main__":
    main()
