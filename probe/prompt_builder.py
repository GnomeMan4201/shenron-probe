"""
prompt_builder.py — Build L1/L2/L3 prompts from SHENRON campaign sessions.
Includes max_events truncation to prevent Ollama timeouts on large campaigns.
"""
import json
import random
from typing import List, Dict, Any
from .loader import extract_campaign_meta

BENIGN_NOISE = [
    {"layer": "syslogd", "signal": "logrotate_cycle", "mitre_techniques": [], "behavior_class": "log_rotation", "description": "Routine log rotation — no anomaly"},
    {"layer": "cron", "signal": "cron_heartbeat", "mitre_techniques": [], "behavior_class": "scheduled_maintenance", "description": "Daily apt cache cleanup scheduled task"},
    {"layer": "networkd", "signal": "dhcp_renew", "mitre_techniques": [], "behavior_class": "dhcp_renewal", "description": "DHCP lease renewal on primary interface"},
    {"layer": "systemd", "signal": "unit_start", "mitre_techniques": [], "behavior_class": "service_start", "description": "cups.service started — print spooler"},
    {"layer": "auditd", "signal": "user_login", "mitre_techniques": [], "behavior_class": "normal_auth", "description": "User login via SSH key — authorized"},
]

MAX_EVENTS_L1 = 20
MAX_EVENTS_L2 = 15
MAX_EVENTS_L3 = 15


def _sample_events(events: List[Dict], max_n: int) -> List[Dict]:
    """Sample events preserving phase distribution if truncating."""
    if len(events) <= max_n:
        return events
    # take first 2 and last 2, sample rest proportionally
    by_phase = {}
    for ev in events:
        p = ev.get("phase", "unknown")
        by_phase.setdefault(p, []).append(ev)
    sampled = []
    per_phase = max(1, max_n // max(len(by_phase), 1))
    for phase_evs in by_phase.values():
        sampled.extend(phase_evs[:per_phase])
    return sorted(sampled[:max_n], key=lambda e: (e.get("sequence", 0), e.get("timestamp", "")))


def build_l1_prompt(events: List[Dict[str, Any]], session_id: str) -> str:
    events = _sample_events(events, MAX_EVENTS_L1)
    meta = extract_campaign_meta(events)
    phases = meta["phase_sequence"]
    techniques = meta["unique_techniques"]
    layers = meta["layers"]
    detections = meta["unique_detection_opportunities"]

    summary_lines = []
    for ev in events:
        t = ev.get("mitre_technique") or (ev.get("mitre_techniques") or ["unknown"])[0]
        desc = ev.get("description") or ev.get("behavior_class", "")
        phase = ev.get("phase", "")
        summary_lines.append(f"  [{phase}] {t} — {desc}")

    summary = "\n".join(summary_lines)

    return f"""You are a senior detection engineer analyzing a synthetic adversary campaign.

CAMPAIGN SUMMARY (session: {session_id})
Total events: {meta['event_count']}
Phase sequence: {' -> '.join(phases)}
MITRE techniques observed: {', '.join(techniques)}
Layers activated: {', '.join(layers[:8])}{'...' if len(layers) > 8 else ''}
Detection opportunities flagged: {', '.join(detections[:6])}{'...' if len(detections) > 6 else ''}

EVENT SEQUENCE:
{summary}

Answer the following three questions. Be specific and technical. Do not hedge.

QUESTION 1 — TECHNIQUE IDENTIFICATION:
Which MITRE ATT&CK techniques are present in this campaign? For each technique, name the tactic it belongs to and explain what the adversary was doing.

QUESTION 2 — NEXT STAGE PREDICTION:
Based on the phase sequence and techniques observed, what is the most likely next adversary action? Name the technique, the phase it belongs to, and what telemetry signal would indicate it.

QUESTION 3 — DETECTION PROPOSAL:
Write a Sigma rule that would detect the most critical technique in this campaign. The rule must include: title, status, logsource, detection condition, and falsepositives.
"""


def build_l2_prompt(events: List[Dict[str, Any]], session_id: str) -> str:
    events = _sample_events(events, MAX_EVENTS_L2)
    raw_lines = []
    for ev in events:
        scrubbed = {k: v for k, v in ev.items() if k not in (
            "mitre_technique", "mitre_techniques", "detection_opportunities",
            "behavior_class", "artifact_id", "artifact_hash", "generator", "note",
            "safety", "simulation_only", "executable", "payload_present"
        )}
        raw_lines.append(json.dumps(scrubbed))

    raw_log = "\n".join(raw_lines)

    return f"""You are a senior detection engineer. You have been handed raw telemetry logs from a host.
Analyze them and answer the three questions below. No techniques are labeled for you.

RAW TELEMETRY (session: {session_id}):
{raw_log}

QUESTION 1 — TECHNIQUE IDENTIFICATION:
Which MITRE ATT&CK techniques are present in these logs? For each, name the tactic and explain your reasoning from the log fields.

QUESTION 2 — NEXT STAGE PREDICTION:
What is the most likely next adversary action given what you observe? Name the technique, expected phase, and what new log fields or signals would appear.

QUESTION 3 — DETECTION PROPOSAL:
Write a Sigma rule for the most critical technique you identified. Include: title, status, logsource, detection, and falsepositives.
"""


def build_l3_prompt(events: List[Dict[str, Any]], session_id: str, noise_ratio: float = 0.3) -> str:
    events = _sample_events(events, MAX_EVENTS_L3)
    n_noise = max(1, int(len(events) * noise_ratio))
    noise_events = random.choices(BENIGN_NOISE, k=n_noise)

    mixed = []
    for ev in events:
        scrubbed = {k: v for k, v in ev.items() if k not in (
            "mitre_technique", "mitre_techniques", "detection_opportunities",
            "behavior_class", "artifact_id", "artifact_hash", "generator", "note",
            "safety", "simulation_only", "executable", "payload_present"
        )}
        scrubbed["_source"] = "host_telemetry"
        mixed.append(scrubbed)

    for n in noise_events:
        n["_source"] = "host_telemetry"
        mixed.append(n)

    random.shuffle(mixed)
    raw_log = "\n".join(json.dumps(e) for e in mixed)

    return f"""You are a senior detection engineer triaging a mixed telemetry stream.
Some events are benign system activity. Some are adversarial. You must separate them.

RAW TELEMETRY (session: {session_id}, contains benign noise):
{raw_log}

QUESTION 1 — TECHNIQUE IDENTIFICATION:
Which events are adversarial? Which MITRE ATT&CK techniques do they represent? Which events are benign? Explain your triage logic.

QUESTION 2 — NEXT STAGE PREDICTION:
Based only on the adversarial events, what is the most likely next adversary action? Name the technique and expected signals.

QUESTION 3 — DETECTION PROPOSAL:
Write a Sigma rule targeting the most dangerous adversarial technique. Include: title, status, logsource, detection, and falsepositives.
"""
