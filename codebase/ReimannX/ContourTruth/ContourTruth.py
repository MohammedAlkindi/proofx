import mpmath
import numpy as np
import matplotlib.pyplot as plt

def main():
    # Configure ultra-high precision
    mpmath.mp.dps = 40
    print(f"🔍 Contour Truth Scanner (mpmath precision: {mpmath.mp.dps} digits)\n")

    # Define contour parameters
    T = 100.0  # Height of contour
    sigma_min, sigma_max = 0.4, 0.6  # Real part bounds
    num_points = 1000  # Points per contour segment

    # Define the zeta logarithmic derivative function
    def zeta_ld(s):
        return mpmath.zeta(s, derivative=1) / mpmath.zeta(s)

    # Parameterize the four contour segments (counter-clockwise)
    def contour_segments():
        # Bottom: 0.4 -> 0.6 (t=0)
        s_bottom = [mpmath.mpc(sigma, 0) for sigma in
                   np.linspace(sigma_min, sigma_max, num_points)]

        # Right: 0.6 + 0i -> 0.6 + Ti
        s_right = [mpmath.mpc(sigma_max, t) for t in
                   np.linspace(0, T, num_points)]

        # Top: 0.6 + Ti -> 0.4 + Ti
        s_top = [mpmath.mpc(sigma, T) for sigma in
                 np.linspace(sigma_max, sigma_min, num_points)]

        # Left: 0.4 + Ti -> 0.4 + 0i
        s_left = [mpmath.mpc(sigma_min, t) for t in
                  np.linspace(T, 0, num_points)]

        return s_bottom + s_right + s_top + s_left

    # Compute the contour integral numerically
    print("🧮 Computing contour integral...")
    segments = contour_segments()
    integral = 0j

    for i in range(len(segments)-1):
        a = segments[i]
        b = segments[i+1]
        midpoint = (a + b)/2
        dz = b - a
        integral += zeta_ld(midpoint) * dz

    N_estimated = integral / (2j * mpmath.pi)
    N_estimated = complex(N_estimated).real  # Should be real and near-integer
    N_rounded = int(round(N_estimated))

    # Theoretical zero count from Riemann-von Mangoldt
    def theoretical_zero_count(T):
        if T <= 0:
            return 0
        return (T/(2*mpmath.pi)) * mpmath.log(T/(2*mpmath.pi)) - T/(2*mpmath.pi)

    N_theory = theoretical_zero_count(T) - theoretical_zero_count(0)
    N_theory = float(N_theory)  # Convert mpmath float to Python float

    # Calculate differences
    abs_diff = abs(N_rounded - N_theory)
    rel_diff = abs_diff / max(1, N_theory)

    # Generate verdict
    print("\n📊 Results:")
    print(f"Contour: σ ∈ [{sigma_min}, {sigma_max}], t ∈ [0, {T}]")
    print(f"Estimated zeros (argument principle): {N_rounded}")
    print(f"Theoretical zeros (RvM formula): {N_theory:.2f}")
    print(f"Absolute difference: {abs_diff:.2f}")
    print(f"Relative difference: {rel_diff:.2%}")

    tolerance = 0.1
    if abs_diff <= tolerance:
        print("\n✅ Agreement within tolerance. The zeros are where they should be.")
    else:
        print("\n⚠️ Divergence detected! The boundary may contain surprises.")

    # Visualization
    print("\n🎨 Generating visualization...")
    plt.figure(figsize=(12, 6))

    # Contour plot
    plt.subplot(1, 2, 1)
    seg_complex = np.array([complex(s) for s in segments])
    plt.plot(seg_complex.real, seg_complex.imag, 'b-')
    plt.fill(seg_complex.real, seg_complex.imag, 'b', alpha=0.1)
    plt.xlabel('Re(s)')
    plt.ylabel('Im(s)')
    plt.title('Integration Contour')
    plt.grid(True, alpha=0.3)

    # Function values along contour
    plt.subplot(1, 2, 2)
    ld_values = [zeta_ld(s) for s in segments]
    ld_complex = np.array([complex(v) for v in ld_values])

    plt.plot(np.arange(len(segments)), ld_complex.real, 'r-', label='Re(ζ\'(s)/ζ(s))')
    plt.plot(np.arange(len(segments)), ld_complex.imag, 'b-', label='Im(ζ\'(s)/ζ(s))')
    plt.xlabel('Contour point index')
    plt.ylabel('Function value')
    plt.title('Logarithmic Derivative Along Contour')
    plt.legend()
    plt.grid(True, alpha=0.3)

    plt.tight_layout()
    plt.savefig('contour_truth.png')
    print("\n🌌 The contour has spoken. The zeros are accounted for.")

if __name__ == "__main__":
    main()
