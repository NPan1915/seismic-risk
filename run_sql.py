"""Run a .sql file against your database:  python run_sql.py schema.sql   (replaces the psql tool)"""
import sys
from common import connect
conn = connect(); conn.autocommit = True
with conn.cursor() as cur: cur.execute(open(sys.argv[1], encoding="utf-8").read())
print("OK: ran", sys.argv[1])
