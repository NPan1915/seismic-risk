# Seismic hazard & exposure pipeline

USGS catalog (1900+) -> PostGIS (Neon) -> spatially-validated Random Forest -> hazard x exposure ranking -> 3D globe.

## Files
| file | role |
|---|---|
| `schema.sql` | PostGIS tables: `earthquakes` (GiST + BRIN + JSONB/GIN), `plate_boundaries`, `cities` |
| `ingest.py` / `load_plates.py` / `load_cities.py` | data loaders (quakes are upserted; USGS revises events) |
| `features.py` | per-cell features, plate-boundary distance and population exposure computed **in SQL** |
| `train.py` | baselines, spatial-block CV, hazard + rate-change models, `zones.json`, `metrics.json` |
| `refresh.py`, `.github/workflows/refresh.yml` | weekly incremental ingest, retrain, commit `zones.json`; Vercel redeploys |
| `globe.html` | 3D globe (loads `zones.json` next to it) |

## Method
- Label: any M6+ in the last 10 years per 2° cell; features use only data before that window (temporal split).
- Models compared: rate only, boundary only, rate+boundary, full, plus two zero-training heuristics. `lat/lon` are excluded so the model can't memorise regions.
- Validation: `StratifiedGroupKFold` over 30° lat/lon blocks (whole regions held out); random-CV AUC is printed alongside to show leakage inflation.
- Drivers: permutation importance on held-out regions.
- Impact: `risk x population within 100 km`; the globe's "impact" mode sizes dots by log-scaled impact.
- Rate-change: among active cells, predict whether the M4.5+ rate rises >=1.5x in the next decade.

## Run once
```
psql -f schema.sql
python load_plates.py && python load_cities.py && python ingest.py
python train.py        # prints the baseline table; writes zones.json, metrics.json
```

## Live deployment
Neon (Postgres+PostGIS) holds the data; a GitHub Action refreshes it weekly and commits `zones.json`; Vercel serves the site. See `SETUP_GUIDE.md`.

New to this? Start with `BEGINNER_GUIDE.md`. Short reference: `SETUP_GUIDE.md`. See `LIMITATIONS.md` for what these numbers do and don't mean.
