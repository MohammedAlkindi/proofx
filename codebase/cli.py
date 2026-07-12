"""
proofx — Unified CLI for the ProofX research toolkit
══════════════════════════════════════════════════════

Subcommands
───────────
  falsify   Run the FalsificationEngine (Collatz + Goldbach directed search)
  calibrate Fit or apply a score calibrator to a JSONL ledger
  correlate Run cross-engine correlation analysis on two JSONL ledgers
  riemann   Run the Riemann zero-property verifier (ZeroProperties)
  collatz   Run the CollatzX pipeline
  goldbach  Run the GoldbachX partition analysis

All subcommands share:
  --log-level   DEBUG | INFO | WARNING | ERROR  (default INFO)
  --log-file    Append logs to a file in addition to stdout

Usage examples
──────────────
  python -m codebase.cli falsify --budget 500 --seed 42 --target both
  python -m codebase.cli calibrate fit --ledger out.jsonl --method isotonic
  python -m codebase.cli calibrate annotate --ledger out.jsonl --calibrator cal.pkl
  python -m codebase.cli correlate --collatz cz.jsonl --goldbach gb.jsonl
"""

from __future__ import annotations

import argparse
import logging
import sys
from pathlib import Path

# ── Shared logging setup ──────────────────────────────────────────────────────


def _setup_logging(level: str, log_file: str | None) -> None:
    handlers: list[logging.Handler] = [logging.StreamHandler(sys.stdout)]
    if log_file:
        handlers.append(logging.FileHandler(log_file, encoding="utf-8"))
    logging.basicConfig(
        level=getattr(logging, level.upper(), logging.INFO),
        format="%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
        handlers=handlers,
    )


def _add_common_args(p: argparse.ArgumentParser) -> None:
    p.add_argument("--log-level", default="INFO", choices=["DEBUG", "INFO", "WARNING", "ERROR"])
    p.add_argument("--log-file", default=None, metavar="PATH", help="Also write logs to this file")


# ── falsify ───────────────────────────────────────────────────────────────────


def _cmd_falsify(args: argparse.Namespace) -> int:
    _setup_logging(args.log_level, args.log_file)
    import json

    from codebase.FalsificationEngine.FalsificationEngine import (
        _SIEVE_LIMIT,
        FalsificationEngine,
        json_default,
    )

    sieve = args.sieve_limit if getattr(args, "sieve_limit", None) is not None else _SIEVE_LIMIT
    min_score = getattr(args, "min_score", 0.0)
    engine = FalsificationEngine(sieve_limit=sieve)
    result = engine.run(budget=args.budget, seed=args.seed, target=args.target, min_score=min_score)

    stats = result["stats"]
    print(f"\n{'═' * 62}")
    print(f"  ProofX FalsificationEngine  (seed={args.seed})")
    print(f"{'═' * 62}")
    print(f"  Collatz evaluated  : {stats['collatz_evaluated']}")
    print(f"  Goldbach evaluated : {stats['goldbach_evaluated']}")
    print(f"  Elapsed            : {stats['elapsed_s']:.2f}s")
    print(f"  Max Collatz score  : {stats['collatz_max_near_miss']:.4f}")
    print(f"  Max Goldbach score : {stats['goldbach_max_near_miss']:.4f}")

    for label, key in [
        ("Collatz top near-misses", "top_collatz"),
        ("Goldbach top near-misses", "top_goldbach"),
        ("Riemann top near-misses", "top_riemann"),
    ]:
        entries = result[key]
        if not entries:
            continue
        print(f"\n  {label}:")
        for i, e in enumerate(entries[: args.top_k], 1):
            print(
                f"    #{i}  n={e.candidate:>12,}  score={e.near_miss_score:.4f}"
                f"  strategy={e.strategy}"
            )

    if args.save_ledger:
        result["ledger"].save(Path(args.save_ledger))
        print(f"\n  Ledger: {args.save_ledger}")

    if args.output_json:

        def _serialize_top(key: str) -> list:
            return [
                {
                    "candidate": e.candidate,
                    "near_miss_score": e.near_miss_score,
                    "strategy": e.strategy,
                    "features": e.features,
                    "details": e.details,
                }
                for e in result.get(key, [])[: args.top_k]
            ]

        out = {
            "seed": args.seed,
            "budget": args.budget,
            "target": args.target,
            "stats": stats,
            "top_collatz": _serialize_top("top_collatz"),
            "top_goldbach": _serialize_top("top_goldbach"),
            "top_riemann": _serialize_top("top_riemann"),
        }
        p = Path(args.output_json)
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(json.dumps(out, indent=2, default=json_default), encoding="utf-8")
        print(f"  JSON summary: {args.output_json}")

    return 0


