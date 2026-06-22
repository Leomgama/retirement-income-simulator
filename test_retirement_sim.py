import numpy as np
from retirement_sim import (SimInputs, simulate, run_paths,
                            lognormal_params, portfolio_params)


def test_zero_volatility_matches_closed_form():
    # With no volatility, the simulated path must equal the exact annuity formula.
    P, S, r, n = 1_000_000.0, 40_000.0, 0.05, 30
    mu, sigma = lognormal_params(r, 0.0)          # std=0 -> deterministic return r
    bal, _ = run_paths(P, S, n, mu, sigma, n_sims=1, seed=1)
    closed = np.array([P*(1+r)**t - S*(1+r)*((1+r)**t - 1)/r for t in range(n+1)])
    assert np.allclose(bal[0], closed, rtol=0, atol=1e-6)


def test_more_spending_lowers_success():
    base = simulate(SimInputs(1_000_000, 40_000, 65, 95, 0.6))["success_prob"]
    more = simulate(SimInputs(1_000_000, 55_000, 65, 95, 0.6))["success_prob"]
    assert more < base


def test_more_savings_raises_success():
    base = simulate(SimInputs(1_000_000, 40_000, 65, 95, 0.6))["success_prob"]
    more = simulate(SimInputs(1_300_000, 40_000, 65, 95, 0.6))["success_prob"]
    assert more > base


def test_longer_horizon_lowers_success():
    base = simulate(SimInputs(1_000_000, 40_000, 65, 95, 0.6))["success_prob"]
    longer = simulate(SimInputs(1_000_000, 40_000, 65, 105, 0.6))["success_prob"]
    assert longer < base


def test_reproducible_with_seed():
    a = simulate(SimInputs(1_000_000, 40_000, 65, 95, 0.6, seed=7))["success_prob"]
    b = simulate(SimInputs(1_000_000, 40_000, 65, 95, 0.6, seed=7))["success_prob"]
    assert a == b


def test_converges_as_sims_grow():
    big = simulate(SimInputs(1_000_000, 40_000, 65, 95, 0.6, n_sims=200_000, seed=0))["success_prob"]
    for nn in (10_000, 50_000):
        sp = simulate(SimInputs(1_000_000, 40_000, 65, 95, 0.6, n_sims=nn, seed=0))["success_prob"]
        assert abs(sp - big) < 0.01


def test_four_percent_anchor_in_published_band():
    sp = simulate(SimInputs(1_000_000, 40_000, 65, 95, 0.6))["success_prob"]
    assert 0.80 <= sp <= 0.92