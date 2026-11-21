"""Per-cell event history + telemetry for the globe's side panel -> details.json (loaded lazily on first click)."""
import json
import pandas as pd
from features import GRID
DECADES = list(range(1900, 2030, 10))            # 1900s .. 2020s -> 13 buckets
def key(lat, lon): return f"{lat + 0.0:g}_{lon + 0.0:g}"     # must match the JS key: `${lat}_${lon}`

def _cell(col): return f"ST_{col}(ST_SnapToGrid(geom::geometry, {GRID}))"
STATS_SQL = f"""
WITH e AS (SELECT {_cell('X')} AS clon, {_cell('Y')} AS clat, mag, depth_km, event_time FROM earthquakes)
SELECT clon AS lon, clat AS lat, COUNT(*) AS n,
  COUNT(*) FILTER (WHERE mag >= 6) AS n6, COUNT(*) FILTER (WHERE mag >= 7) AS n7,
  COALESCE(AVG(depth_km), 0) AS depth_mean, MAX(event_time) AS last,
  COUNT(*) FILTER (WHERE depth_km < 70) AS d_sh,
  COUNT(*) FILTER (WHERE depth_km >= 70 AND depth_km < 300) AS d_mid,
  COUNT(*) FILTER (WHERE depth_km >= 300) AS d_deep,
  COUNT(*) FILTER (WHERE mag < 5) AS m_lt5, COUNT(*) FILTER (WHERE mag >= 5 AND mag < 6) AS m_5,
  COUNT(*) FILTER (WHERE mag >= 6 AND mag < 7) AS m_6, COUNT(*) FILTER (WHERE mag >= 7) AS m_7,
  {', '.join(f"COUNT(*) FILTER (WHERE mag >= 5 AND EXTRACT(year FROM event_time) BETWEEN {y} AND {y + 9}) AS dec_{y}" for y in DECADES)}
FROM e GROUP BY clon, clat"""
EVENTS_SQL = f"""
WITH e AS (SELECT {_cell('X')} AS clon, {_cell('Y')} AS clat, event_time, mag, depth_km,
                  COALESCE(extra->>'place', '') AS place FROM earthquakes WHERE mag IS NOT NULL),
r AS (SELECT *, row_number() OVER (PARTITION BY clon, clat ORDER BY event_time DESC) AS rr,
                row_number() OVER (PARTITION BY clon, clat ORDER BY mag DESC, event_time DESC) AS rb FROM e)
SELECT clon AS lon, clat AS lat, rr, rb, event_time, mag, depth_km, place FROM r WHERE rr <= 6 OR rb <= 3"""

def _ev(r): return [r.event_time.strftime("%Y-%m-%dT%H:%MZ"), round(float(r.mag), 1),
                    None if pd.isna(r.depth_km) else round(float(r.depth_km)), (r.place or "").strip()]

def assemble(stats, events, now, keep, generated):
    """stats/events: DataFrames from the SQL above; now: scored cells; keep: set of (lat, lon) cells to export."""
    cells = {}
    for r in stats.itertuples():
        if (r.lat, r.lon) not in keep: continue
        cells[key(r.lat, r.lon)] = dict(n=int(r.n), n6=int(r.n6), n7=int(r.n7), dm=round(float(r.depth_mean)), last=r.last.strftime("%Y-%m-%dT%H:%MZ"),
            dp=[int(r.d_sh), int(r.d_mid), int(r.d_deep)], mb=[int(r.m_lt5), int(r.m_5), int(r.m_6), int(r.m_7)],
            dec=[int(getattr(r, f"dec_{y}")) for y in DECADES], rec=[], big=[])
    for r in events.sort_values(["rr", "rb"]).itertuples():
        c = cells.get(key(r.lat, r.lon))
        if c is None: continue
        if r.rr <= 6: c["rec"].append(_ev(r))
        if r.rb <= 3: c["big"].append(_ev(r))
    for r in now.itertuples():                                   # model-side telemetry for the same cells
        c = cells.get(key(r.lat, r.lon))
        if c is not None: c.update(r10=int(r.n_recent10), p10=int(r.n_prior10), sd=round(float(r.mag_std), 2))
    for c in cells.values(): c["big"].sort(key=lambda e: (-e[1], e[0]))   # biggest first
    return dict(generated=generated, cells=cells)

def build(conn, now, zones, generated):
    stats, events = pd.read_sql(STATS_SQL, conn), pd.read_sql(EVENTS_SQL, conn)
    return assemble(stats, events, now, set(zip(zones.lat, zones.lon)), generated)

def write(d, path="details.json"):
    json.dump(d, open(path, "w"), separators=(",", ":"))