def _build_falsify(sub: argparse._SubParsersAction) -> None:
    p = sub.add_parser("falsify", help="Run directed counterexample search")
    _add_common_args(p)
    p.add_argument("--budget", type=int, default=200)
    p.add_argument("--seed", type=int, default=42)
    p.add_argument(
        "--target", choices=["collatz", "goldbach", "riemann", "both", "all"], default="both"
    )
    p.add_argument("--top-k", type=int, default=5)
    p.add_argument("--save-ledger", metavar="PATH")
    p.add_argument("--output-json", metavar="PATH")
    p.add_argument(
        "--sieve-limit",
        type=int,
        default=None,
        metavar="N",
        help="Upper bound for Goldbach prime sieve",
    )
    p.add_argument(
        "--min-score",
        type=float,
        default=0.0,
        metavar="F",
        help="Drop ledger entries below this near-miss score",
    )
    p.set_defaults(func=_cmd_falsify)


# ── calibrate ─────────────────────────────────────────────────────────────────


def _cmd_calibrate_fit(args: argparse.Namespace) -> int:
    _setup_logging(args.log_level, args.log_file)
    import json

    from codebase.FalsificationEngine.calibration import IsotonicCalibrator, PlattCalibrator

    lines = Path(args.ledger).read_text(encoding="utf-8").splitlines()
    entries = [json.loads(line) for line in lines if line.strip()]
    if not entries:
        print("ERROR: ledger is empty", file=sys.stderr)
        return 1
    if "label" not in entries[0]:
        print("ERROR: entries must have a 'label' field (0 or 1)", file=sys.stderr)
        return 1

    scores = [e["near_miss_score"] for e in entries]
    labels = [int(e["label"]) for e in entries]
    cal = IsotonicCalibrator() if args.method == "isotonic" else PlattCalibrator()
    report = cal.fit(scores, labels, seed=args.seed)
    print(report.summary())
    cal.save(Path(args.output))
    return 0


def _cmd_calibrate_annotate(args: argparse.Namespace) -> int:
    _setup_logging(args.log_level, args.log_file)
    from codebase.FalsificationEngine.calibration import _BaseCalibrator, annotate_ledger

    cal = _BaseCalibrator.load(Path(args.calibrator))
    out = Path(args.output) if args.output else None
    annotate_ledger(Path(args.ledger), cal, out)
    return 0


def _build_calibrate(sub: argparse._SubParsersAction) -> None:
    p = sub.add_parser("calibrate", help="Fit or apply a score calibrator")
    _add_common_args(p)
    csub = p.add_subparsers(dest="cal_cmd", required=True)

    fit = csub.add_parser("fit")
    fit.add_argument("--ledger", required=True)
    fit.add_argument("--method", choices=["isotonic", "platt"], default="isotonic")
    fit.add_argument("--output", default="calibrator.pkl")
    fit.add_argument("--seed", type=int, default=0)
    fit.add_argument("--log-level", default="INFO")
    fit.add_argument("--log-file", default=None)
    fit.set_defaults(func=_cmd_calibrate_fit)

    ann = csub.add_parser("annotate")
    ann.add_argument("--ledger", required=True)
    ann.add_argument("--calibrator", required=True)
    ann.add_argument("--output", default=None)
    ann.add_argument("--log-level", default="INFO")
    ann.add_argument("--log-file", default=None)
    ann.set_defaults(func=_cmd_calibrate_annotate)

    p.set_defaults(func=lambda a: p.print_help() or 0)


