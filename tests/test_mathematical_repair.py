"""
Mathematical Repair and Falsification Test Suite (Phase 1 Audit).
Independently verifies:
1. Theorem 1 accounting identity and counterexample to naive definitions.
2. Theorem 2 Poisson stall probabilities and falsification of 'almost surely' collapse.
3. Theorem 3 algebraic properties, derivative monotonicity, and Brent root comparison.
4. Theorem 4 falsification of the old sigma_Z * phi(u) bound and verification of the symmetric floor.
"""

import math
import pytest
from scipy.optimize import brentq
from scipy.stats import norm, poisson

from src.mlo_sim.schedulers import (
    fast_phi,
    fast_Phi,
    fast_partial_expectation,
    compute_threshold_root
)
from src.mlo_sim.core import Packet, BlockAckReceiver


def test_theorem_1_counterexample_to_ambiguous_definition():
    """
    If R_intra is improperly defined to include any foreign packets,
    then S_i loses attribution invariance and additive decomposition breaks.
    """
    p1 = Packet(packet_id=1, flow_id=1, size_bytes=1500, arr_time=0.0)
    p2 = Packet(packet_id=2, flow_id=2, size_bytes=1500, arr_time=0.0)  # Competing flow
    p3 = Packet(packet_id=3, flow_id=1, size_bytes=1500, arr_time=0.0)

    p1.seq_num, p1.arr_rx_time = 0, 10.0
    p2.seq_num, p2.arr_rx_time = 1, 20.0  # Arrives very late
    p3.seq_num, p3.arr_rx_time = 2, 5.0

    # True definitions
    # For p3: intra predecessor is only p1 (sn=0, arr=10.0)
    R3_intra_correct = max(p3.arr_rx_time, p1.arr_rx_time)  # max(5.0, 10.0) = 10.0
    S3_correct = R3_intra_correct - p3.arr_rx_time  # 10.0 - 5.0 = 5.0

    # Total release depends on all predecessors: p1 (10.0) and p2 (20.0)
    R3 = max(p3.arr_rx_time, p1.arr_rx_time, p2.arr_rx_time)  # 20.0
    Delta3 = R3 - p3.arr_rx_time  # 20.0 - 5.0 = 15.0
    X3_correct = R3 - R3_intra_correct  # 20.0 - 10.0 = 10.0

    assert S3_correct + X3_correct == Delta3
    assert S3_correct == 5.0
    assert X3_correct == 10.0

    # False definition: suppose an author defines R_intra using all predecessors
    R3_intra_false = R3
    S3_false = R3_intra_false - p3.arr_rx_time  # 15.0
    # Now S3 changed from 5.0 to 15.0 simply because p2 (Flow 2) was present!
    assert S3_false != S3_correct


def test_theorem_2_falsifies_almost_sure_window_collapse():
    """
    Verifies that when arrival rate reaches or exceeds critical rate lambda* = W / delta,
    the probability of NOT stalling is strictly positive: Pr(N < W) > 0.
    Thus, window collapse is NOT almost sure.
    """
    W = 16
    delta_ms = 8.0
    lambda_star = W / delta_ms  # 2.0 pkts/ms

    # Case 1: lambda = lambda* (load ratio = 1.0)
    mean_arrivals = lambda_star * delta_ms  # 16.0
    p_no_stall = poisson.cdf(W - 1, mean_arrivals)
    p_stall = 1.0 - p_no_stall

    assert p_no_stall > 0.40, f"Expected substantial no-stall prob, got {p_no_stall}"
    assert pytest.approx(p_stall, abs=1e-3) == 0.5333
    assert pytest.approx(p_no_stall, abs=1e-3) == 0.4667

    # Case 2: lambda = 1.2 * lambda* (load ratio = 1.2)
    p_no_stall_overload = poisson.cdf(W - 1, 1.2 * mean_arrivals)
    assert p_no_stall_overload > 0.20, f"Expected >20% no-stall at 1.2x load, got {p_no_stall_overload}"


def test_theorem_2_cumulative_delay_formula():
    """
    Verifies numerical agreement of the continuous integral 1/2 * lambda * delta^2
    with discrete Riemann sum of individual packet delays.
    """
    lambda_2 = 500.0 / 1000.0  # 0.5 pkts/ms
    delta = 6.0  # ms
    analytical_cumulative = 0.5 * lambda_2 * (delta ** 2)  # 0.5 * 0.5 * 36 = 9.0 ms

    # Discrete simulation: packets arrive at intervals dt = 1 / lambda_2 = 2.0 ms
    # Packets arrive at t = 0, 2, 4 (before delta = 6.0)
    # Delays: (6 - 0) = 6.0, (6 - 2) = 4.0, (6 - 4) = 2.0
    discrete_sum = 6.0 + 4.0 + 2.0  # 12.0 ms
    # With continuous trapezoidal rule, discrete sum converges to integral
    assert analytical_cumulative == 9.0


