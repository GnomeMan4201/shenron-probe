# SHENRON-PROBE

**LLM defensive reasoning benchmark grounded in synthetic adversary telemetry.**

SHENRON-PROBE uses [SHENRON](https://github.com/GnomeMan4201/shenron) campaign output as adversarially-grounded evaluation data. Ground truth is machine-generated, not human-authored. Benchmark questions are never the same twice — fresh SHENRON run, fresh evaluation.

## The problem with existing LLM security benchmarks

Existing benchmarks measure **declarative knowledge**: give the model a labeled question about an attack technique and check if it knows the answer. That's useful, but it has two fundamental limits:

1. **Static datasets get memorized.** Future models will train on published benchmark questions. Scores inflate without capability improving.
2. **Knowing about an attack is not the same as reasoning about one.** An analyst doesn't get labeled telemetry. They get raw logs, noise, and partial signals.

SHENRON-PROBE measures something different: **can a model reason about an attack it is observing mid-execution, from evidence alone, and produce actionable detection logic?**

## What it measures

| Dimension | Question | Ground truth source |
|-----------|----------|-------------------|
| D1 — Technique Identification | Did the model correctly identify MITRE ATT&CK techniques from telemetry? | SHENRON campaign metadata |
| D2 — Next Stage Prediction | Did the model correctly predict the next adversary action? | Actual next event in campaign sequence |
| D3 — Detection Proposal | Did the model produce a valid Sigma rule targeting the right technique? | SHENRON Sigma rules + detection opportunities |

## Difficulty levels

| Level | Input | What makes it hard |
|-------|-------|--------------------|
| L1 | Structured campaign summary with technique labels | Clean, labeled — tests recall |
| L2 | Raw JSONL telemetry, ground truth stripped | No labels — tests inference from log fields |
| L3 | Raw logs + injected benign noise events | Must triage adversarial from normal activity |

## Results — v0.1.0 (local models, 4 models, 3 sessions each)

| Model | Level | Aggregate | D1 Technique | D2 Next Stage | D3 Sigma | Fatal Errors | Avg Latency |
|-------|-------|-----------|-------------|--------------|----------|-------------|-------------|
| mistral:latest (4.4GB) | L1 | 0.527 | **1.000** | 0.583 | 0.000 | 2/2 | 96.7s |
| mistral:latest | L2 | 0.149 | 0.000 | 0.167 | 0.280 | 0/2 | 92.8s |
| mistral:latest | L3 | 0.344 | 0.250 | 0.250 | 0.530 | 0/2 | 99.7s |
| llama3:latest (4.7GB) | L1 | 0.500 | **1.000** | 0.500 | 0.000 | 2/2 | 69.0s |
| llama3:latest | L2 | 0.298 | 0.010 | 0.333 | 0.550 | 0/3 | 89.9s |
| llama3:latest | L3 | 0.175 | 0.000 | 0.167 | 0.360 | 0/2 | 106.7s |
| phi3:mini (2.2GB) | L1 | 0.500 | **1.000** | 0.500 | 0.000 | 2/2 | 49.5s |
| phi3:mini | L2 | 0.000 | 0.000 | 0.000 | 0.000 | 1/1 | 88.2s |
| phi3:mini | L3 | 0.093 | 0.000 | 0.000 | 0.280 | 1/3 | 101.2s |
| qwen2.5:3b (1.9GB) | L1 | 0.390 | 0.618 | 0.278 | 0.273 | 2/3 | **17.7s** |
| qwen2.5:3b | L2 | 0.301 | 0.010 | 0.333 | **0.558** | 0/3 | 24.0s |
| qwen2.5:3b | L3 | 0.245 | 0.000 | 0.333 | 0.403 | 0/3 | 30.7s |

### Key findings

**The D1 label-lookup collapse.** Every model scores near-perfect on D1 at L1 (technique identification from labeled summaries), then collapses to ~0.010 at L2 (raw logs, no labels). This is not a scoring artifact. These models are doing label lookup, not reasoning. Strip the technique IDs and they fail almost completely.

**D3 behaves inversely to D1.** Sigma rule quality is 0.000 at L1 with fatal errors across all models, but improves at L2 and L3. When forced to reason from raw evidence, models produce more grounded detection logic rather than generic placeholder rules.

**qwen2.5:3b punches above its weight.** At 1.9GB it completes in 18-30 seconds vs 70-107 seconds for models twice its size, with competitive D3 scores at L2/L3. It's the only model that didn't go 100% fatal on D3 at L1.

**phi3:mini struggles with complexity.** High timeout rate on multi-event sessions. Not suitable for campaign-level reasoning tasks at this prompt length.

## Quick start

```bash
git clone https://github.com/GnomeMan4201/shenron-probe.git
cd shenron-probe

# Requires Ollama running locally
# Run against SHENRON demo artifact
python3 probe_cli.py run \
  --input /path/to/shenron_run.jsonl \
  --model mistral:latest \
  --levels L1,L2,L3 \
  --sessions 3

# Generate report
python3 probe_cli.py report --results-dir results/
```

## Integrates with SHENRON

Point `--input` at any SHENRON run artifact. Fresh campaign seed = fresh benchmark. No dataset staleness, no memorization risk.

```bash
# Generate fresh campaign with SHENRON then probe it
cd ~/research_hub/shenron
python shenron.py run --scenario beacon_emitter_cloak --seed $(date +%s) > /tmp/fresh_campaign.jsonl
cd ~/research_hub/shenron-probe
python3 probe_cli.py run --input /tmp/fresh_campaign.jsonl --model mistral:latest
```

## Roadmap

- [ ] v0.2.0: Increase timeout handling, streaming Ollama support
- [ ] v0.2.0: Larger session support without truncation
- [ ] v0.3.0: Cloud model baselines (GPT, Claude, Gemini via API)
- [ ] v0.4.0: LLM-as-Judge audit layer for D3 Sigma validation
- [ ] v1.0.0: Public leaderboard with reproducible run submissions

## Related work

- [SHENRON](https://github.com/GnomeMan4201/shenron) — the synthetic telemetry framework that powers this benchmark
- [Red Team AI Benchmark v2.0](https://dev.to/toxy4ny/red-team-ai-benchmark-v20-from-12-questions-to-60-a-technical-deep-dive-omn) by KL3FT3Z — measures LLM offensive knowledge; SHENRON-PROBE measures defensive reasoning, a complementary but distinct problem

## License

MIT. Authorized security research, detection engineering, and AI evaluation use.

## Author

[GnomeMan4201](https://dev.to/gnomeman4201) / badBANANA Research Collective
