"""
RareEvent - Advanced Collatz Long-Tail Behavior Analyzer
=========================================================
"""

import argparse
import json
import math
import os
import sys
from collections import defaultdict, deque
from dataclasses import dataclass
from pathlib import Path
from typing import Callable, Dict, List, Optional, Tuple

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from matplotlib.colors import LogNorm
from sklearn.ensemble import IsolationForest
from sklearn.preprocessing import StandardScaler
from sympy import isprime


@dataclass
class CollatzConfig:
    """Configuration for generalized Collatz rules"""
    a: int = 3  # multiplier for odd numbers
    b: int = 1   # additive term for odd numbers
    d: int = 2   # divisor for even numbers
    use_floor: bool = False  # whether to use floor division
    max_steps: int = 10_000  # maximum steps before considering divergent

    def __post_init__(self):
        if self.a <= 0 or self.b < 0 or self.d <= 1:
            raise ValueError("Invalid Collatz parameters")


@dataclass
class SequenceStats:
    """Statistics for a single Collatz sequence"""
    seed: int
    steps: int  # stopping time
    max_value: int  # peak value
    steps_to_max: int  # time to reach peak
    has_diverged: bool  # if sequence exceeded max_steps
    values: List[int]  # sequence values (optional)
    entropy: float = 0.0  # sequence entropy
    divergence_rate: float = 0.0  # growth rate estimate


class CollatzSimulator:
    """Core engine for simulating generalized Collatz sequences"""

    def __init__(self, config: CollatzConfig):
        self.config = config
        self.cache = {}

    def _next_value(self, x: int) -> int:
        """Compute next value in the sequence"""
        if x % 2 == 0:
            return x // self.config.d
        else:
            if self.config.use_floor:
                return (self.config.a * x + self.config.b) // self.config.d
            return (self.config.a * x + self.config.b) // self.config.d

    def compute_sequence(self, seed: int, track_values: bool = False) -> SequenceStats:
        """Generate sequence and compute statistics"""
        if seed in self.cache:
            return self.cache[seed]

        x = seed
        steps = 0
        max_value = x
        steps_to_max = 0
        values = [x] if track_values else []
        seen = set()
        has_diverged = False

        while x != 1 and steps < self.config.max_steps:
            if x in seen:  # Detected a cycle
                has_diverged = True
                break
            seen.add(x)

            x = self._next_value(x)
            steps += 1

            if x > max_value:
                max_value = x
                steps_to_max = steps

            if track_values:
                values.append(x)

        # Calculate entropy if tracking values
        entropy = 0.0
        if track_values and len(values) > 1:
            transitions = defaultdict(int)
            for i in range(len(values)-1):
                transition = (values[i] % 10, values[i+1] % 10)  # Look at last digit transitions
                transitions[transition] += 1

            total = sum(transitions.values())
            entropy = -sum((v/total) * math.log2(v/total) for v in transitions.values())

        # Estimate divergence rate
        divergence_rate = 0.0
        if steps > 1 and track_values:
            log_values = np.log(np.array(values[:steps+1]) + 1e-10)
            x = np.arange(len(log_values))
            coef = np.polyfit(x, log_values, 1)[0]
            divergence_rate = coef

        stats = SequenceStats(
            seed=seed,
            steps=steps,
            max_value=max_value,
            steps_to_max=steps_to_max,
            has_diverged=has_diverged,
            values=values if track_values else [],
            entropy=entropy,
            divergence_rate=divergence_rate
        )

        self.cache[seed] = stats
        return stats


class RareSequenceTracker:
    """Tracks and ranks pathological sequences based on various metrics"""

    def __init__(self, top_n: int = 100):
        self.top_n = top_n
        self.longest_stopping = []
        self.highest_peaks = []
        self.highest_entropy = []
        self.most_divergent = []

    def update(self, stats: SequenceStats):
        """Update trackers with new sequence statistics"""
        # Longest stopping time
        self._update_list(self.longest_stopping, stats, key=lambda x: x.steps)

        # Highest peak values
        self._update_list(self.highest_peaks, stats, key=lambda x: x.max_value)

        # Highest entropy sequences
        if stats.entropy > 0:
            self._update_list(self.highest_entropy, stats, key=lambda x: x.entropy)

        # Most divergent sequences
        self._update_list(self.most_divergent, stats, key=lambda x: abs(x.divergence_rate))

    def _update_list(self, lst: List[SequenceStats], new_item: SequenceStats, key: Callable):
        """Helper method to maintain a sorted top-N list"""
        lst.append(new_item)
        lst.sort(key=key, reverse=True)
        if len(lst) > self.top_n:
            lst.pop()


