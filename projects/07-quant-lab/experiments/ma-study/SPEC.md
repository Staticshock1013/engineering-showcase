# Experiment: ma-study

Status: PRE-REGISTERED (frozen before first result run)

## Hypothesis

On NQ (CME E-mini Nasdaq-100) daily front-month-style closes, classic
moving-average cross signals have a higher hit rate on the sign of the
next-session close-to-close return than a random-entry baseline that fires
on the **same calendar days** with shuffled trade direction.

## Instrument and costs (explicit)

- Contract: **NQ** (not MNQ)
- Cost model: `FuturesCostModel(contract="NQ")`
- Commission basis: **USD per contract per side**
- Commission: **$2.50 per side** for NQ (this is not "$2.50 round trip for MNQ")
- Slippage: 1 tick; tick size 0.25; point value $20
- Round-trip cost for 1 NQ = 2 × ($2.50 + 1×0.25×20) = **$15.00**
- Every result payload must include `cost_assumptions` with `contract="NQ"` and
  `commission_basis="usd_per_contract_per_side"`

## Data window

- Series: synthetic NQ daily closes labeled as such in
  `data/fixtures/nq_daily_synthetic.csv` (stand-in until Massive live data is
  configured). Same rules apply when swapping to Massive NQ front-month daily.
- Warmup: 200 sessions of history required before any signal is eligible.
- **Development (spent set):** 2020-01-02 through 2023-12-29 inclusive.
  Used for exploration and for documenting in-sample behavior. Spent once
  the holdout is opened.
- **Holdout (run once):** 2024-01-02 through 2024-12-31 inclusive.
  Never used for tuning thresholds, signal definitions, or cost assumptions.
- Holdout start aligns with `QUANT_LAB_HOLDOUT_START=2024-01-01` (first
  holdout session on/after that date in the series).

## Moving-average definitions

Causal simple moving averages of daily `close` only (no centered windows):

- `MA20`  = SMA(close, window=20,  min_periods=20)
- `MA50`  = SMA(close, window=50,  min_periods=50)
- `MA200` = SMA(close, window=200, min_periods=200)

Feature at time `t` uses closes `≤ t` only (enforced by no-lookahead tests).

## Signal rules

Signals are formed at the close of bar `t`. Position is held over bar `t+1`
(engine no-lookahead shift). One-session evaluation uses the return
`close[t+1] - close[t]`.

| Signal id | Rule | Direction |
|-----------|------|-----------|
| `price_cross_ma20_up` | close crosses from ≤ MA20 to > MA20 | +1 (long) |
| `price_cross_ma20_down` | close crosses from ≥ MA20 to < MA20 | -1 (short) |
| `golden_cross` | MA50 crosses from ≤ MA200 to > MA200 | +1 (long) |
| `death_cross` | MA50 crosses from ≥ MA200 to < MA200 | -1 (short) |

Families for thresholding:

- `ma20_family` = `price_cross_ma20_up` ∪ `price_cross_ma20_down`
- `cross_family` = `golden_cross` ∪ `death_cross`

## Baseline

Random-entry baseline on the **same signal days**:

- Keep the event dates from the MA signal family.
- Replace direction with independent draws from `{+1, -1}` with equal
  probability.
- Development baseline RNG seed: `42`
- Holdout baseline RNG seed: `43`
- Same cost model applied to baseline one-session round trips.

## Primary metric

Hit rate = fraction of events where
`sign(close[t+1] - close[t]) == signal_direction`
(zeros in the forward point change count as misses).

Report hit rate and event count `n` for each signal and family, on
development and holdout separately.

## Secondary metric

Mean net USD PnL per event for a one-session round trip of 1 NQ contract
in the signal direction, using the explicit NQ cost model above
(entry + exit = one round trip charged per event). Compare to the random
baseline on the same days.

## Pass threshold (holdout only)

On the **holdout** window, the experiment **passes** if at least one of
`ma20_family` or `cross_family` satisfies:

1. `n ≥ 30` events, and
2. `hit_rate_ma ≥ hit_rate_random + 0.02` (2.0 percentage points).

Otherwise the experiment **fails**. Failure on holdout is an acceptable,
honest outcome and must be reported as such. The development window must
not be used to revise this threshold after holdout results are known.

## Out of scope

- SPY, equities, 0DTE, options, and MNQ
- Multi-session holding-period optimization
- Parameter search over MA lengths (20/50/200 are fixed)

## Reproducibility

- Results must verify `HASH.txt` matches SHA-256 of this `SPEC.md`
  (bytes as committed, UTF-8, LF line endings).
- Do not edit this SPEC after HASH.txt is committed without bumping a new
  experiment folder.
