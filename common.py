import os, psycopg2
def _load_env(path=".env"):
    """Read KEY=VALUE lines from a local .env file (so beginners don't need `export`)."""
    if os.path.exists(path):
        for line in open(path, encoding="utf-8-sig"):
            line = line.strip()
            if line and not line.startswith("#") and "=" in line:
                k, v = line.split("=", 1); os.environ.setdefault(k.strip(), v.strip().strip('"').strip("'"))
_load_env()
def connect():
    """Use DATABASE_URL (Neon/Supabase/any Postgres) if set, else PGHOST/PGUSER/PGPASSWORD/PGDATABASE."""
    if os.environ.get("DATABASE_URL"):
        return psycopg2.connect(os.environ["DATABASE_URL"])
    return psycopg2.connect(host=os.environ["PGHOST"], user=os.environ["PGUSER"], password=os.environ["PGPASSWORD"],
                            dbname=os.environ.get("PGDATABASE", "quakes"), sslmode="require")