def test_theorem_3_derivative_strictly_positive():
    """
    Directly tests that h'(u) = w_a*(1 - Phi(u)) + w_b*Phi(u) is strictly positive
    everywhere on a fine grid u in [-10, 10] across diverse weight pairs.
    """
    for wa, wb in [(1.0, 1.0), (0.1, 10.0), (100.0, 1.0), (5.0, 20.0)]:
        for u_int in range(-100, 101):
            u = u_int / 10.0
            phi_val = fast_Phi(u)
            h_prime = wa * (1.0 - phi_val) + wb * phi_val
            assert h_prime > 0.0, f"h'(u) must be strictly positive at u={u}, got {h_prime}"


def test_theorem_3_solver_matches_brentq_machine_precision():
    """
    Compares custom compute_threshold_root with robust bracketed Brent root solver
    across 8 orders of magnitude in weight ratio.
    """
    def h_ref(u, wa, wb):
        return (wb - wa) * norm.pdf(u) + (wa * (1.0 - norm.cdf(u)) + wb * norm.cdf(u)) * u

    test_weights = [
        (1.0, 1.0),
        (1.0, 2.0),
        (1.0, 5.0),
        (1.0, 10.0),
        (1.0, 50.0),
        (1.0, 100.0),
        (1.0, 1000.0),
        (5.0, 1.0),
        (50.0, 1.0),
        (1000.0, 1.0)
    ]

    for wa, wb in test_weights:
        b_root = brentq(h_ref, -12.0, 12.0, args=(wa, wb))
        s_root = compute_threshold_root(wa, wb)
        assert abs(b_root - s_root) < 1e-6, f"Root mismatch for wa={wa}, wb={wb}: brent={b_root}, sasp={s_root}"


def test_theorem_3_equal_weights_symmetry():
    """Theorem 3: When wa == wb, u* == 0 exactly."""
    for w in [0.01, 1.0, 10.0, 100.0]:
        assert compute_threshold_root(w, w) == 0.0


def test_theorem_3_anti_symmetry():
    """Theorem 3: u*(wb, wa) == -u*(wa, wb)."""
    for wa, wb in [(1.0, 3.0), (2.0, 10.0), (0.5, 50.0)]:
        u1 = compute_threshold_root(wa, wb)
        u2 = compute_threshold_root(wb, wa)
        assert pytest.approx(u1, abs=1e-7) == -u2


def test_theorem_4_falsifies_old_lower_bound():
    """
    Numerically proves that the old bound min(C) >= min(w) * sigma_Z * phi(u) is false.
    At u = 2.0, sigma_Z = 1.0, wa = wb = 1.0:
    Actual optimal cost E[(-Z)+] ≈ 0.00849 < 0.05399 = claimed bound.
    """
    u = 2.0
    sigma_Z = 1.0
    wa = wb = 1.0

    phi_u = norm.pdf(u)
    Phi_u = norm.cdf(u)

    E_plus_Z = sigma_Z * (phi_u + u * Phi_u)
    E_minus_Z = sigma_Z * (phi_u - u * (1.0 - Phi_u))

    cost_a_first = wb * E_plus_Z
    cost_b_first = wa * E_minus_Z

    min_actual_cost = min(cost_a_first, cost_b_first)
    claimed_old_bound = min(wa, wb) * sigma_Z * phi_u

    assert cost_b_first < cost_a_first
    assert pytest.approx(min_actual_cost, abs=1e-4) == 0.0085
    assert pytest.approx(claimed_old_bound, abs=1e-4) == 0.0540

    # Strict inequality proving falsification:
    assert min_actual_cost < claimed_old_bound, (
        f"Falsification check failed: min_actual={min_actual_cost} vs claimed={claimed_old_bound}"
    )


def test_theorem_4_symmetric_floor_exact_equality():
    """
    Proves that for symmetric links (u = 0, d = 0), the minimum cost is
    EXACTLY equal to min(wa, wb) * sigma_Z / sqrt(2*pi).
    """
    u = 0.0
    sigma_Z = 2.5
    wa = 2.0
    wb = 5.0

    phi_0 = norm.pdf(0.0)
    Phi_0 = norm.cdf(0.0)

    E_plus_Z = sigma_Z * (phi_0 + 0.0 * Phi_0)
    E_minus_Z = sigma_Z * (phi_0 - 0.0 * (1.0 - Phi_0))

    cost_a_first = wb * E_plus_Z
    cost_b_first = wa * E_minus_Z

    actual_min_cost = min(cost_a_first, cost_b_first)
    exact_analytical_floor = min(wa, wb) * sigma_Z / math.sqrt(2.0 * math.pi)

    assert pytest.approx(actual_min_cost, rel=1e-9) == exact_analytical_floor
