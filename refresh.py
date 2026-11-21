"""Weekly job: incremental USGS ingest -> retrain -> write zones.json/metrics.json into the Vercel site folder.
The GitHub Action then commits those files and Vercel redeploys. env: DATABASE_URL"""
import datetime as dt, shutil, subprocess, sys
from common import connect
from ingest import ingest_range
conn = connect()
with conn.cursor() as cur:
    cur.execute("SELECT max(event_time) FROM earthquakes"); last = cur.fetchone()[0]
ingest_range(conn, (last.date() - dt.timedelta(days=3)) if last else dt.date(1900, 1, 1), dt.date.today() + dt.timedelta(days=1))
subprocess.run([sys.executable, "train.py"], check=True)
for f in ("zones.json", "metrics.json", "details.json"): shutil.copy(f, f"vercel-site/public/{f}")
print("refreshed", dt.datetime.now(dt.timezone.utc).isoformat())
