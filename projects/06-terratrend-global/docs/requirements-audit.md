# Submission requirements audit

This audit distinguishes implemented evidence from open scope. It does not treat a partial sample
as a completed global environmental-change solution.

| Requirement area | Evidence | Status |
|---|---|---|
| Reproducible local MVP | `run-local.sh`, `test.sh`, documented Python dependencies | Ready |
| Automated verification | Deterministic pytest suite; project GitHub Actions workflow | Ready |
| NASA Earth-observation access | Authenticated CMR discovery and protected MOD11A2/MOD13A2 HDF4 retrieval | Ready for sampled products |
| Scientific transformation | Product/version, in-file metadata, QC, scale, sinusoidal sampling, and provenance validation | Ready for implemented products |
| Explainable visualization | Synthetic global charts are labeled; verified samples expose CMR/product/QC provenance | Ready with stated scope |
| City comparison/export | Product, unit, interval, aggregation, QC, and sampling gates; provenance-rich CSVs | Ready for compatible period caches |
| Historical change | NYC/London DOY-177 fixed-season NDVI series, 2010–2024, with thresholded OLS statistics | Ready as fixed-season only |
| Annual/global trends | No complete annual global coverage or annual trend dataset | Not claimed |
| Broad London representation | Fixed-season London uses one tile-contained central/west window because the broader bbox crosses tiles | Limited and disclosed |
| Decision/policy use | No uncertainty, attribution, or operational validation | Not supported |

The NASA-facing evidence is intentionally bounded: verified sample products and a seasonal city
series demonstrate an auditable ingestion pattern, not a complete global monitoring service.
