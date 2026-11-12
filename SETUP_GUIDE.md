# Setup guide (no AWS): Neon + GitHub + Vercel, all free tiers

Order: **(1) tools -> (2) Neon database -> (3) load data -> (4) train -> (5) GitHub -> (6) Vercel -> (7) weekly auto-refresh**.
Website wording changes now and then; look for the nearest equivalent if a label differs. Free-tier limits change too, so check each provider's pricing page.

**Cost:** $0 on free tiers. Nothing here needs a credit card (Neon, GitHub, Vercel Hobby all allow signup without one at the time of writing).

---
## 1. Install tools and get the code
- Python 3.12 (`python3 --version`), Git, Node.js 18+ (only for the Vercel CLI; skip if you deploy via GitHub import).
- `psql` client (optional but handy): macOS `brew install libpq`; Ubuntu/WSL `sudo apt install postgresql-client`; Windows: use WSL.

```
cd quake
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
```

---
## 2. Create the database on Neon (Postgres + PostGIS)
PostGIS is a Postgres *extension*: you enable it with one SQL command, you don't install anything.

1. Sign up at neon.tech (GitHub login is fine). **Create project**: name `quakes`, Postgres 16, pick the region closest to you.
2. On the project dashboard click **Connect** and copy the **connection string**. It looks like
   `postgresql://user:password@ep-xxxx.region.aws.neon.tech/neondb?sslmode=require`
   (the "aws" in the hostname is just where Neon runs; you don't use AWS yourself). This string contains your password; treat it like one.
3. Put it in an environment variable for this terminal session:
```
export DATABASE_URL='postgresql://...your string...'
```
   Every script reads `DATABASE_URL` automatically.
4. Check the connection and enable PostGIS:
```
psql "$DATABASE_URL" -c "CREATE EXTENSION IF NOT EXISTS postgis;"
psql "$DATABASE_URL" -c "SELECT postgis_full_version();"
```
A version string means PostGIS works. (`schema.sql` also runs the CREATE EXTENSION line.)

**Alternatives:** Supabase also offers free Postgres with PostGIS, but its free direct connection is IPv6-only, which GitHub Actions may not reach; Neon avoids that. For offline development you can run `docker run -p 5432:5432 -e POSTGRES_PASSWORD=pw postgis/postgis` and set `DATABASE_URL=postgresql://postgres:pw@localhost:5432/postgres`, but the weekly refresh in step 7 needs a database reachable from the internet.

**Storage:** the free tier is about 0.5 GB. This dataset (~500k-700k events plus indexes) should fit, but verify after loading (step 3). If you exceed it, either upgrade the plan or drop the oldest low-value rows.

---
## 3. Create tables and load the data
```
psql "$DATABASE_URL" -f schema.sql         # tables + spatial (GiST), time (BRIN), JSONB (GIN) indexes
python load_plates.py                       # 241 plate-boundary lines
python load_cities.py                       # ~25k cities >=15k people (GeoNames), for exposure
python ingest.py                            # USGS 1900-today; the slow one
```
- `ingest.py` takes roughly 20-60 minutes (~250 API calls). Progress lines print. **Safe to stop and rerun**: rows are upserted by event ID.
- Neon's free compute auto-suspends when idle; the first query after a pause takes a second or two. Normal.

**Verify**
```
psql "$DATABASE_URL" -c "SELECT count(*), min(event_time), max(event_time) FROM earthquakes;"
psql "$DATABASE_URL" -c "SELECT pg_size_pretty(pg_database_size(current_database()));"   # compare to the free limit
psql "$DATABASE_URL" -c "SELECT count(*) FROM earthquakes WHERE mag>=6 AND ST_DWithin(geom, ST_MakePoint(139.7,35.7)::geography, 300000);"
```
The last query (M6+ within 300 km of Tokyo) uses the spatial index; prefix it with `EXPLAIN` to see an index scan on `eq_geom_gist`, which is a nice interview talking point.

---
## 4. Train and read the results
```
python train.py
```
It prints the baseline table (spatial-block CV), the leaky random-CV comparison, key drivers, the rate-change model, and the top zones by exposure, then writes `zones.json` and `metrics.json`. Copy the real numbers, including unflattering ones, into your README.

Preview locally:
```
cp zones.json metrics.json vercel-site/public/
cd vercel-site/public && python3 -m http.server 8000     # open http://localhost:8000
```
Those two files in `vercel-site/public/` are exactly what gets deployed. Hold off committing until you're happy with the results (step 5 below does it).

---
## 5. Put the project on GitHub
1. Create an empty repo on github.com (e.g. `seismic-risk`), **public** if you want it on your resume.
2. From inside the `quake` folder (so `schema.sql`, `train.py` and `vercel-site/` sit at the repo root):
```
git init && git add . && git commit -m "Seismic risk pipeline"
git branch -M main
git remote add origin https://github.com/<you>/seismic-risk.git
git push -u origin main
```
3. Before pushing, run `git status` and confirm no passwords, `.env` files or connection strings are included. `DATABASE_URL` lives only in your terminal and in GitHub Secrets (step 7), never in files.

---
## 6. Deploy to Vercel
1. vercel.com -> sign up with GitHub -> **Add New -> Project** -> import `seismic-risk`.
2. Settings: **Framework Preset: Other**, **Root Directory: `vercel-site`**, build command empty, **output directory `public`**. Deploy.
3. You get `https://<project-name>.vercel.app` (rename under Project -> Settings -> Domains if you like).
4. Open it. If `vercel-site/public/zones.json` was committed, the panel says "N zones from the live model"; otherwise it shows the illustrative sample zones.

Vercel redeploys automatically whenever you push to `main`.

(CLI alternative: `npm i -g vercel && cd vercel-site && vercel login && vercel --prod`.)

---
## 7. Weekly auto-refresh with GitHub Actions
The workflow `.github/workflows/refresh.yml` pulls new earthquakes into Neon, retrains, commits the new `zones.json`, and Vercel redeploys.

1. GitHub repo -> **Settings -> Secrets and variables -> Actions -> New repository secret**: name `DATABASE_URL`, value = your Neon connection string.
2. **Settings -> Actions -> General -> Workflow permissions**: choose **Read and write permissions**.
3. Test it: **Actions** tab -> *refresh-data* -> **Run workflow**. Within a few minutes you should see a bot commit "Update zones ..." and a new Vercel deployment.
4. It then runs every Monday 06:00 UTC (edit the cron line to change this).

Notes: GitHub may pause scheduled workflows on repos with no activity for ~60 days (re-enable in the Actions tab); the bot commits normally count as activity. Runs use a small slice of the free Actions minutes.

---
## 8. Finish for your resume
- README: add the live URL, a screenshot, the baseline table, the random-vs-spatial CV result, and link `LIMITATIONS.md`.
- One-line architecture: USGS -> PostGIS (Neon) -> scikit-learn -> GitHub Action -> Vercel globe.

## 9. Security and cleanup
- If your connection string ever leaks (commit, screenshot), reset the password in Neon (Roles -> reset) and update the GitHub secret.
- To stop everything: delete the Vercel project, the Neon project, and the GitHub repo/Actions.

## Troubleshooting
| symptom | likely cause |
|---|---|
| `could not connect` / timeout | wrong `DATABASE_URL`, or you opened a new terminal and the `export` is gone |
| `permission denied to create extension` | connect with the project's owner role (the default one Neon gives you) |
| `ingest.py` "API cap hit" | a window returned 20k rows; shorten the 183-day chunk in `ingest_range` |
| Empty distance/population columns | `load_plates.py` / `load_cities.py` not run |
| Database full | check size (step 3); upgrade plan or trim data |
| Vercel shows sample data | no `zones.json` in `vercel-site/public/` on `main` yet, or Root Directory not set to `vercel-site` |
| Action fails on `git push` | workflow permissions not set to Read and write (step 7.2) |
| Action fails connecting to DB | secret name must be exactly `DATABASE_URL` |
