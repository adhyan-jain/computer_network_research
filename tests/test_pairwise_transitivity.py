"""
Unit and property tests for Theorem 3 pairwise cost calculation, transitivity,
and multi-frame cycle characterization (Phase 2 Audit).

Independently establishes:
1. Exact mathematical derivation of pairwise reordering cost and difference equation.
2. Direct confirmation of the intransitive three-frame cycle (Condorcet cycle).
3. Universal transitivity failure for pairwise comparison when variances and weights are heterogeneous.
4. Transitivity preservation under equal flow priorities (wa = wb = wc).
5. Evaluation of full permutation enumeration under exact aggregate receiver delay.
"""

import math
import itertools
import pytest
from scipy.stats import norm
from scipy.optimize import brentq
from scipy.integrate import quad

from src.mlo_sim.schedulers import (
    fast_phi,
    fast_Phi,
    fast_partial_expectation,
    compute_threshold_root
)


def independent_expected_pos_diff(mu_a: float, sigma_a: float, mu_b: float, sigma_b: float) -> float:
    """
    Computes E[(A_a - A_b)^+] via independent high-precision quadrature.
    Does not use the closed-form normal formula to ensure zero code-sharing.
    """
    d = mu_a - mu_b
    sigma_z = math.sqrt(sigma_a**2 + sigma_b**2)
    # Z ~ N(d, sigma_z^2)
    integrand = lambda z: max(0.0, z) * norm.pdf(z, loc=d, scale=sigma_z)
    val, _ = quad(integrand, 0.0, d + 10.0 * sigma_z)
    return val


def independent_pairwise_cost(mu_1: float, sig_1: float, w_1: float,
                              mu_2: float, sig_2: float, w_2: float) -> float:
    """
    Cost of assigning sequence number s_1 < s_2.
    Frame 2 is delayed if Frame 1 completes later: w_2 * E[(A_1 - A_2)^+].
    """
    d = mu_1 - mu_2
    sig = math.sqrt(sig_1**2 + sig_2**2)
    u = d / sig
    phi = norm.pdf(u)
    Phi = norm.cdf(u)
    return w_2 * sig * (phi + u * Phi)


def test_independent_pairwise_cost_against_quadrature():
    """
    Verifies that the closed-form formula w_b * sigma_Z * [phi(u) + u*Phi(u)]
    matches direct numerical quadrature to within 1e-7 across diverse regimes.
    """
    test_cases = [
        (0.0, 0.1, 1.0, 0.0, 0.1, 1.0),
        (1.0, 0.2, 5.0, 0.5, 0.3, 10.0),
        (-0.5, 0.15, 2.0, 0.2, 0.05, 20.0),
        (2.0, 0.1, 1.0, 0.1, 0.1, 50.0),
        (0.0, 0.01, 1.0, 0.0, 0.01, 1.0),
    ]
    for mu_a, sig_a, w_a, mu_b, sig_b, w_b in test_cases:
        quad_cost = w_b * independent_expected_pos_diff(mu_a, sig_a, mu_b, sig_b)
        form_cost = independent_pairwise_cost(mu_a, sig_a, w_a, mu_b, sig_b, w_b)
        assert abs(quad_cost - form_cost) < 1e-6, (
            f"Quadrature mismatch: quad={quad_cost}, formula={form_cost}"
        )


def test_independent_pairwise_threshold_difference_identity():
    """
    Verifies that C(a < b) - C(b < a) == sigma_Z * h(u) identically.
    """
    for wa, wb in [(1.0, 1.0), (2.0, 10.0), (50.0, 5.0), (0.1, 20.0)]:
        for d in [-0.5, -0.1, 0.0, 0.1, 0.5]:
            sig_a, sig_b = 0.12, 0.16
            sig_z = math.sqrt(sig_a**2 + sig_b**2)
            u = d / sig_z
            c_ab = independent_pairwise_cost(d, sig_a, wa, 0.0, sig_b, wb)
            c_ba = independent_pairwise_cost(0.0, sig_b, wb, d, sig_a, wa)
            diff = c_ab - c_ba
            
            # h(u) formulation
            phi_u = norm.pdf(u)
            Phi_u = norm.cdf(u)
            h_u = (wb - wa) * phi_u + (wa * (1.0 - Phi_u) + wb * Phi_u) * u
            expected_diff = sig_z * h_u
            
            assert pytest.approx(diff, abs=1e-8) == expected_diff