class AnomalyDetector:
    """Statistical and ML-based anomaly detection for sequences"""

    def __init__(self):
        self.scaler = StandardScaler()
        self.model = IsolationForest(n_estimators=100, contamination='auto')

    def detect_anomalies(self, data: pd.DataFrame) -> pd.DataFrame:
        """Identify anomalous sequences using statistical and ML methods"""
        # Statistical anomaly detection
        data['z_score_steps'] = self._zscore(data['steps'])
        data['z_score_peak'] = self._zscore(np.log(data['max_value'] + 1))
        data['iqr_outlier'] = self._iqr_outlier(data['steps'])

        # ML-based anomaly detection
        features = data[['steps', 'max_value', 'entropy', 'divergence_rate']].copy()
        features['log_peak'] = np.log(features['max_value'] + 1)
        features = features[['steps', 'log_peak', 'entropy', 'divergence_rate']]

        scaled = self.scaler.fit_transform(features)
        anomalies = self.model.fit_predict(scaled)
        data['is_anomaly'] = anomalies == -1

        return data

    def _zscore(self, x: pd.Series) -> pd.Series:
        """Calculate z-scores with outlier-robust statistics"""
        median = x.median()
        mad = (x - median).abs().median() * 1.4826  # MAD to SD conversion
        return (x - median) / (mad + 1e-10)

    def _iqr_outlier(self, x: pd.Series) -> pd.Series:
        """Identify outliers using IQR method"""
        q1 = x.quantile(0.25)
        q3 = x.quantile(0.75)
        iqr = q3 - q1
        return (x < (q1 - 1.5*iqr)) | (x > (q3 + 1.5*iqr))


class Visualizer:
    """Handles all visualization tasks"""

    @staticmethod
    def plot_stopping_times(data: pd.DataFrame, output_path: str):
        """Create scatter plot of seed vs stopping time"""
        plt.figure(figsize=(12, 8))
        plt.scatter(data['seed'], data['steps'], s=1, alpha=0.6)
        plt.yscale('log')
        plt.xscale('log')
        plt.xlabel('Seed (log scale)')
        plt.ylabel('Stopping Time (log scale)')
        plt.title('Collatz Stopping Times')
        plt.grid(True, which="both", ls="--")
        plt.savefig(os.path.join(output_path, 'stopping_times.png'))
        plt.close()

    @staticmethod
    def plot_peak_values(data: pd.DataFrame, output_path: str):
        """Create scatter plot of seed vs peak values"""
        plt.figure(figsize=(12, 8))
        plt.scatter(data['seed'], data['max_value'], s=1, alpha=0.6)
        plt.yscale('log')
        plt.xscale('log')
        plt.xlabel('Seed (log scale)')
        plt.ylabel('Peak Value (log scale)')
        plt.title('Collatz Peak Values')
        plt.grid(True, which="both", ls="--")
        plt.savefig(os.path.join(output_path, 'peak_values.png'))
        plt.close()

    @staticmethod
    def plot_stopping_histogram(data: pd.DataFrame, output_path: str):
        """Create histogram of stopping times with log bins"""
        plt.figure(figsize=(12, 8))
        bins = np.logspace(0, np.log10(data['steps'].max() + 1), 50)
        plt.hist(data['steps'], bins=bins, edgecolor='black')
        plt.xscale('log')
        plt.xlabel('Stopping Time (log scale)')
        plt.ylabel('Frequency')
        plt.title('Distribution of Collatz Stopping Times')
        plt.grid(True, which="both", ls="--")
        plt.savefig(os.path.join(output_path, 'stopping_histogram.png'))
        plt.close()

    @staticmethod
    def plot_heatmap(data: pd.DataFrame, output_path: str):
        """Create heatmap of sequence growth patterns"""
        plt.figure(figsize=(14, 10))

        # Sample some interesting sequences
        sample_seeds = data.nlargest(20, 'steps')['seed'].tolist()
        sample_seeds.extend(data.nlargest(20, 'max_value')['seed'].tolist())
        sample_seeds = list(set(sample_seeds))

        max_len = data['steps'].max() + 50

        # Create grid for heatmap
        grid = np.zeros((len(sample_seeds), max_len))

        for i, seed in enumerate(sample_seeds):
            seq = data[data['seed'] == seed]['values'].iloc[0]
            seq_len = len(seq)
            grid[i, :seq_len] = np.log(np.array(seq) + 1)
            grid[i, seq_len:] = np.nan

        plt.imshow(grid, aspect='auto', cmap='viridis', norm=LogNorm())
        plt.colorbar(label='log(value + 1)')
        plt.yticks(range(len(sample_seeds)), sample_seeds)
        plt.xlabel('Step')
        plt.ylabel('Seed')
        plt.title('Collatz Sequence Growth Patterns')
        plt.savefig(os.path.join(output_path, 'growth_heatmap.png'))
        plt.close()

    @staticmethod
    def plot_anomalies(data: pd.DataFrame, output_path: str):
        """Create scatter plot highlighting anomalies"""
        plt.figure(figsize=(14, 10))

        normal = data[~data['is_anomaly']]
        anomalies = data[data['is_anomaly']]

        plt.scatter(normal['seed'], normal['steps'], s=5, alpha=0.5, label='Normal')
        plt.scatter(anomalies['seed'], anomalies['steps'], s=30, color='red',
                   alpha=0.8, label='Anomaly')

        plt.yscale('log')
        plt.xscale('log')
        plt.xlabel('Seed (log scale)')
        plt.ylabel('Stopping Time (log scale)')
        plt.title('Collatz Anomaly Detection')
        plt.legend()
        plt.grid(True, which="both", ls="--")
        plt.savefig(os.path.join(output_path, 'anomalies.png'))
        plt.close()


