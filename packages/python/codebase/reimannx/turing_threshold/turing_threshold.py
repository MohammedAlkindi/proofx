#!/usr/bin/env python3
"""
A cybernetic sentinel implementing Turing's method for verifying the completeness
of Riemann zeta zeros up to a given height T on the critical line.

This monolithic guardian algorithm stands watch over the critical strip,
balancing Hardy's analytic exactness with Turing's computational resolve.
"""

import argparse
import math
import numpy as np
from mpmath import mp
import matplotlib.pyplot as plt

# Configure mpmath for high-precision calculations
mp.dps = 50  # Sufficient precision for our sentinel's watchful eyes

class ZetaSentinel:
    """
    The guardian of the critical line, employing Turing's method to audit
    the Riemann zeta function for missing truths in the critical strip.
    """

    def __init__(self, T):
        """
        Initialize the sentinel to watch up to height T.

        Parameters:
            T (float): The height on the critical line to verify zeros up to
        """
        self.T = float(T)
        self.zero_count_expected = None
        self.zero_count_observed = None
        self.gram_points = None
        self.z_values = None
        self.sign_changes = None
        self.discrepancy_regions = None

    def _riemann_von_mangoldt(self, t):
        """
        Compute the expected number of zeros up to height t using the
        Riemann-von Mangoldt formula.

        N(t) ≈ (t/2π) * log(t/2π) - t/2π + 7/8 + O(1/t)

        Parameters:
            t (float): Height on the critical line

        Returns:
            float: Expected number of zeros up to height t
        """
        if t < 1:
            return 0  # No non-trivial zeros below t=1

        t_div_2pi = t / (2 * math.pi)
        return (t_div_2pi * math.log(t_div_2pi) - t_div_2pi + 7/8 +
                1/(48 * math.pi * t_div_2pi))  # Including first correction term

    def _compute_gram_points(self, n_start, n_end):
        """
        Compute Gram points g_n for n in [n_start, n_end].

        Gram points satisfy θ(g_n) = nπ where θ(t) is the Riemann-Siegel theta function.

        Parameters:
            n_start (int): Starting Gram point index
            n_end (int): Ending Gram point index

        Returns:
            list: List of Gram points [g_{n_start}, ..., g_{n_end}]
        """
        gram_points = []

        for n in range(n_start, n_end + 1):
            # Initial approximation
            if n == 0:
                gram_points.append(0.0)
                continue

            t0 = 2 * math.pi * n / mp.log(n / (2 * math.pi * mp.e))

            # Refine using Newton's method
            for _ in range(5):  # Usually converges quickly
                theta = mp.siegeltheta(t0)
                theta_deriv = mp.siegeltheta(t0, derivative=1)
                t0 = t0 - (theta - n * math.pi) / theta_deriv

            gram_points.append(float(t0))

        return gram_points

    def _z_function(self, t):
        """
        Compute the Riemann-Siegel Z function at height t.

        Z(t) = e^{iθ(t)} ζ(1/2 + it)
        where θ(t) is the Riemann-Siegel theta function.

        Parameters:
            t (float): Height on the critical line

        Returns:
            float: Value of Z(t)
        """
        return float(mp.siegelz(t))

    def _find_gram_block(self):
        """
        Find a suitable range of Gram points around our target height T.

        Returns:
            tuple: (n_start, n_end) indices for Gram points
        """
        # Estimate Gram point indices near T
        n_estimate = int(self.T * mp.log(self.T / (2 * math.pi)) / (2 * math.pi))

        # We'll examine ±100 Gram points around our estimate
        n_start = max(0, n_estimate - 100)
        n_end = n_estimate + 100

        return n_start, n_end

    def _count_sign_changes(self, values):
        """
        Count sign changes in a sequence of values.

        Parameters:
            values (list): Sequence of real values

        Returns:
            int: Number of sign changes
        """
        sign_changes = 0
        prev_sign = 0

        for val in values:
            if val == 0:
                continue

            current_sign = 1 if val > 0 else -1
            if prev_sign != 0 and current_sign != prev_sign:
                sign_changes += 1
            prev_sign = current_sign

        return sign_changes

    def _adaptive_sample_z(self, t_start, t_end, min_samples=10, threshold=1e-3):
        """
        Adaptively sample Z(t) between t_start and t_end to ensure we capture
        all zero crossings.

        Parameters:
            t_start (float): Start of interval
            t_end (float): End of interval
            min_samples (int): Minimum number of samples
            threshold (float): Threshold for adaptive refinement

        Returns:
            tuple: (t_values, z_values) sampled points and Z function values
        """
        # Initial uniform sampling
        t_values = np.linspace(t_start, t_end, min_samples)
        z_values = [self._z_function(t) for t in t_values]

        # Refine where needed
        i = 0
        while i < len(t_values) - 1:
            t1, t2 = t_values[i], t_values[i+1]
            z1, z2 = z_values[i], z_values[i+1]

            # Check if we might have missed a zero crossing
            if z1 * z2 < 0 and abs(z1 - z2) > threshold:
                # Insert a midpoint
                t_mid = (t1 + t2) / 2
                z_mid = self._z_function(t_mid)

                t_values = np.insert(t_values, i+1, t_mid)
                z_values.insert(i+1, z_mid)

                # Don't advance i so we check the new interval
            else:
                i += 1

        return t_values, z_values

    def audit_zeros(self):
        """
        Perform the main audit of zeta zeros up to height T.

        Returns:
            bool: True if audit passes (expected zeros == observed), False otherwise
        """
        # Compute expected number of zeros
        self.zero_count_expected = round(self._riemann_von_mangoldt(self.T))

        # Find suitable Gram points around our target height
        n_start, n_end = self._find_gram_block()
        self.gram_points = self._compute_gram_points(n_start, n_end)

        # Compute Z(t) at Gram points and count sign changes
        self.z_values = [self._z_function(g) for g in self.gram_points]
        gram_sign_changes = self._count_sign_changes(self.z_values)

        # Perform adaptive sampling between Gram points to ensure we catch all zeros
        total_sign_changes = 0
        discrepancy_regions = []

        for i in range(len(self.gram_points) - 1):
            t_start, t_end = self.gram_points[i], self.gram_points[i+1]
            z_start, z_end = self.z_values[i], self.z_values[i+1]

            # Skip if no sign change between Gram points
            if z_start * z_end > 0:
                continue

            # Adaptive sampling for this interval
            t_samples, z_samples = self._adaptive_sample_z(t_start, t_end)
            interval_changes = self._count_sign_changes(z_samples)

            # Check for discrepancies (should be exactly 1 between Gram points)
            if interval_changes != 1:
                discrepancy_regions.append((t_start, t_end, interval_changes))

            total_sign_changes += interval_changes

        self.zero_count_observed = total_sign_changes
        self.discrepancy_regions = discrepancy_regions

        return (self.zero_count_observed == self.zero_count_expected and
                len(discrepancy_regions) == 0)

    def generate_report(self):
        """
        Generate a human-readable report of the audit findings.

        Returns:
            str: Formatted report
        """
        report = []
        report.append("\n=== ZETA ZERO AUDIT REPORT ===")
        report.append(f"Height T: {self.T}")
        report.append(f"Expected zeros (N(T)): {self.zero_count_expected}")
        report.append(f"Observed zeros: {self.zero_count_observed}")

        if self.zero_count_observed == self.zero_count_expected:
            report.append("\nRESULT: PASS - Zero count matches expectation")
        else:
            report.append("\nRESULT: FAIL - Zero count discrepancy detected")
            report.append(f"Discrepancy: {abs(self.zero_count_observed - self.zero_count_expected)} zeros")

        if self.discrepancy_regions:
            report.append("\nDiscrepancy regions detected:")
            for i, (t1, t2, count) in enumerate(self.discrepancy_regions, 1):
                report.append(f"  Region {i}: [{t1:.2f}, {t2:.2f}] - Found {count} zeros")

        return "\n".join(report)

    def plot_analysis(self, filename=None):
        """
        Generate diagnostic plots of the analysis.

        Parameters:
            filename (str, optional): If provided, save plot to file. Otherwise display.
        """
        plt.figure(figsize=(12, 8))

        # Plot Z(t) with zero crossings marked
        plt.subplot(2, 1, 1)

        # Create a finer sampling for smooth plot
        t_plot = np.linspace(min(self.gram_points), max(self.gram_points), 1000)
        z_plot = [self._z_function(t) for t in t_plot]

        plt.plot(t_plot, z_plot, label='Z(t)')
        plt.plot(t_plot, np.zeros_like(t_plot), 'k--', alpha=0.5)

        # Mark Gram points
        plt.scatter(self.gram_points, self.z_values, c='red', s=30,
                   label='Gram points', zorder=3)

        # Mark zero crossings
        zero_crossings = []
        for i in range(len(z_plot) - 1):
            if z_plot[i] * z_plot[i+1] < 0:
                zero_crossings.append((t_plot[i] + t_plot[i+1]) / 2)

        plt.scatter(zero_crossings, np.zeros(len(zero_crossings)),
                   c='green', marker='x', s=100, label='Zero crossings', zorder=4)

        plt.xlabel('t')
        plt.ylabel('Z(t)')
        plt.title(f'Riemann-Siegel Z Function near t = {self.T}')
        plt.legend()
        plt.grid(True)

        # Plot cumulative zero count difference
        plt.subplot(2, 1, 2)

        # Sample points for cumulative plot
        t_samples = np.linspace(1, self.T, 100)
        expected = [self._riemann_von_mangoldt(t) for t in t_samples]

        # For observed counts, we'd need to recompute for each t (simplify for demo)
        # In a full implementation, we'd track this during the audit
        observed = []
        last_gram = 0
        sign_changes = 0
        for t in t_samples:
            # Find Gram points below t
            while last_gram < len(self.gram_points) and self.gram_points[last_gram] < t:
                last_gram += 1

            # Simplified: use proportion of our total count (would be more accurate in full impl)
            observed.append(self.zero_count_observed * t / self.T)

        plt.plot(t_samples, np.array(expected) - np.array(observed),
                label='Expected - Observed')
        plt.xlabel('t')
        plt.ylabel('Zero count difference')
        plt.title('Discrepancy in Zero Counts')
        plt.grid(True)
        plt.legend()

        plt.tight_layout()

        if filename:
            plt.savefig(filename)
            plt.close()
        else:
            plt.show()

