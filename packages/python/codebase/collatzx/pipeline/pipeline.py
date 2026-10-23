#!/usr/bin/env python3
import argparse, os, math, time, struct, multiprocessing as mp
from pathlib import Path
import numpy as np
from numba import njit
import zstandard as zstd
import matplotlib.pyplot as plt
from datetime import datetime, timedelta
import json
import signal
import sys
from typing import Dict, List, Tuple, Optional, Union

# -----------------------------
# Collatz Kernels
# -----------------------------
@njit(cache=True, fastmath=True)
def collatz_step(n):
    """Single step of the Collatz function."""
    return (n >> 1) if (n & 1) == 0 else 3*n + 1

@njit(cache=True, fastmath=True)
def collatz_length_u16(n):
    """Calculate Collatz sequence length for a number, capped at 65535."""
    cnt = 1; x = n
    while x != 1:
        x = collatz_step(x); cnt += 1
        if cnt >= 65535: return 65535
    return cnt

@njit(cache=True, fastmath=True)
def collatz_sequence(n, max_steps=1000):
    """Generate Collatz sequence for a number (for analysis)."""
    seq = [n]
    x = n
    for _ in range(max_steps):
        if x == 1:
            break
        x = collatz_step(x)
        seq.append(x)
    return seq

# -----------------------------
# Utilities
# -----------------------------
def human_bytes(x):
    """Convert bytes to human-readable format."""
    for u in ["B","KB","MB","GB","TB","PB"]:
        if x < 1024: return f"{x:.1f} {u}"
        x /= 1024
    return f"{x:.1f} EB"

def human_time(seconds):
    """Convert seconds to human-readable format."""
    if seconds < 60:
        return f"{seconds:.1f}s"
    elif seconds < 3600:
        return f"{seconds/60:.1f}m"
    elif seconds < 86400:
        return f"{seconds/3600:.1f}h"
    else:
        return f"{seconds/86400:.1f}d"

def parse_drives(drives_csv: str):
    """Parse comma-separated drive paths."""
    return [Path(d.strip().strip('"').strip()) for d in drives_csv.split(",") if d.strip()]

def setup_signal_handlers():
    """Setup graceful shutdown handlers."""
    def signal_handler(sig, frame):
        print(f"\nReceived signal {sig}, shutting down gracefully...")
        sys.exit(1)

    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)

# -----------------------------
# Writer Logic
# -----------------------------
class RollingZstdWriter:
    def __init__(self, outdir: Path, roll_bytes: int, level: int):
        self.outdir, self.roll_bytes, self.level = outdir, roll_bytes, level
        self.idx = 0; self.cur_fp = None; self.cur = None; self.cur_written = 0; self.total = 0
        self.start_time = time.time()
        outdir.mkdir(parents=True, exist_ok=True)
        self._open_new()

    def _open_new(self):
        if self.cur:
            self.cur.flush(zstd.FLUSH_FRAME)
            self.cur.close()
            self.cur_fp.close()

        self.idx += 1
        fn = self.outdir / f"part_{self.idx:06d}.zst"
        self.cur_fp = open(fn, "wb", buffering=0)
        self.cur = zstd.ZstdCompressor(level=self.level).stream_writer(self.cur_fp)
        self.cur_written = 0

    def write(self, b: bytes):
        try:
            self.cur.write(b)
            self.cur_written += len(b)
            self.total += len(b)
            if self.cur_written >= self.roll_bytes:
                self._open_new()
        except IOError as e:
            raise Exception(f"Write error after {self.total} bytes: {e}")

    def close(self):
        if self.cur:
            try:
                self.cur.flush(zstd.FLUSH_FRAME)
                self.cur.close()
                self.cur_fp.close()
            except:
                pass
            self.cur = None
            self.cur_fp = None