# ── correlate ─────────────────────────────────────────────────────────────────


def _cmd_correlate(args: argparse.Namespace) -> int:
    _setup_logging(args.log_level, args.log_file)
    from codebase.CrossEngineAnalysis.cross_engine import CrossEngineAnalyzer

    analyzer = CrossEngineAnalyzer()
    report = analyzer.analyze(
        collatz_ledger=Path(args.collatz),
        goldbach_ledger=Path(args.goldbach),
        neighborhood_radius=args.radius,
    )
    analyzer.print_report(report)

    if args.output_json:
        import json

        Path(args.output_json).write_text(
            json.dumps(report, indent=2, default=str), encoding="utf-8"
        )
        print(f"\nCorrelation report saved: {args.output_json}")

    return 0


def _build_correlate(sub: argparse._SubParsersAction) -> None:
    p = sub.add_parser("correlate", help="Cross-engine near-miss correlation analysis")
    _add_common_args(p)
    p.add_argument("--collatz", required=True, metavar="PATH", help="Collatz JSONL ledger")
    p.add_argument("--goldbach", required=True, metavar="PATH", help="Goldbach JSONL ledger")
    p.add_argument(
        "--radius",
        type=int,
        default=100,
        help="Neighborhood radius for co-occurrence search (default 100)",
    )
    p.add_argument("--output-json", metavar="PATH")
    p.set_defaults(func=_cmd_correlate)


# ── riemann ───────────────────────────────────────────────────────────────────


def _cmd_riemann(args: argparse.Namespace) -> int:
    _setup_logging(args.log_level, args.log_file)
    print("Launching ReimannX ZeroProperties verifier...")
    from codebase.ReimannX.ZeroProperties.ZeroProperties import ConfigManager

    cfg = ConfigManager()
    print(f"  Config version : {cfg.config['version']}")
    print(f"  Precision      : {cfg.config['precision']['digits']} digits")
    print("  (Pass --help inside ZeroProperties.py for full options)")
    return 0


def _build_riemann(sub: argparse._SubParsersAction) -> None:
    p = sub.add_parser("riemann", help="Riemann zero-property verifier")
    _add_common_args(p)
    p.set_defaults(func=_cmd_riemann)


# ── collatz ───────────────────────────────────────────────────────────────────


def _cmd_collatz(args: argparse.Namespace) -> int:
    _setup_logging(args.log_level, args.log_file)
    from codebase.CollatzX.Pipeline.pipeline import run_dump, run_plot, run_stats

    if args.collatz_cmd == "dump":
        run_dump(args)
    elif args.collatz_cmd == "plot":
        run_plot(args)
    elif args.collatz_cmd == "stats":
        run_stats(args)
    return 0


