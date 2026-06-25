"""
runner.py — Drive the full SHENRON-PROBE pipeline against a local Ollama model.
"""
import json
import time
import subprocess
import sys
from pathlib import Path
from typing import List, Dict, Any, Optional

from .loader import load_jsonl, group_by_session, extract_campaign_meta
from .prompt_builder import build_l1_prompt, build_l2_prompt, build_l3_prompt
from .scorer import (
    score_technique_identification,
    score_next_stage_prediction,
    score_detection_proposal,
    aggregate_scores,
)


def query_ollama(model: str, prompt: str, timeout: int = 120) -> Dict[str, Any]:
    payload = json.dumps({"model": model, "prompt": prompt, "stream": False})
    start = time.time()
    try:
        result = subprocess.run(
            ["curl", "-s", "-X", "POST", "http://localhost:11434/api/generate",
             "-H", "Content-Type: application/json", "-d", payload],
            capture_output=True, text=True, timeout=timeout
        )
        latency_ms = int((time.time() - start) * 1000)
        data = json.loads(result.stdout)
        return {"response": data.get("response", ""), "latency_ms": latency_ms, "error": None}
    except Exception as e:
        return {"response": "", "latency_ms": -1, "error": str(e)}


def derive_ground_truth(events: List[Dict[str, Any]], session_events: List[Dict[str, Any]]) -> Dict[str, Any]:
    meta = extract_campaign_meta(events)
    # next stage: use last event's next in full session if available
    all_phases = [e.get("phase", "") for e in session_events if e.get("phase")]
    unique_phases = list(dict.fromkeys(all_phases))
    current_phases = set(e.get("phase", "") for e in events)
    remaining_phases = [p for p in unique_phases if p not in current_phases]
    next_phase = remaining_phases[0] if remaining_phases else unique_phases[-1] if unique_phases else ""

    # next technique: first technique from events not yet seen
    all_techs = []
    for e in session_events:
        all_techs.extend(e.get("mitre_techniques", []))
    seen_techs = set(meta["unique_techniques"])
    next_tech = next((t for t in all_techs if t not in seen_techs), meta["unique_techniques"][-1] if meta["unique_techniques"] else "")

    return {
        "techniques": meta["unique_techniques"],
        "detection_opportunities": meta["unique_detection_opportunities"],
        "next_phase": next_phase,
        "next_technique": next_tech,
        "next_signals": meta["unique_detection_opportunities"][:3],
    }


def run_probe(
    jsonl_path: str,
    model: str,
    levels: List[str] = ["L1", "L2", "L3"],
    max_sessions: int = 5,
    output_dir: str = "results"
) -> List[Dict[str, Any]]:
    print(f"[shenron-probe] Loading: {jsonl_path}")
    events = load_jsonl(jsonl_path)
    sessions = group_by_session(events)
    print(f"[shenron-probe] Sessions found: {len(sessions)} | Model: {model}")

    Path(output_dir).mkdir(parents=True, exist_ok=True)
    all_results = []

    for i, (sid, sevents) in enumerate(list(sessions.items())[:max_sessions]):
        print(f"\n[session {i+1}/{min(max_sessions, len(sessions))}] {sid} ({len(sevents)} events)")

        gt = derive_ground_truth(sevents, sevents)

        for level in levels:
            print(f"  [{level}] Building prompt...")
            if level == "L1":
                prompt = build_l1_prompt(sevents, sid)
            elif level == "L2":
                prompt = build_l2_prompt(sevents, sid)
            elif level == "L3":
                prompt = build_l3_prompt(sevents, sid)
            else:
                continue

            print(f"  [{level}] Querying {model}...")
            resp = query_ollama(model, prompt)

            if resp["error"]:
                print(f"  [{level}] ERROR: {resp['error']}")
                continue

            response_text = resp["response"]

            d1 = score_technique_identification(response_text, gt["techniques"])
            d2 = score_next_stage_prediction(
                response_text,
                gt["next_phase"],
                gt["next_technique"],
                gt["next_signals"],
            )
            d3 = score_detection_proposal(
                response_text,
                gt["techniques"],
                gt["detection_opportunities"],
            )

            agg = aggregate_scores([d1, d2, d3])

            result = {
                "session_id": sid,
                "level": level,
                "model": model,
                "latency_ms": resp["latency_ms"],
                "ground_truth": gt,
                "scores": agg,
                "response_preview": response_text[:500],
            }
            all_results.append(result)

            print(f"  [{level}] aggregate={agg['aggregate_score']} "
                  f"D1={d1['score']} D2={d2['score']} D3={d3['score']} "
                  f"fatal={agg['fatal_error_present']} latency={resp['latency_ms']}ms")

    out_path = Path(output_dir) / f"probe_results_{model.replace(':', '_').replace('/', '_')}.jsonl"
    with open(out_path, "w") as f:
        for r in all_results:
            f.write(json.dumps(r) + "\n")

    print(f"\n[shenron-probe] Results written: {out_path}")
    return all_results
