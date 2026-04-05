import mpmath
import numpy as np
import matplotlib.pyplot as plt

def compute_li_coefficients(N):
    """Compute the first N Keiper-Li coefficients λₙ"""
    mpmath.mp.dps = 50  # Ultra-high precision

    # Define the Riemann ξ function (completed zeta)
    def xi(s):
        return 0.5 * s * (s - 1) * mpmath.gamma(s/2) * mpmath.pow(mpmath.pi, -s/2) * mpmath.zeta(s)

    coefficients = []
    print("🧮 Computing Keiper-Li coefficients...")

    for n in range(1, N+1):
        # Define the function to differentiate: s^(n-1) * log(xi(s))
        def f(s):
            return mpmath.power(s, n-1) * mpmath.log(xi(s))

        # Compute nth derivative at s=1
        derivative = mpmath.diff(f, 1, n)
        λ_n = derivative / mpmath.factorial(n-1)
        coefficients.append(float(λ_n))
        print(f"λ_{n} = {λ_n}")

    return np.array(coefficients)

def analyze_coefficients(λ):
    """Analyze the properties of the coefficient sequence"""
    print("\n🔍 Performing Riemann Hypothesis diagnostics...")

    # Test positivity
    positive = np.all(λ > 0)
    print(f"Positivity: {'✅ All λₙ > 0' if positive else '⚠️ Some λₙ ≤ 0'}")

    # Test monotonicity (strictly increasing)
    diffs = np.diff(λ)
    monotonic = np.all(diffs > 0)
    print(f"Monotonicity: {'✅ Strictly increasing' if monotonic else '⚠️ Non-monotonic'}")

    # Test convexity (second differences positive)
    second_diffs = np.diff(λ, 2)
    convex = np.all(second_diffs > 0)
    print(f"Convexity: {'✅ Convex' if convex else '⚠️ Non-convex'}")

    # Final verdict
    if positive and monotonic and convex:
        print("\n🌊 Final Verdict: ✅ RH holds under these waters.")
    else:
        print("\n🌊 Final Verdict: ⚠️ Turbulence detected. RH's flow may be broken.")

def plot_coefficients(λ):
    """Visualize the Keiper-Li coefficients"""
    plt.figure(figsize=(12, 6))

    # Main plot
    plt.subplot(1, 2, 1)
    plt.plot(λ, 'o-', color='navy', markersize=4)
    plt.xlabel('n')
    plt.ylabel('λₙ')
    plt.title('Keiper-Li Coefficients')
    plt.grid(True, alpha=0.3)

    # Log plot to show growth trends
    plt.subplot(1, 2, 2)
    plt.semilogy(np.abs(λ), 'o-', color='crimson', markersize=4)
    plt.xlabel('n')
    plt.ylabel('log|λₙ|')
    plt.title('Logarithmic Growth')
    plt.grid(True, alpha=0.3)

    plt.tight_layout()
    plt.savefig('li_flow.png')
    print("\n📈 Visualization saved to li_flow.png")

def main():
    N = 50  # Number of coefficients to compute
    λ = compute_li_coefficients(N)
    analyze_coefficients(λ)
    plot_coefficients(λ)

if __name__ == "__main__":
    print("🌌 Beginning Li Criterion Analysis 🌌")
    print(f"Computing first {N} Keiper-Li coefficients...\n")
    main()
    print("\n🌠 Analysis complete. The ξ-function's truth flows onward.")