class StatsEngine:
    """Computes advanced statistics and metrics"""

    @staticmethod
    def compute_volatility(values: List[int]) -> float:
        """Calculate volatility of a sequence"""
        if len(values) < 2:
            return 0.0
        returns = np.diff(np.log(np.array(values) + 1e-10))
        return np.std(returns)

    @staticmethod
    def compute_graph_metrics(data: pd.DataFrame) -> Dict:
        """Compute graph-theoretic metrics across all sequences"""
        # Analyze stopping time distribution
        steps_stats = {
            'mean': data['steps'].mean(),
            'median': data['steps'].median(),
            'std': data['steps'].std(),
            'skewness': data['steps'].skew(),
            'kurtosis': data['steps'].kurtosis(),
        }

        # Analyze peak value distribution
        peak_stats = {
            'mean': data['max_value'].mean(),
            'median': data['max_value'].median(),
            'std': data['max_value'].std(),
            'skewness': data['max_value'].skew(),
            'kurtosis': data['max_value'].kurtosis(),
        }

        # Analyze correlation between metrics
        corr_matrix = data[['steps', 'max_value', 'entropy', 'divergence_rate']].corr()

        return {
            'stopping_time_stats': steps_stats,
            'peak_value_stats': peak_stats,
            'correlation_matrix': corr_matrix.to_dict(),
        }


def parse_arguments():
    """Parse command line arguments"""
    parser = argparse.ArgumentParser(description="RareEventX - Collatz Long-Tail Explorer")

    # Core simulation parameters
    parser.add_argument('--range', type=str, default="1:1000",
                       help="Seed range to analyze (e.g., '1:1000' or '1,10,100,1000')")
    parser.add_argument('--a', type=int, default=3, help="Multiplier for odd numbers")
    parser.add_argument('--b', type=int, default=1, help="Additive term for odd numbers")
    parser.add_argument('--d', type=int, default=2, help="Divisor for even numbers")
    parser.add_argument('--floor', action='store_true', help="Use floor division")
    parser.add_argument('--max-steps', type=int, default=10000,
                       help="Maximum steps before considering sequence divergent")

    # Analysis parameters
    parser.add_argument('--threshold', type=str, default="steps>100",
                       help="Threshold for interesting sequences (e.g., 'steps>100')")
    parser.add_argument('--top-n', type=int, default=100,
                       help="Number of top sequences to track for each metric")
    parser.add_argument('--track-values', action='store_true',
                       help="Track full sequence values (required for some analyses)")

    # Output control
    parser.add_argument('--output', type=str, default="./results",
                       help="Output directory for results")
    parser.add_argument('--plot', action='store_true', help="Generate visualizations")
    parser.add_argument('--format', type=str, default="csv", choices=["csv", "json", "both"],
                       help="Output format for data")

    return parser.parse_args()


def parse_range(range_str: str) -> List[int]:
    """Parse seed range specification"""
    if ':' in range_str:
        start, end = map(int, range_str.split(':'))
        return list(range(start, end + 1))
    elif ',' in range_str:
        return list(map(int, range_str.split(',')))
    else:
        return [int(range_str)]


def parse_threshold(threshold_str: str) -> Callable[[SequenceStats], bool]:
    """Parse threshold specification into a filter function"""
    field, op_value = threshold_str.split('>')
    value = int(op_value)

    def filter_fn(stats: SequenceStats) -> bool:
        field_value = getattr(stats, field)
        return field_value > value

    return filter_fn


