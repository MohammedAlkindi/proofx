import mpmath
import numpy as np
import matplotlib.pyplot as plt
from sympy.ntheory import chebyshev

# Configuration
mpmath.mp.dps = 30  # Set high precision
N = 100  # Number of zeros to use
x_min, x_max = 2, 50  # Range of x values
num_points = 200  # Number of points to evaluate

def compute_psi_approx(x_vals, zeros):
    """Compute ψ(x) approximation using explicit formula"""
    psi_approx = []
    for x in x_vals:
        x_mp = mpmath.mpf(x)
        sum_term = mpmath.mpf(0)

        # Sum over zeros
        for n in range(1, N+1):
            zero = zeros[n-1]
            term = mpmath.power(x_mp, zero) / zero
            sum_term += term

        # Explicit formula: ψ(x) ≈ x - sum(x^ρ/ρ) - log(2π) - 1/2*log(1-x^-2)
        result = x_mp - sum_term.real - mpmath.log(2*mpmath.pi) - 0.5*mpmath.log(1 - mpmath.power(x_mp, -2))
        psi_approx.append(float(result))
    return np.array(psi_approx)

def compute_psi_true(x_vals):
    """Compute true ψ(x) using sympy"""
    return np.array([chebyshev.psi(float(x)) for x in x_vals])

def main():
    print("⚡ Harvesting zeros from the critical line...")
    zeros = [mpmath.zetazero(n) for n in range(1, N+1)]

    print("🧮 Computing ψ(x) approximations...")
    x_vals = np.linspace(x_min, x_max, num_points)
    psi_approx = compute_psi_approx(x_vals, zeros)
    psi_true = compute_psi_true(x_vals)

    # Compute deviation
    deviation = psi_true - psi_approx

    print("📊 Plotting results...")
    plt.figure(figsize=(12, 8))

    # Plot ψ(x) comparisons
    plt.subplot(2, 1, 1)
    plt.plot(x_vals, psi_true, label='True ψ(x)', color='blue')
    plt.plot(x_vals, psi_approx, label=f'Approx ψ(x) (N={N})', color='red', linestyle='dashed')
    plt.xlabel('x')
    plt.ylabel('ψ(x)')
    plt.title('Chebyshev Function ψ(x) Comparison')
    plt.legend()
    plt.grid(True)

    # Plot deviation
    plt.subplot(2, 1, 2)
    plt.plot(x_vals, deviation, label='Deviation (True - Approx)', color='green')
    plt.xlabel('x')
    plt.ylabel('Δ(x)')
    plt.title('Deviation Analysis')
    plt.legend()
    plt.grid(True)

    plt.tight_layout()
    plt.savefig('prime_echoes.png')

    # Philosophical verdict
    max_dev = np.max(np.abs(deviation))
    threshold = 2.0  # Empirical threshold for "good" approximation

    print("\n🔮 Philosophical Verdict:")
    if max_dev < threshold:
        print("✅ The zeros echo the primes.")
        print(f"The maximum deviation ({max_dev:.4f}) is within acceptable bounds.")
    else:
        print("⚠️ The zeros whisper misdirection.")
        print(f"The maximum deviation ({max_dev:.4f}) suggests significant divergence.")

    print("\n🌌 Analysis complete. The cosmic dance of primes and zeros continues...")

if __name__ == "__main__":
    main()
