"""USGS ComCat -> Postgres. `python ingest.py` backfills 1900..now; refresh.py calls ingest_range() for increments."""
import json, datetime as dt, requests
from psycopg2.extras import execute_values
from common import connect
API = "https://earthquake.usgs.gov/fdsnws/event/1/query"
def fetch(s, e, minmag):
    r = requests.get(API, params=dict(format="geojson", starttime=s, endtime=e, minmagnitude=minmag,
                                      orderby="time-asc", limit=20000), timeout=180)
    r.raise_for_status(); feats = r.json()["features"]
    if len(feats) >= 20000: raise RuntimeError(f"API cap hit {s}..{e}; use a smaller window")
    return feats
def rows(feats):
    for f in feats:
        p, (lon, lat, *d) = f["properties"], f["geometry"]["coordinates"]
        if p["mag"] is None: continue
        extra = {k: p[k] for k in ("place", "magType", "tsunami", "felt", "mmi", "alert", "sig") if p.get(k) is not None}
        yield (f["id"], "usgs", dt.datetime.fromtimestamp(p["time"]/1000, dt.timezone.utc), p["mag"],
               d[0] if d else None, f"SRID=4326;POINT({lon} {lat})", json.dumps(extra))
def ingest_range(conn, start, end):
    s = start
    while s < end:
        e = min(s + dt.timedelta(days=183), end)
        data = list(rows(fetch(s.isoformat(), e.isoformat(), 5.5 if s.year < 1973 else 4.5)))
        if data:
            with conn, conn.cursor() as cur:   # DO UPDATE: USGS revises magnitudes/depths after the fact
                execute_values(cur, """INSERT INTO earthquakes (id,source,event_time,mag,depth_km,geom,extra) VALUES %s
                  ON CONFLICT (id) DO UPDATE SET mag=EXCLUDED.mag, depth_km=EXCLUDED.depth_km, extra=EXCLUDED.extra""", data)
        print(s, "->", e, len(data)); s = e
if __name__ == "__main__":
    ingest_range(connect(), dt.date(1900, 1, 1), dt.date.today() + dt.timedelta(days=1))
