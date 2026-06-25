"""
report.py — Aggregate results into a human-readable benchmark report.
"""
import json
from pathlib import Path
from typing import List, Dict, Any
from collections import defaultdict


def load_results(results_dir: str) -> List[Dict[str, Any]]:
    results = []
    for p in Path(results_dir).glob("*.jsonl"):
        with open(p) as f:
            for line in f:
                line = line.strip()
                if line:
                    results.append(json.loads(line))
    return results


def build_report(results: List[Dict[str, Any]]) -> str:
    if not results:
        return "No results found."

    by_model: Dict[str, List] = defaultdict(list)
    for r in results:
        by_model[r["model"]].append(r)

    lines = ["=" * 60, "SHENRON-PROBE BENCHMARK REPORT", "=" * 60, ""]

    for model, mrs in sorted(by_model.items()):
        lines.append(f"MODEL: {model}")
        lines.append(f"  Total evaluations: {len(mrs)}")

        by_level: Dict[str, List] = defaultdict(list)
        for r in mrs:
            by_level[r["level"]].append(r)

        for level in ["L1", "L2", "L3"]:
            lvl_results = by_level.get(level, [])
            if not lvl_results:
                continue
            agg_scores = [r["scores"]["aggregate_score"] for r in lvl_results]
            d1 = [r["scores"]["dimension_scores"].get("technique_identification", 0) for r in lvl_results]
            d2 = [r["scores"]["dimension_scores"].get("next_stage_prediction", 0) for r in lvl_results]
            d3 = [r["scores"]["dimension_scores"].get("detection_proposal", 0) for r in lvl_results]
            fatals = sum(1 for r in lvl_results if r["scores"]["fatal_error_present"])
            avg_lat = sum(r["latency_ms"] for r in lvl_results) / len(lvl_results)

            lines.append(f"  [{level}] n={len(lvl_results)}")
            lines.append(f"    aggregate:    {sum(agg_scores)/len(agg_scores):.3f}")
            lines.append(f"    D1 technique: {sum(d1)/len(d1):.3f}")
            lines.append(f"    D2 next_stage:{sum(d2)/len(d2):.3f}")
            lines.append(f"    D3 detection: {sum(d3)/len(d3):.3f}")
            lines.append(f"    fatal_errors: {fatals}/{len(lvl_results)}")
            lines.append(f"    avg_latency:  {avg_lat:.0f}ms")

        lines.append("")

    return "\n".join(lines)
