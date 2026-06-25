# SHENRON-PROBE

**LLM defensive reasoning benchmark grounded in synthetic adversary telemetry.**

SHENRON-PROBE uses SHENRON campaign output as adversarially-grounded evaluation data.
Ground truth is machine-generated, not human-authored. Questions are never the same twice.

## What it measures

| Dimension | Question |
|-----------|----------|
| D1 Technique Identification | Did the LLM correctly name the MITRE techniques from telemetry? |
| D2 Next Stage Prediction | Did the LLM predict the correct next adversary action? |
| D3 Detection Proposal | Did the LLM produce a Sigma rule that targets the right technique? |

## Difficulty levels

| Level | Input | Challenge |
|-------|-------|-----------|
| L1 | Structured summary | Clean labeled campaign data |
| L2 | Raw JSONL logs | Stripped ground truth, requires inference |
| L3 | Raw logs + benign noise | Must triage adversarial from normal activity |

## Quick start

```bash
# Run against SHENRON demo artifact
python probe_cli.py run \
  --input ~/research_hub/shenron/artifacts/demo/shenron_demo_run.jsonl \
  --model llama3.1:8b \
  --levels L1,L2,L3 \
  --sessions 3

# Generate report
python probe_cli.py report --results-dir results/
```

## Integrates with SHENRON

Point --input at any SHENRON run artifact. Fresh campaigns = fresh benchmark. No dataset staleness.
