"""
loader.py — Ingest SHENRON JSONL output from disk or stdin.
Supports both demo_generator format and full shenron run format.
"""
import json
from pathlib import Path
from typing import List, Dict, Any


def load_jsonl(path: str) -> List[Dict[str, Any]]:
    events = []
    with open(path, "r") as f:
        for line in f:
            line = line.strip()
            if line:
                try:
                    events.append(json.loads(line))
                except json.JSONDecodeError:
                    continue
    return events


def group_by_session(events: List[Dict[str, Any]]) -> Dict[str, List[Dict]]:
    sessions: Dict[str, List[Dict]] = {}
    for ev in events:
        sid = ev.get("session_id") or ev.get("run_id") or "unknown"
        sessions.setdefault(sid, []).append(ev)
    # sort each session by sequence or timestamp
    for sid in sessions:
        sessions[sid].sort(key=lambda e: (e.get("sequence", 0), e.get("timestamp", "")))
    return sessions


def extract_campaign_meta(events: List[Dict[str, Any]]) -> Dict[str, Any]:
    techniques = []
    phases = []
    layers = []
    detection_opportunities = []
    for ev in events:
        techniques.extend(ev.get("mitre_techniques", []))
        phase = ev.get("phase")
        if phase:
            phases.append(phase)
        layer = ev.get("layer")
        if layer:
            layers.append(layer)
        detection_opportunities.extend(ev.get("detection_opportunities", []))
    return {
        "unique_techniques": sorted(set(techniques)),
        "phase_sequence": list(dict.fromkeys(phases)),
        "layers": list(dict.fromkeys(layers)),
        "unique_detection_opportunities": sorted(set(detection_opportunities)),
        "event_count": len(events),
    }
