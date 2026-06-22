"""
Will My Money Last? - retirement income Monte Carlo engine.

Everything is in REAL (inflation-adjusted) dollars. Spending stays constant
in today's money, so we never model inflation as a separate variable.
"""
from dataclasses import dataclass
import numpy as np

# --- Capital-market assumptions (real, annual) -----------------------------
# Long-run US history (SBBI/Ibbotson 1926-2024, cross-checked vs Damodaran).
STOCK_REAL_MEAN = 0.07
STOCK_REAL_STD  = 0.20
BOND_REAL_MEAN  = 0.02
BOND_REAL_STD   = 0.06
STOCK_BOND_CORR = 0.0   # assume uncorrelated (a simplification; stated as a limitation)



@dataclass
class SimInputs:
    current_savings: float
    annual_spending: float
    retirement_age: int
    end_age: int
    stock_weight: float = 0.6
    n_sims: int = 10_000
    seed: int | None = 42


def portfolio_params(stock_weight: float):
    """Blend stock/bond assumptions into one portfolio mean and std (real, annual)."""
    w = stock_weight
    mean = w * STOCK_REAL_MEAN + (1 - w) * BOND_REAL_MEAN
    var = ((w * STOCK_REAL_STD) ** 2
           + ((1 - w) * BOND_REAL_STD) ** 2
           + 2 * w * (1 - w) * STOCK_BOND_CORR * STOCK_REAL_STD * BOND_REAL_STD)
    return mean, float(np.sqrt(var))



def lognormal_params(mean: float, std: float):
    """Arithmetic mean/std of simple returns -> mu/sigma of the underlying normal,
    so 1+R is lognormal with E[1+R]=1+mean and Var(1+R)=std**2. Keeps R > -100%."""
    m = 1.0 + mean
    v = std ** 2
    sigma2 = np.log(1 + v / m**2)
    mu = np.log(m) - 0.5 * sigma2
    return mu, float(np.sqrt(sigma2))


def run_paths(savings, spending, years, mu, sigma, n_sims, seed):
    """Core loop. Returns (balances [n_sims, years+1], ruin_year [n_sims])."""
    rng = np.random.default_rng(seed)
    growth = np.exp(rng.normal(mu, sigma, size=(n_sims, years)))  # = 1 + R per year
    balances = np.empty((n_sims, years + 1))
    balances[:, 0] = savings
    ruin_year = np.full(n_sims, -1)
    for t in range(years):
        can_fund = balances[:, t] >= spending
        newly_ruined = (~can_fund) & (ruin_year < 0)
        ruin_year[newly_ruined] = t
        after = np.where(can_fund, balances[:, t] - spending, 0.0)
        balances[:, t + 1] = after * growth[:, t]
    return balances, ruin_year



def simulate(inp: SimInputs):
    years = inp.end_age - inp.retirement_age
    mean, std = portfolio_params(inp.stock_weight)
    mu, sigma = lognormal_params(mean, std)
    balances, ruin_year = run_paths(inp.current_savings, inp.annual_spending,
                                    years, mu, sigma, inp.n_sims, inp.seed)
    survived = ruin_year < 0
    success_prob = float(survived.mean())
    pct = np.percentile(balances, [10, 25, 50, 75, 90], axis=0)
    failed = ~survived
    median_ruin_age = (float(inp.retirement_age + np.median(ruin_year[failed]))
                       if failed.any() else None)
    return {
        "success_prob": success_prob,
        "years": years,
        "port_mean": mean,
        "port_std": std,
        "percentiles": pct,                       # rows: 10,25,50,75,90
        "median_end_balance": float(np.median(balances[:, -1])),
        "median_ruin_age": median_ruin_age,
    }


if __name__ == "__main__":
    r = simulate(SimInputs(1_000_000, 40_000, 65, 95, 0.6))
    print(f"[4% anchor]   port mean={r['port_mean']:.3%} std={r['port_std']:.3%}  "
          f"success={r['success_prob']:.1%}  median end=${r['median_end_balance']:,.0f}")