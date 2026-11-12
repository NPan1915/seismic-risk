"""Sanity check:  python check_db.py   - prints what's in your database."""
from common import connect
conn = connect(); conn.autocommit = True; cur = conn.cursor()
def q(sql):
    try: cur.execute(sql); return cur.fetchone()
    except Exception as e: conn.rollback(); return f"(not available yet: {str(e).splitlines()[0]})"
print("Connected. PostGIS:", q("SELECT postgis_version()"))
print("Earthquakes (count, oldest, newest, biggest):", q("SELECT count(*), min(event_time)::date, max(event_time)::date, max(mag) FROM earthquakes"))
print("Plate boundary lines (expect 241):", q("SELECT count(*) FROM plate_boundaries"))
print("Cities (expect ~25,000):", q("SELECT count(*) FROM cities"))
print("Database size (free limit is about 512 MB):", q("SELECT pg_size_pretty(pg_database_size(current_database()))"))
