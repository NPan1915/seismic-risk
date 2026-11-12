"""Load PB2002_boundaries.json (Bird 2003) into plate_boundaries. Run once after schema.sql."""
import json
from psycopg2.extras import execute_values
from common import connect
conn = connect()
feats = json.load(open("PB2002_boundaries.json"))["features"]
rows = []
for f in feats:
    pts = ",".join(f"{x} {y}" for x, y in f["geometry"]["coordinates"])
    rows.append((f["properties"]["Name"], json.dumps(f["properties"]), f"SRID=4326;LINESTRING({pts})"))
with conn, conn.cursor() as cur:
    cur.execute("TRUNCATE plate_boundaries RESTART IDENTITY")
    execute_values(cur, "INSERT INTO plate_boundaries (name, props, geom) VALUES %s", rows)
print(len(rows), "boundary segments loaded")
