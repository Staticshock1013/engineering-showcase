# Final run instructions

## Local dashboard

From this project directory:

```bash
./run-local.sh
```

The script installs dependencies into an isolated local `.terratrend-deps` directory and starts
Streamlit. Open the local URL printed by Streamlit. This avoids requiring system-wide package
installation or `python3-venv`.

## Automated checks

```bash
./test.sh
```

The same dependency setup runs the deterministic test suite. CI runs the equivalent commands on
pushes and pull requests that change this project.

## What to verify in the dashboard

1. The global map and bar chart have a visible synthetic-data warning.
2. Use **Verified processed data variable** to inspect authenticated LST or NDVI period caches.
3. Expand **Verified sample provenance** to see product, CMR, QC, query, and source fields.
4. Select the matching 2024-06-25 LST caches for New York City and London to see the gated
   period-level city comparison.
5. Review the NYC and London fixed-season NDVI panels and their qualified side-by-side comparison.

The fixed-season panels use one DOY-177 16-day MOD13A2 composite per year. They are not annual
NDVI or annual trends. London represents the documented central/west tile-contained window only.
