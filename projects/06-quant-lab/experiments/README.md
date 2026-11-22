# Experiments

Each experiment gets its own folder with a pre-registered `SPEC.md` and `HASH.txt`
(SHA-256 of the frozen spec). Results must be checked against that hash.

## Separation rules

| Experiment family | Folder pattern | Data notes |
|-------------------|----------------|------------|
| NQ futures / MA / lead-lag / ML | `experiments/nq-*` | Massive futures aggregates + volume roll |
| SPY 0DTE / option premium | `experiments/spy-0dte-*` | **Separate** — needs option historicals (Massive or Robinhood). Not covered by NQ roll logic. |

Do not mix NQ futures specs with SPY 0DTE specs in one folder.

The SPY 0DTE `SPEC.md` is intentionally not created yet — it waits on the five open design decisions from the project owner.
