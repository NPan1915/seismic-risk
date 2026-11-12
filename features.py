"""Per-cell features. Features use events BEFORE `cut`; labels use events in [cut, end)."""
import pandas as pd
GRID = 2.0
SQL = """
WITH e AS (SELECT ST_SnapToGrid(geom::geometry, %(g)s) g, mag, depth_km, event_time FROM earthquakes)
SELECT ST_X(g) AS lon, ST_Y(g) AS lat,
  COUNT(*) FILTER (WHERE event_time < %(cut)s) AS n_hist,
  AVG(mag) FILTER (WHERE event_time < %(cut)s) AS mag_mean,
  MAX(mag) FILTER (WHERE event_time < %(cut)s) AS mag_max,
  COALESCE(STDDEV(mag) FILTER (WHERE event_time < %(cut)s),0) AS mag_std,
  AVG(depth_km) FILTER (WHERE event_time < %(cut)s) AS depth_mean,
  COALESCE(STDDEV(depth_km) FILTER (WHERE event_time < %(cut)s),0) AS depth_std,
  COUNT(*) FILTER (WHERE mag>=6 AND event_time < %(cut)s) AS n_m6_hist,
  COUNT(*) FILTER (WHERE mag>=4.5 AND event_time >= %(cut)s - interval '10 years' AND event_time < %(cut)s) AS n_recent10,
  COUNT(*) FILTER (WHERE mag>=4.5 AND event_time >= %(cut)s - interval '20 years' AND event_time < %(cut)s - interval '10 years') AS n_prior10,
  COUNT(*) FILTER (WHERE mag>=6 AND event_time >= %(cut)s AND event_time < %(end)s) AS n_m6_future,
  COUNT(*) FILTER (WHERE mag>=4.5 AND event_time >= %(cut)s AND event_time < %(end)s) AS n_m45_future
FROM e GROUP BY g HAVING COUNT(*) FILTER (WHERE event_time < %(cut)s) >= 5"""
CTX = """
SELECT v.lon, v.lat,
  (SELECT ST_Distance(ST_SetSRID(ST_MakePoint(v.lon,v.lat),4326)::geography, ST_Collect(b.geom::geometry)::geography)/1000.0
     FROM plate_boundaries b) AS dist_boundary_km,
  (SELECT COALESCE(SUM(c.pop),0) FROM cities c
     WHERE ST_DWithin(c.geom, ST_SetSRID(ST_MakePoint(v.lon,v.lat),4326)::geography, 100000)) AS pop100
FROM (SELECT unnest(%(lons)s::float8[]) AS lon, unnest(%(lats)s::float8[]) AS lat) v"""
def build(conn, cut, end):
    df = pd.read_sql(SQL, conn, params=dict(g=GRID, cut=cut.to_pydatetime(), end=end.to_pydatetime())).fillna(0)
    ctx = pd.read_sql(CTX, conn, params=dict(lons=df.lon.tolist(), lats=df.lat.tolist()))
    df = df.merge(ctx, on=["lon", "lat"], how="left")
    df["rate_ratio"] = (df.n_recent10 + 1) / (df.n_prior10 + 1)
    return df
