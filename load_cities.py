"""Load GeoNames cities15000 (population exposure proxy). Run once."""
import io, zipfile, requests
from psycopg2.extras import execute_values
from common import connect
z = zipfile.ZipFile(io.BytesIO(requests.get("https://download.geonames.org/export/dump/cities15000.zip", timeout=120).content))
rows = []
for line in z.open("cities15000.txt").read().decode().splitlines():
    c = line.split("\t")
    rows.append((int(c[0]), c[1], int(c[14]), f"SRID=4326;POINT({c[5]} {c[4]})"))
conn = connect()
with conn, conn.cursor() as cur:
    execute_values(cur, "INSERT INTO cities (geonameid,name,pop,geom) VALUES %s ON CONFLICT (geonameid) DO UPDATE SET pop=EXCLUDED.pop", rows)
print(len(rows), "cities loaded")