def worker(proc_id, start_n, count, outdir, roll_mib, zstd_level, chunk, report_queue, max_retries=3):
    """Worker process for computing and writing Collatz lengths."""
    out = Path(outdir)
    attempts = 0

    while attempts < max_retries:
        try:
            w = RollingZstdWriter(out, roll_mib * 1024 * 1024, zstd_level)

            if proc_id == 0:
                # Create metadata file
                metadata = {
                    "format_version": "1.0",
                    "generated": datetime.utcnow().isoformat(),
                    "start_n": start_n,
                    "total_records": count,
                    "chunk_size": chunk,
                    "compression": f"zstd level {zstd_level}",
                    "roll_size_mib": roll_mib,
                    "data_type": "uint16",
                    "endianness": "little",
                    "description": "Collatz sequence lengths (capped at 65535)"
                }
                with open(out / "metadata.json", "w") as f:
                    json.dump(metadata, f, indent=2)

            buf = np.empty(chunk, dtype=np.uint16)
            rec_size = 2
            n0 = start_n
            remaining = count
            t0 = time.time()
            last_report = t0
            bytes_at_last = 0
            processed = 0

            while remaining > 0:
                this_chunk = min(remaining, chunk)

                # Compute Collatz lengths
                for i in range(this_chunk):
                    buf[i] = collatz_length_u16(n0 + i)

                # Write to compressed stream
                w.write(memoryview(buf)[:this_chunk * rec_size].tobytes())

                n0 += this_chunk
                remaining -= this_chunk
                processed += this_chunk

                # Progress reporting
                now = time.time()
                if now - last_report >= 2.0:  # Report every 2 seconds
                    elapsed = now - t0
                    speed = (w.total - bytes_at_last) / max(1e-9, now - last_report)
                    overall_speed = w.total / max(1e-9, elapsed)

                    if speed > 0:
                        eta = (count * rec_size - w.total) / overall_speed
                    else:
                        eta = float('inf')

                    percent = (processed / count) * 100

                    report_queue.put({
                        "proc": proc_id,
                        "written": w.total,
                        "speed": speed,
                        "overall_speed": overall_speed,
                        "processed": processed,
                        "total": count,
                        "percent": percent,
                        "eta": eta,
                        "elapsed": elapsed
                    })

                    last_report = now
                    bytes_at_last = w.total

            w.close()
            report_queue.put({"proc": proc_id, "done": True, "processed": processed})
            break  # Success, break retry loop

        except Exception as e:
            attempts += 1
            if attempts >= max_retries:
                report_queue.put({"proc": proc_id, "error": f"Failed after {max_retries} attempts: {e}"})
                break
            time.sleep(5)  # Wait before retry

def split_even(total, k):
    """Split total records evenly across k workers."""
    base, rem = total // k, total % k
    spans, start = [], 0
    for i in range(k):
        c = base + (1 if i < rem else 0)
        spans.append((start, c))
        start += c
    return spans

