"""
Unit and property tests verifying Theorem 3:
Optimal Sequence-Aware Scheduling Threshold and Gaussian Expectations.
"""

import math
import pytest
from scipy.stats import norm
from src.mlo_sim.schedulers import compute_threshold_root, gaussian_partial_expectation


def test_theorem_3_symmetry():
    """Verify that equal weights w_a = w_b yield root u* = 0."""
    for w in [0.1, 1.0, 5.0, 100.0]:
        u_star = compute_threshold_root(w, w)
        assert abs(u_star) < 1e-9


def test_theorem_3_asymmetric_direction():
    """
    Verify that when w_b > w_a (flow b is higher priority),
    u* < 0, favoring flow b to get the earlier sequence number.
    """
    # Test w_a = 1, w_b = 5
    u_star_5 = compute_threshold_root(1.0, 5.0)
    assert u_star_5 < 0.0

    # Test w_a = 1, w_b = 20
    u_star_20 = compute_threshold_root(1.0, 20.0)
    assert u_star_20 < u_star_5  # More negative as priority increases

    # Inverse test: w_a = 5, w_b = 1
    u_star_inv = compute_threshold_root(5.0, 1.0)
    assert u_star_inv > 0.0
    assert abs(u_star_5 + u_star_inv) < 1e-6  # Anti-symmetric property


def test_theorem_3_root_accuracy():
    """
    Verify that h(u*) is numerically zero at the found root u*.
    """
    for w_a, w_b in [(1.0, 2.0), (1.0, 10.0), (3.0, 15.0), (20.0, 2.0)]:
        u_star = compute_threshold_root(w_a, w_b)
        phi_u = norm.pdf(u_star)
        Phi_u = norm.cdf(u_star)
        h_val = (w_b - w_a) * phi_u + (w_a * (1.0 - Phi_u) + w_b * Phi_u) * u_star
        assert abs(h_val) < 1e-6, f"Root residual too large for w_a={w_a}, w_b={w_b}: {h_val}"


def test_gaussian_partial_expectation_identities():
    """Verify identity E[Z+] - E[(-Z)+] = mu for various distributions."""
    for mu, sigma in [(-2.0, 1.0), (0.0, 1.5), (3.0, 2.0)]:
        ez_pos = gaussian_partial_expectation(mu, sigma)
        ez_neg = gaussian_partial_expectation(-mu, sigma)
        diff = ez_pos - ez_neg
        assert abs(diff - mu) < 1e-9