def _build_collatz(sub: argparse._SubParsersAction) -> None:
    p = sub.add_parser(
        "collatz", help="CollatzX pipeline: generate, analyze, or visualize sequence lengths"
    )
    _add_common_args(p)
    csub = p.add_subparsers(dest="collatz_cmd", required=True)

    dump = csub.add_parser("dump", help="Generate & dump Collatz sequence lengths")
    dump.add_argument("--drives", required=True, help="Comma-separated list of drive paths")
    dump.add_argument("--start", type=int, default=1, help="Starting number")
    dump.add_argument("--total-records", type=int, required=True, help="Total records to generate")
    dump.add_argument("--roll-mib", type=int, default=8192, help="Rollover size in MiB")
    dump.add_argument("--zstd-level", type=int, default=9, help="Zstd compression level (1-19)")
    dump.add_argument("--chunk", type=int, default=1_000_000, help="Chunk size for processing")
    dump.add_argument("--max-retries", type=int, default=3, help="Maximum retries per worker")
    dump.add_argument("--log-level", default="INFO")
    dump.add_argument("--log-file", default=None)
    dump.set_defaults(func=_cmd_collatz)

    plot = csub.add_parser("plot", help="Visualize an existing .zst dataset")
    plot.add_argument("file", help="Input .zst file or directory")
    plot.add_argument("--mode", choices=["hist", "scatter", "analyze"], default="hist")
    plot.add_argument("--bins-max", type=int, default=2000, help="Maximum bin value for histogram")
    plot.add_argument(
        "--scatter-step", type=int, default=1000, help="Sampling step for scatter plot"
    )
    plot.add_argument(
        "--scatter-limit", type=int, default=5_000_000, help="Maximum points for scatter plot"
    )
    plot.add_argument("--sample-size", type=int, default=1000, help="Sample size for analysis")
    plot.add_argument("--log-scale", action="store_true", help="Use logarithmic scale")
    plot.add_argument("--stats", action="store_true", help="Show statistics on plot")
    plot.add_argument("--out", type=str, default="", help="Output file path")
    plot.add_argument("--log-level", default="INFO")
    plot.add_argument("--log-file", default=None)
    plot.set_defaults(func=_cmd_collatz)

    stats = csub.add_parser("stats", help="Show statistics about a dataset")
    stats.add_argument("file", help="Input .zst file or directory")
    stats.add_argument("--log-level", default="INFO")
    stats.add_argument("--log-file", default=None)
    stats.set_defaults(func=_cmd_collatz)


# ── goldbach ──────────────────────────────────────────────────────────────────


def _cmd_goldbach(args: argparse.Namespace) -> int:
    _setup_logging(args.log_level, args.log_file)
    from codebase.GoldbachX.PartitionEnumerator.PartitionEnumerator import enumerate_partitions
    from codebase.GoldbachX.SieveEngine.SieveEngine import get_primes

    primes = get_primes(args.n)
    pairs = enumerate_partitions(
        args.n,
        primes,
        allow_equal=not args.no_equal,
        exclude_twins=args.exclude_twins,
        unique=True,
    )
    print(f"Goldbach partitions of {args.n}: {len(pairs)} pair(s)")
    for p, q in pairs[: args.top_k]:
        print(f"  {p} + {q} = {args.n}")

    if args.output_json:
        import json

        out = {"n": args.n, "pairs": pairs, "count": len(pairs)}
        p_out = Path(args.output_json)
        p_out.parent.mkdir(parents=True, exist_ok=True)
        p_out.write_text(json.dumps(out, indent=2), encoding="utf-8")
        print(f"  JSON summary: {args.output_json}")

    return 0


def _build_goldbach(sub: argparse._SubParsersAction) -> None:
    p = sub.add_parser("goldbach", help="Enumerate Goldbach prime-pair partitions of n")
    _add_common_args(p)
    p.add_argument("--n", type=int, required=True, help="Target even number >= 4")
    p.add_argument("--no-equal", action="store_true", help="Exclude p == q pairs")
    p.add_argument("--exclude-twins", action="store_true", help="Exclude twin-prime pairs")
    p.add_argument("--top-k", type=int, default=10)
    p.add_argument("--output-json", metavar="PATH")
    p.set_defaults(func=_cmd_goldbach)


# ── main ──────────────────────────────────────────────────────────────────────


def main() -> None:
    parser = argparse.ArgumentParser(
        prog="proofx",
        description="ProofX — conjecture falsification & analysis toolkit",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="Run `proofx <subcommand> --help` for per-command options.",
    )
    sub = parser.add_subparsers(dest="command")

    _build_falsify(sub)
    _build_calibrate(sub)
    _build_correlate(sub)
    _build_riemann(sub)
    _build_collatz(sub)
    _build_goldbach(sub)

    args = parser.parse_args()
    if not hasattr(args, "func"):
        parser.print_help()
        sys.exit(0)

    sys.exit(args.func(args) or 0)


if __name__ == "__main__":
    main()