def run_dump(args):
    """Main dump function with enhanced monitoring."""
    setup_signal_handlers()
    drives = parse_drives(args.drives)

    if not drives:
        raise SystemExit("No drives provided.")

    # Verify drives are accessible
    for i, drive in enumerate(drives):
        if not drive.exists():
            raise SystemExit(f"Drive path {drive} does not exist.")
        if not os.access(drive, os.W_OK):
            raise SystemExit(f"Drive path {drive} is not writable.")

    spans = split_even(args.total_records, len(drives))
    mgr = mp.get_context("spawn")
    q = mgr.Queue()
    procs, alive, metrics = [], {}, {}

    print(f"Starting {len(drives)} workers for {args.total_records:,} records")
    print(f"Start number: {args.start:,}, Chunk size: {args.chunk:,}")
    print("=" * 60)

    for i, (offset, count) in enumerate(spans):
        start_i = args.start + offset
        p = mgr.Process(
            target=worker,
            args=(i, start_i, count, drives[i], args.roll_mib,
                  args.zstd_level, args.chunk, q, args.max_retries)
        )
        p.start()
        procs.append(p)
        alive[i] = True
        metrics[i] = {
            "written": 0, "speed": 0.0, "overall_speed": 0.0,
            "processed": 0, "total": count, "percent": 0.0,
            "eta": float('inf'), "elapsed": 0
        }

    start_time = time.time()
    errors = []

    try:
        while any(alive.values()):
            try:
                m = q.get(timeout=5.0)
                if "error" in m:
                    errors.append(f"Worker {m['proc']}: {m['error']}")
                    alive[m["proc"]] = False
                elif "done" in m:
                    alive[m["proc"]] = False
                    print(f"Worker {m['proc']} completed: {m['processed']:,} records")
                else:
                    metrics[m["proc"]] = m

                # Aggregate stats
                total_written = sum(v["written"] for v in metrics.values())
                total_speed = sum(v["speed"] for v in metrics.values())
                total_processed = sum(v["processed"] for v in metrics.values())
                total_records = sum(v["total"] for v in metrics.values())

                # Calculate overall progress
                elapsed = time.time() - start_time
                overall_percent = (total_processed / total_records) * 100

                if total_speed > 0:
                    overall_eta = (total_records * 2 - total_written) / total_speed
                else:
                    overall_eta = float('inf')

                # Display status
                active_workers = sum(alive.values())
                print(f"\r[Status] {overall_percent:6.2f}% | "
                      f"Processed: {total_processed:,}/{total_records:,} | "
                      f"Speed: {human_bytes(total_speed)}/s | "
                      f"ETA: {human_time(overall_eta)} | "
                      f"Workers: {active_workers}/{len(drives)} | "
                      f"Elapsed: {human_time(elapsed)}",
                      end="", flush=True)

            except mp.queues.Empty:
                # Timeout, check if processes are still alive
                for i, p in enumerate(procs):
                    if not p.is_alive() and alive.get(i, False):
                        alive[i] = False
                        print(f"\nWorker {i} died unexpectedly")

        print("\n" + "=" * 60)

        if errors:
            print("Errors occurred:")
            for error in errors:
                print(f"  {error}")
        else:
            total_time = time.time() - start_time
            total_data = total_written
            avg_speed = total_data / total_time if total_time > 0 else 0

            print(f"Completed in {human_time(total_time)}")
            print(f"Total data: {human_bytes(total_data)}")
            print(f"Average speed: {human_bytes(avg_speed)}/s")
            print(f"Records processed: {total_processed:,}")

    except KeyboardInterrupt:
        print("\nInterrupted by user, terminating workers...")
    finally:
        for p in procs:
            if p.is_alive():
                p.terminate()
        for p in procs:
            p.join(timeout=5.0)

# -----------------------------
# Reader/Visualizer Logic
# -----------------------------
def stream_lengths(path: Path, chunk_bytes=8_000_000):
    """Stream Collatz lengths from compressed file."""
    dctx = zstd.ZstdDecompressor()
    try:
        with open(path, "rb") as fh, dctx.stream_reader(fh) as r:
            while True:
                chunk = r.read(chunk_bytes)
                if not chunk:
                    break
                n = len(chunk) // 2
                if n:
                    yield np.frombuffer(chunk[:n * 2], dtype="<u2")
    except Exception as e:
        raise Exception(f"Error reading {path}: {e}")

def load_metadata(path: Path):
    """Load metadata from directory."""
    meta_path = path / "metadata.json" if path.is_dir() else path.parent / "metadata.json"
    if meta_path.exists():
        with open(meta_path, 'r') as f:
            return json.load(f)
    return None

def hist_stream(path: Path, bins):
    """Calculate histogram from stream of lengths."""
    hist = np.zeros(len(bins) - 1, dtype=np.int64)
    total, minv, maxv, ssum, squares = 0, None, None, 0, 0

    for arr in stream_lengths(path):
        h, _ = np.histogram(arr, bins=bins)
        hist += h
        total += arr.size
        a_min, a_max = int(arr.min()), int(arr.max())
        minv = a_min if minv is None else min(minv, a_min)
        maxv = a_max if maxv is None else max(maxv, a_max)
        ssum += int(arr.sum())
        squares += int(np.sum(arr.astype(np.int64) ** 2))

    mean = ssum / total if total else 0
    variance = (squares / total) - (mean ** 2) if total else 0
    std_dev = math.sqrt(variance) if variance >= 0 else 0

    return hist, total, minv, maxv, mean, std_dev

def scatter_downsample(path: Path, step=1000, limit_points=5_000_000):
    """Downsample data for scatter plot."""
    kept, seen = [], 0
    for arr in stream_lengths(path):
        if arr.size > step:
            kept.append(arr[::step])
        else:
            kept.append(arr)
        seen += arr.size
        if sum(x.size for x in kept) >= limit_points:
            break

    if kept:
        y = np.concatenate(kept)
        x = np.arange(1, y.size + 1) * step
        return x, y, seen
    return np.array([]), np.array([]), 0