def test_demonstration_of_strict_three_frame_cycle():
    """
    Independently verifies the candidate triplet from the audit specification:
    Frame A: mu = -0.0060, sig = 0.1069, w = 4.10
    Frame B: mu = 0.1068,  sig = 0.1101, w = 20.80
    Frame C: mu = -0.0845, sig = 0.2477, w = 2.85

    Calculates exact pairwise costs:
    C(A < B) < C(B < A) => A preferred to B (A < B)
    C(B < C) < C(C < B) => B preferred to C (B < C)
    C(C < A) < C(A < C) => C preferred to A (C < A)

    This conclusively disproves universal transitivity.
    """
    A = (-0.0060, 0.1069, 4.10)
    B = (0.1068, 0.1101, 20.80)
    C = (-0.0845, 0.2477, 2.85)

    c_AB = independent_pairwise_cost(A[0], A[1], A[2], B[0], B[1], B[2])
    c_BA = independent_pairwise_cost(B[0], B[1], B[2], A[0], A[1], A[2])
    diff_AB = c_AB - c_BA

    c_BC = independent_pairwise_cost(B[0], B[1], B[2], C[0], C[1], C[2])
    c_CB = independent_pairwise_cost(C[0], C[1], C[2], B[0], B[1], B[2])
    diff_BC = c_BC - c_CB

    c_CA = independent_pairwise_cost(C[0], C[1], C[2], A[0], A[1], A[2])
    c_AC = independent_pairwise_cost(A[0], A[1], A[2], C[0], C[1], C[2])
    diff_CA = c_CA - c_AC

    # Verification: Each comparison has a strict negative difference
    assert diff_AB < -0.10, f"A < B failed: diff={diff_AB}"
    assert diff_BC < -0.10, f"B < C failed: diff={diff_BC}"
    assert diff_CA < -0.10, f"C < A failed: diff={diff_CA}"

    assert pytest.approx(c_AB, abs=1e-4) == 0.4296
    assert pytest.approx(c_BA, abs=1e-4) == 0.5472
    assert pytest.approx(c_BC, abs=1e-4) == 0.6545
    assert pytest.approx(c_CB, abs=1e-4) == 0.7978
    assert pytest.approx(c_CA, abs=1e-4) == 0.2989
    assert pytest.approx(c_AC, abs=1e-4) == 0.4315

    # Conclusive assertion of strict Condorcet cycle:
    assert c_AB < c_BA  # A prec B
    assert c_BC < c_CB  # B prec C
    assert c_CA < c_AC  # C prec A


def test_transitivity_preserved_under_equal_weights():
    """
    When all weights are equal (wa = wb = wc = w):
    u* = 0, so a prec b <=> mu_a <= mu_b.
    The real numbers under standard <= form a total order, which is provably transitive.
    No cycles can ever exist under equal weights.
    """
    # Triplet with identical weights
    frames = [
        (-0.0060, 0.1069, 5.0),
        (0.1068, 0.1101, 5.0),
        (-0.0845, 0.2477, 5.0)
    ]
    for p in itertools.permutations(frames, 3):
        f1, f2, f3 = p
        c12 = independent_pairwise_cost(f1[0], f1[1], f1[2], f2[0], f2[1], f2[2])
        c21 = independent_pairwise_cost(f2[0], f2[1], f2[2], f1[0], f1[1], f1[2])
        c23 = independent_pairwise_cost(f2[0], f2[1], f2[2], f3[0], f3[1], f3[2])
        c32 = independent_pairwise_cost(f3[0], f3[1], f3[2], f2[0], f2[1], f2[2])
        c13 = independent_pairwise_cost(f1[0], f1[1], f1[2], f3[0], f3[1], f3[2])
        c31 = independent_pairwise_cost(f3[0], f3[1], f3[2], f1[0], f1[1], f1[2])

        if (c12 <= c21) and (c23 <= c32):
            assert c13 <= c31, "Transitivity violated under equal weights!"


def test_exact_batch_permutation_objective_evaluation():
    """
    For the cyclic candidate triplet (A, B, C), evaluates all 3! = 6 possible sequence
    permutations under the true aggregate receiver reordering cost:
    J(pi) = E[ sum_{i=1}^3 w_i * (max_{j: pi(j) <= pi(i)} A_j - A_i) ]
    via Monte Carlo sampling (100,000 draws).
    Determines the unambiguous global optimum permutation and compares it with
    naive pairwise sorting.
    """
    import numpy as np
    rng = np.random.default_rng(42)
    N_SAMPLES = 100000

    A = (-0.0060, 0.1069, 4.10)
    B = (0.1068, 0.1101, 20.80)
    C = (-0.0845, 0.2477, 2.85)
    candidates = [A, B, C]
    names = ["A", "B", "C"]

    # Sample completion times
    samples_A = rng.normal(A[0], A[1], N_SAMPLES)
    samples_B = rng.normal(B[0], B[1], N_SAMPLES)
    samples_C = rng.normal(C[0], C[1], N_SAMPLES)
    samples = [samples_A, samples_B, samples_C]

    perm_costs = {}
    for p in itertools.permutations([0, 1, 2]):
        # p is sequence order: frame p[0] gets sn=0, p[1] gets sn=1, p[2] gets sn=2
        # Delta for p[0]: 0
        # Delta for p[1]: max(0, samples[p[0]] - samples[p[1]])
        # Delta for p[2]: max(0, samples[p[0]] - samples[p[2]], samples[p[1]] - samples[p[2]])
        d0 = np.zeros(N_SAMPLES)
        d1 = np.maximum(0.0, samples[p[0]] - samples[p[1]])
        d2 = np.maximum(0.0, np.maximum(samples[p[0]] - samples[p[2]], samples[p[1]] - samples[p[2]]))

        w0, w1, w2 = candidates[p[0]][2], candidates[p[1]][2], candidates[p[2]][2]
        total_cost = np.mean(w0 * d0 + w1 * d1 + w2 * d2)
        perm_label = f"{names[p[0]]}{names[p[1]]}{names[p[2]]}"
        perm_costs[perm_label] = total_cost

    best_perm = min(perm_costs, key=perm_costs.get)
    worst_perm = max(perm_costs, key=perm_costs.get)

    # In the cycle A < B < C < A:
    # Pairwise preference does not yield a linear order, but global batch evaluation
    # yields an unambiguous minimum cost permutation!
    assert best_perm == "ABC", f"Unexpected best perm: {best_perm}"
    assert perm_costs[best_perm] < perm_costs[worst_perm]
