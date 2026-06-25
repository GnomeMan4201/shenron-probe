#!/usr/bin/env python3
"""
probe_cli.py — SHENRON-PROBE command line interface.

Usage:
  python probe_cli.py run --input <path.jsonl> --model <ollama_model> [--levels L1,L2,L3] [--sessions 5]
  python probe_cli.py report [--results-dir results/]
"""
import argparse
import sys
from probe.runner import run_probe
from probe.report import load_results, build_report


def cmd_run(args):
    levels = [l.strip().upper() for l in args.levels.split(",")]
    run_probe(
        jsonl_path=args.input,
        model=args.model,
        levels=levels,
        max_sessions=args.sessions,
        output_dir=args.output_dir,
    )


def cmd_report(args):
    results = load_results(args.results_dir)
    print(build_report(results))


def main():
    parser = argparse.ArgumentParser(prog="shenron-probe")
    sub = parser.add_subparsers(dest="command")

    run_p = sub.add_parser("run", help="Run probe against a SHENRON JSONL artifact")
    run_p.add_argument("--input", required=True, help="Path to SHENRON .jsonl output")
    run_p.add_argument("--model", required=True, help="Ollama model name (e.g. llama3.1:8b)")
    run_p.add_argument("--levels", default="L1,L2,L3", help="Difficulty levels (default: L1,L2,L3)")
    run_p.add_argument("--sessions", type=int, default=5, help="Max sessions to evaluate (default: 5)")
    run_p.add_argument("--output-dir", default="results", help="Directory for result JSONL files")

    rep_p = sub.add_parser("report", help="Generate report from result files")
    rep_p.add_argument("--results-dir", default="results", help="Directory containing result JSONL files")

    args = parser.parse_args()
    if args.command == "run":
        cmd_run(args)
    elif args.command == "report":
        cmd_report(args)
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