def analyze_sequences(path: Path, sample_size=1000):
    """Analyze Collatz sequences for interesting patterns."""
    print("Analyzing sequences...")
    metadata = load_metadata(Path(path).parent)
    start_n = metadata['start_n'] if metadata else 1

    max_length = 0
    max_length_n = 0
    interesting_sequences = []

    for i, arr in enumerate(stream_lengths(path)):
        if i >= sample_size // 1000:  # Limit analysis
            break

        for j, length in enumerate(arr):
            n = start_n + i * 1000 + j
            if length > max_length:
                max_length = length
                max_length_n = n

            # Look for interesting patterns
            if length > 500:  # Long sequences
                interesting_sequences.append((n, length))

    return {
        'max_length': (max_length_n, max_length),
        'interesting_sequences': interesting_sequences[:10]  # Top 10
    }

def run_plot(args):
    """Enhanced plotting function with multiple visualization options."""
    in_path = Path(args.file)

    if not in_path.exists():
        raise SystemExit(f"File {in_path} does not exist.")

    metadata = load_metadata(in_path)
    if metadata:
        print(f"Dataset info: {metadata.get('description', 'Unknown')}")
        print(f"Records: {metadata.get('total_records', 'Unknown'):,}")
        print(f"Start number: {metadata.get('start_n', 1):,}")

    if args.mode == "hist":
        bins = np.arange(0, args.bins_max + 1, 1, dtype=int)
        hist, total, vmin, vmax, mean, std_dev = hist_stream(in_path, bins)

        print(f"Records: {total:,}")
        print(f"Min length: {vmin}, Max length: {vmax}")
        print(f"Mean: {mean:.2f}, Std Dev: {std_dev:.2f}")

        plt.figure(figsize=(14, 8))
        centers = (bins[:-1] + bins[1:]) / 2

        if args.log_scale:
            plt.yscale('log')
            hist[hist == 0] = 1  # Avoid log(0)

        plt.bar(centers, hist, width=1.0, alpha=0.7)
        plt.xlabel('Sequence Length')
        plt.ylabel('Frequency')
        plt.title(f'Collatz Sequence Length Distribution\n{total:,} records')
        plt.grid(True, alpha=0.3)

        if args.stats:
            # Add statistical annotations
            textstr = '\n'.join([
                f'Total: {total:,}',
                f'Min: {vmin}',
                f'Max: {vmax}',
                f'Mean: {mean:.2f}',
                f'Std Dev: {std_dev:.2f}'
            ])
            props = dict(boxstyle='round', facecolor='wheat', alpha=0.5)
            plt.text(0.02, 0.98, textstr, transform=plt.gca().transAxes,
                    fontsize=10, verticalalignment='top', bbox=props)

        out = Path(args.out) if args.out else in_path.with_name(f"plot_{in_path.stem}_hist.png")
        plt.tight_layout()
        plt.savefig(out, dpi=200)
        plt.close()
        print(f"Saved → {out}")

    elif args.mode == "scatter":
        x, y, seen = scatter_downsample(in_path, args.scatter_step, args.scatter_limit)
        print(f"Streamed {seen:,} records; plotting {y.size:,} points.")

        plt.figure(figsize=(14, 8))

        if args.log_scale:
            plt.xscale('log')
            plt.yscale('log')

        plt.scatter(x, y, s=0.5, alpha=0.5, c=y, cmap='viridis')
        plt.colorbar(label='Sequence Length')
        plt.xlabel('Number (n)')
        plt.ylabel('Sequence Length')
        plt.title(f'Collatz Sequence Lengths\n{seen:,} records sampled')
        plt.grid(True, alpha=0.3)

        out = Path(args.out) if args.out else in_path.with_name(f"plot_{in_path.stem}_scatter.png")
        plt.tight_layout()
        plt.savefig(out, dpi=200)
        plt.close()
        print(f"Saved → {out}")

    elif args.mode == "analyze":
        results = analyze_sequences(in_path, args.sample_size)
        print(f"\nAnalysis Results:")
        print(f"Longest sequence: n={results['max_length'][0]:,} with length={results['max_length'][1]}")
        print(f"\nTop {len(results['interesting_sequences'])} interesting sequences:")
        for n, length in results['interesting_sequences']:
            print(f"  n={n:,}: length={length}")