def generate_report(tracker: RareSequenceTracker, stats: Dict, output_path: str):
    """Generate markdown-style report of findings"""
    report_path = os.path.join(output_path, 'report.md')
    with open(report_path, 'w') as f:
        f.write("# RareEventX Collatz Analysis Report\n\n")

        f.write("## Top Pathological Sequences\n\n")

        f.write("### Longest Stopping Times\n")
        f.write("| Seed | Steps | Max Value | Entropy |\n")
        f.write("|------|-------|-----------|---------|\n")
        for seq in tracker.longest_stopping:
            f.write(f"| {seq.seed} | {seq.steps} | {seq.max_value} | {seq.entropy:.3f} |\n")
        f.write("\n")

        f.write("### Highest Peak Values\n")
        f.write("| Seed | Steps | Max Value | Steps to Peak |\n")
        f.write("|------|-------|-----------|---------------|\n")
        for seq in tracker.highest_peaks:
            f.write(f"| {seq.seed} | {seq.steps} | {seq.max_value} | {seq.steps_to_max} |\n")
        f.write("\n")

        f.write("### Highest Entropy Sequences\n")
        f.write("| Seed | Entropy | Steps | Max Value |\n")
        f.write("|------|---------|-------|-----------|\n")
        for seq in tracker.highest_entropy:
            f.write(f"| {seq.seed} | {seq.entropy:.3f} | {seq.steps} | {seq.max_value} |\n")
        f.write("\n")

        f.write("## Statistical Summary\n\n")
        f.write("### Stopping Time Statistics\n")
        for k, v in stats['stopping_time_stats'].items():
            f.write(f"- {k}: {v:.2f}\n")

        f.write("\n### Peak Value Statistics\n")
        for k, v in stats['peak_value_stats'].items():
            f.write(f"- {k}: {v:.2f}\n")

        f.write("\n## Famous Pathological Seeds\n")
        famous_seeds = {27: "Classic difficult seed",
                       703: "High peak value",
                       9663: "Extremely long stopping time"}

        for seed, desc in famous_seeds.items():
            f.write(f"- {seed}: {desc}\n")


def main():
    """Main execution function"""
    args = parse_arguments()

    # Create output directory
    os.makedirs(args.output, exist_ok=True)

    # Initialize components
    config = CollatzConfig(
        a=args.a,
        b=args.b,
        d=args.d,
        use_floor=args.floor,
        max_steps=args.max_steps
    )

    simulator = CollatzSimulator(config)
    tracker = RareSequenceTracker(top_n=args.top_n)
    detector = AnomalyDetector()
    visualizer = Visualizer()

    # Parse seed range
    seeds = parse_range(args.range)

    # Parse threshold filter
    threshold_filter = parse_threshold(args.threshold)

    # Run simulations
    results = []
    for seed in seeds:
        stats = simulator.compute_sequence(seed, track_values=args.track_values)

        if threshold_filter(stats):
            tracker.update(stats)

        results.append({
            'seed': seed,
            'steps': stats.steps,
            'max_value': stats.max_value,
            'steps_to_max': stats.steps_to_max,
            'has_diverged': stats.has_diverged,
            'entropy': stats.entropy,
            'divergence_rate': stats.divergence_rate,
            'values': stats.values if args.track_values else []
        })

    # Convert to DataFrame for analysis
    df = pd.DataFrame(results)

    # Detect anomalies
    if len(df) > 10:  # Need sufficient data for anomaly detection
        df = detector.detect_anomalies(df)

    # Compute advanced statistics
    stats_engine = StatsEngine()
    stats = stats_engine.compute_graph_metrics(df)

    # Save results
    if args.format in ("csv", "both"):
        df.to_csv(os.path.join(args.output, 'results.csv'), index=False)
    if args.format in ("json", "both"):
        with open(os.path.join(args.output, 'results.json'), 'w') as f:
            json.dump({
                'config': vars(config),
                'data': df.to_dict('records'),
                'stats': stats,
                'top_sequences': {
                    'longest_stopping': [vars(s) for s in tracker.longest_stopping],
                    'highest_peaks': [vars(s) for s in tracker.highest_peaks],
                    'highest_entropy': [vars(s) for s in tracker.highest_entropy],
                }
            }, f, indent=2)

    # Generate visualizations
    if args.plot:
        visualizer.plot_stopping_times(df, args.output)
        visualizer.plot_peak_values(df, args.output)
        visualizer.plot_stopping_histogram(df, args.output)

        if args.track_values and len(df) > 0:
            visualizer.plot_heatmap(df, args.output)

        if 'is_anomaly' in df.columns:
            visualizer.plot_anomalies(df, args.output)

    # Generate report
    generate_report(tracker, stats, args.output)

    # Print summary
    print("\nPathological Sequence Report:")
    print(f"- Longest stopping time: {tracker.longest_stopping[0].seed} "
          f"(steps: {tracker.longest_stopping[0].steps})")
    print(f"- Highest peak: {tracker.highest_peaks[0].seed} "
          f"(peak: {tracker.highest_peaks[0].max_value})")
    if tracker.highest_entropy:
        print(f"- Top entropy: {tracker.highest_entropy[0].seed} "
              f"(entropy: {tracker.highest_entropy[0].entropy:.3f})")
    print(f"\nResults saved to: {args.output}")


if __name__ == "__main__":
    main()