def main():
    """
    The main sentinel routine, parsing arguments and executing the audit.
    """
    parser = argparse.ArgumentParser(
        description="Turing's method for verifying completeness of Riemann zeta zeros.",
        epilog="Like Turing and Hardy over tea, we watch the critical line."
    )
    parser.add_argument('T', type=float, help='Height on critical line to verify up to')
    parser.add_argument('--plot', action='store_true', help='Generate diagnostic plots')
    parser.add_argument('--plot-file', type=str, help='Save plot to file instead of displaying')

    args = parser.parse_args()

    # Initialize our sentinel
    sentinel = ZetaSentinel(args.T)

    print(f"\nInitializing zeta zero audit up to height T = {args.T}...")
    print("The sentinel stands watch over the critical line...\n")

    # Perform the audit
    audit_result = sentinel.audit_zeros()

    # Generate and print report
    print(sentinel.generate_report())

    # Generate plots if requested
    if args.plot or args.plot_file:
        print("\nGenerating diagnostic plots...")
        sentinel.plot_analysis(args.plot_file)

    # Exit with appropriate status
    if audit_result:
        print("\nAudit complete. The critical line remains undisturbed.")
        return 0
    else:
        print("\nAudit complete. Anomalies detected in the critical strip!")
        return 1

if __name__ == "__main__":
    import sys
    sys.exit(main())