def run_stats(args):
    """Display statistics about the dataset."""
    in_path = Path(args.file)

    if not in_path.exists():
        raise SystemExit(f"File {in_path} does not exist.")

    metadata = load_metadata(in_path)
    if metadata:
        print("=== Dataset Metadata ===")
        for key, value in metadata.items():
            if key != 'description':
                print(f"{key:20}: {value}")
        if 'description' in metadata:
            print(f"{'description':20}: {metadata['description']}")
        print()

    # Calculate basic statistics
    bins = np.arange(0, 65536, 1, dtype=int)
    hist, total, vmin, vmax, mean, std_dev = hist_stream(in_path, bins)

    print("=== Statistics ===")
    print(f"{'Total records':20}: {total:,}")
    print(f"{'Min length':20}: {vmin}")
    print(f"{'Max length':20}: {vmax}")
    print(f"{'Mean length':20}: {mean:.2f}")
    print(f"{'Std deviation':20}: {std_dev:.2f}")
    print(f"{'Data size':20}: {human_bytes(total * 2)}")

    # Find most common lengths
    top_n = 10
    most_common_indices = np.argsort(hist)[-top_n:][::-1]
    most_common_lengths = [(i, hist[i]) for i in most_common_indices if hist[i] > 0]

    print(f"\nTop {len(most_common_lengths)} most common lengths:")
    for length, count in most_common_lengths:
        print(f"  Length {length:4d}: {count:,} records ({count/total*100:.2f}%)")

# -----------------------------
# CLI
# -----------------------------
def main():
    ap = argparse.ArgumentParser(description="Collatz Tool: generate, analyze, or visualize Collatz sequence lengths.")
    sub = ap.add_subparsers(dest="cmd", required=True)

    # dump command
    ap_dump = sub.add_parser("dump", help="Generate & dump Collatz lengths.")
    ap_dump.add_argument("--drives", required=True, help="Comma-separated list of drive paths")
    ap_dump.add_argument("--start", type=int, default=1, help="Starting number")
    ap_dump.add_argument("--total-records", type=int, required=True, help="Total records to generate")
    ap_dump.add_argument("--roll-mib", type=int, default=8192, help="Rollover size in MiB")
    ap_dump.add_argument("--zstd-level", type=int, default=9, help="Zstd compression level (1-19)")
    ap_dump.add_argument("--chunk", type=int, default=1_000_000, help="Chunk size for processing")
    ap_dump.add_argument("--max-retries", type=int, default=3, help="Maximum retries per worker")
    ap_dump.set_defaults(func=run_dump)

    # plot command
    ap_plot = sub.add_parser("plot", help="Visualize existing .zst file")
    ap_plot.add_argument("file", help="Input .zst file or directory")
    ap_plot.add_argument("--mode", choices=["hist", "scatter", "analyze"], default="hist")
    ap_plot.add_argument("--bins-max", type=int, default=2000, help="Maximum bin value for histogram")
    ap_plot.add_argument("--scatter-step", type=int, default=1000, help="Sampling step for scatter plot")
    ap_plot.add_argument("--scatter-limit", type=int, default=5_000_000, help="Maximum points for scatter plot")
    ap_plot.add_argument("--sample-size", type=int, default=1000, help="Sample size for analysis")
    ap_plot.add_argument("--log-scale", action="store_true", help="Use logarithmic scale")
    ap_plot.add_argument("--stats", action="store_true", help="Show statistics on plot")
    ap_plot.add_argument("--out", type=str, default="", help="Output file path")
    ap_plot.set_defaults(func=run_plot)

    # stats command
    ap_stats = sub.add_parser("stats", help="Show statistics about dataset")
    ap_stats.add_argument("file", help="Input .zst file or directory")
    ap_stats.set_defaults(func=run_stats)

    args = ap.parse_args()
    args.func(args)

if __name__ == "__main__":
    main()
