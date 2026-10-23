import mpmath
import numpy as np
import matplotlib.pyplot as plt

def main():
    # Configure ultra-high precision
    mpmath.mp.dps = 30
    print(" Riemann Mirror engaged. Precision:", mpmath.mp.dps, "digits\n")

    # Define symmetric test points (s, 1-s pairs)
    t_values = np.linspace(0.1, 50, 100)  # Imaginary parts
    σ_vals = [0.3, 0.4, 0.5, 0.6, 0.7]   # Real parts (0.5 is critical line)

    # Initialize results storage
    results = {
        'on_critical': {'t': [], 'delta': [], 'Λp_s': [], 'Λp_1ms': []},
        'off_critical': {'t': [], 'sigma': [], 'delta': [], 'Λp_s': [], 'Λp_1ms': []}
    }

    # Define completed zeta Λ(s) = π^(-s/2)Γ(s/2)ζ(s)
    def Λ(s):
        return mpmath.pi**(-s/2) * mpmath.gamma(s/2) * mpmath.zeta(s)

    # Test points on and off critical line
    print(" Testing functional symmetry...")
    for σ in σ_vals:
        for t in t_values:
            s = σ + 1j*t
            s_ref = 1 - s  # Functional reflection

            # Compute Λ'(s) and Λ'(1-s) using numerical differentiation
            Λp_s = mpmath.diff(Λ, s, 1)
            Λp_1ms = mpmath.diff(Λ, s_ref, 1)

            # Calculate symmetry deviation
            delta = abs(Λp_s - Λp_1ms)

            # Store results
            if σ == 0.5:
                results['on_critical']['t'].append(t)
                results['on_critical']['delta'].append(float(delta))
                results['on_critical']['Λp_s'].append(Λp_s)
                results['on_critical']['Λp_1ms'].append(Λp_1ms)
            else:
                results['off_critical']['t'].append(t)
                results['off_critical']['sigma'].append(σ)
                results['off_critical']['delta'].append(float(delta))
                results['off_critical']['Λp_s'].append(Λp_s)
                results['off_critical']['Λp_1ms'].append(Λp_1ms)

    # Statistical analysis
    def analyze_deviations(name, data):
        deltas = np.array(data['delta'])
        print(f"\n {name.replace('_', ' ').title()} Analysis:")
        print(f"Max deviation: {np.max(deltas):.3e}")
        print(f"Mean deviation: {np.mean(deltas):.3e}")
        print(f"L2-norm: {np.linalg.norm(deltas):.3e}")
        print(f"Near-zero anomalies: {np.sum(deltas > 1e-5)} cases > 1e-5")

    analyze_deviations("on_critical", results['on_critical'])
    analyze_deviations("off_critical", results['off_critical'])

    # Visualization
    print("\n Rendering symmetry plots...")
    plt.figure(figsize=(15, 8))

    # Critical line plot
    plt.subplot(2, 2, 1)
    plt.plot(results['on_critical']['t'], results['on_critical']['delta'],
             'o-', color='navy', markersize=3)
    plt.title('Critical Line Symmetry Deviation\n|Λ\'(½+it) - Λ\'(½-it)|')
    plt.xlabel('t')
    plt.ylabel('Deviation Δ(s)')
    plt.yscale('log')
    plt.grid(True, alpha=0.3)

    # Off-critical heatmap
    plt.subplot(2, 2, 2)
    for σ in set(results['off_critical']['sigma']):
        mask = np.array(results['off_critical']['sigma']) == σ
        t_values = np.array(results['off_critical']['t'])[mask]
        delta_values = np.array(results['off_critical']['delta'])[mask]
        plt.plot(t_values, delta_values, 'o-', markersize=3, label=f'σ={σ}')
    plt.title('Off-Critical Symmetry Deviation')
    plt.xlabel('t')
    plt.ylabel('Deviation Δ(s)')
    plt.yscale('log')
    plt.legend()
    plt.grid(True, alpha=0.3)

    # Phase portrait example (for σ=0.5)
    plt.subplot(2, 2, 3)
    Λp_crit = results['on_critical']['Λp_s']
    plt.plot([float(x.real) for x in Λp_crit],
             [float(x.imag) for x in Λp_crit],
             '.-', color='crimson', markersize=2)
    plt.title('Phase Portrait: Λ\'(½+it)')
    plt.xlabel('Re Λ\'(s)')
    plt.ylabel('Im Λ\'(s)')
    plt.grid(True, alpha=0.3)

    # Comparative plot
    plt.subplot(2, 2, 4)
    t_crit = results['on_critical']['t']
    delta_crit = results['on_critical']['delta']
    delta_off = results['off_critical']['delta']
    plt.semilogy(t_crit, delta_crit, '.-', color='navy', label='Critical')
    plt.semilogy(results['off_critical']['t'], delta_off, 'x',
                color='darkorange', alpha=0.5, markersize=3, label='Off-Critical')
    plt.title('Comparative Symmetry Deviation')
    plt.xlabel('t')
    plt.ylabel('Deviation Δ(s)')
    plt.legend()
    plt.grid(True, alpha=0.3)

    plt.tight_layout()
    plt.savefig('zeta_mirror.png')

    # Philosophical verdict
    max_crit_dev = np.max(results['on_critical']['delta'])
    verdict_threshold = 1e-10
    print("\n Functional Symmetry Verdict:")
    if max_crit_dev < verdict_threshold:
        print(" Perfect mirror symmetry on critical line.")
        print(f"Max deviation: {max_crit_dev:.3e} (<< {verdict_threshold})")
    else:
        print("️ Critical line symmetry anomalies detected!")
        print(f"Max deviation: {max_crit_dev:.3e} (≥ {verdict_threshold})")

    print("\n The analytic mirror rests. Truth reflected.")

if __name__ == "__main__":
    main()
