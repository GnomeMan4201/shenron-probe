"""
scorer.py — Score LLM responses against SHENRON ground truth across 3 dimensions.
"""
import re
from typing import Dict, Any, List


def score_technique_identification(
    llm_response: str,
    ground_truth_techniques: List[str]
) -> Dict[str, Any]:
    """
    Dimension 1: Did the LLM correctly identify the MITRE techniques?
    Partial credit per technique identified.
    """
    response_upper = llm_response.upper()
    hits = []
    misses = []
    for tech in ground_truth_techniques:
        tech_id = tech.upper().replace(".", "\\.")
        pattern = rf"\bT\d{{4}}(?:\.\d{{3}})?\b"
        # check by technique ID or common name
        if re.search(tech.upper(), response_upper) or tech.upper() in response_upper:
            hits.append(tech)
        else:
            misses.append(tech)

    total = len(ground_truth_techniques)
    score = len(hits) / total if total > 0 else 0.0

    return {
        "dimension": "technique_identification",
        "score": round(score, 3),
        "hits": hits,
        "misses": misses,
        "total_techniques": total,
        "techniques_found": len(hits),
    }


def score_next_stage_prediction(
    llm_response: str,
    actual_next_phase: str,
    actual_next_technique: str,
    actual_next_signals: List[str]
) -> Dict[str, Any]:
    """
    Dimension 2: Did the LLM correctly predict the next stage?
    3 sub-criteria: phase, technique, signal keyword.
    """
    resp_upper = llm_response.upper()

    phase_hit = actual_next_phase.upper() in resp_upper if actual_next_phase else False
    technique_hit = actual_next_technique.upper() in resp_upper if actual_next_technique else False
    signal_hits = [s for s in actual_next_signals if s.upper() in resp_upper]
    signal_score = len(signal_hits) / len(actual_next_signals) if actual_next_signals else 0.0

    sub_scores = [
        1.0 if phase_hit else 0.0,
        1.0 if technique_hit else 0.0,
        signal_score,
    ]
    score = sum(sub_scores) / len(sub_scores)

    return {
        "dimension": "next_stage_prediction",
        "score": round(score, 3),
        "phase_hit": phase_hit,
        "technique_hit": technique_hit,
        "signal_hits": signal_hits,
        "expected_phase": actual_next_phase,
        "expected_technique": actual_next_technique,
        "expected_signals": actual_next_signals,
    }


def score_detection_proposal(
    llm_response: str,
    ground_truth_techniques: List[str],
    ground_truth_detection_opportunities: List[str]
) -> Dict[str, Any]:
    """
    Dimension 3: Did the LLM produce a valid Sigma rule targeting the right technique?
    Rubric: structure (title/logsource/detection/falsepositives), technique alignment, opportunity coverage.
    Fatal errors: wrong technique family, no detection block, placeholder-only content.
    """
    resp_upper = llm_response.upper()
    resp_lower = llm_response.lower()

    # structural criteria
    has_title = "title:" in resp_lower
    has_logsource = "logsource:" in resp_lower
    has_detection = "detection:" in resp_lower
    has_condition = "condition:" in resp_lower
    has_falsepositives = "falsepositives:" in resp_lower
    structure_score = sum([has_title, has_logsource, has_detection, has_condition, has_falsepositives]) / 5.0

    # technique alignment
    technique_hit = any(t.upper() in resp_upper for t in ground_truth_techniques)

    # detection opportunity coverage
    opp_hits = [o for o in ground_truth_detection_opportunities if o.lower().replace("_", " ") in resp_lower or o.lower() in resp_lower]
    opp_score = len(opp_hits) / len(ground_truth_detection_opportunities) if ground_truth_detection_opportunities else 0.0

    # fatal errors
    is_placeholder = "your_field_here" in resp_lower or "example.com" in resp_lower
    no_detection_block = not has_detection
    fatal_error = is_placeholder or no_detection_block

    if fatal_error:
        score = 0.0
    else:
        score = (structure_score * 0.4) + (1.0 if technique_hit else 0.0) * 0.4 + opp_score * 0.2

    return {
        "dimension": "detection_proposal",
        "score": round(score, 3),
        "structure_score": round(structure_score, 3),
        "technique_aligned": technique_hit,
        "opportunity_coverage": round(opp_score, 3),
        "opportunity_hits": opp_hits,
        "fatal_error": fatal_error,
        "fatal_reason": "placeholder or missing detection block" if fatal_error else None,
        "sigma_fields": {
            "title": has_title,
            "logsource": has_logsource,
            "detection": has_detection,
            "condition": has_condition,
            "falsepositives": has_falsepositives,
        }
    }


def aggregate_scores(dim_results: List[Dict[str, Any]]) -> Dict[str, Any]:
    scores = [d["score"] for d in dim_results]
    avg = sum(scores) / len(scores) if scores else 0.0
    fatal = any(d.get("fatal_error") for d in dim_results)
    return {
        "aggregate_score": round(avg, 3),
        "fatal_error_present": fatal,
        "dimension_scores": {d["dimension"]: d["score"] for d in dim_results},
        "dimensions": dim_results,
    }
