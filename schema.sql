CREATE EXTENSION IF NOT EXISTS postgis;
CREATE TABLE IF NOT EXISTS earthquakes (
  id         TEXT PRIMARY KEY,              -- source event id
  source     TEXT NOT NULL,                 -- 'usgs', 'ncei', ...
  event_time TIMESTAMPTZ NOT NULL,
  mag        REAL,
  depth_km   REAL,
  geom       GEOGRAPHY(Point,4326) NOT NULL,
  extra      JSONB DEFAULT '{}'::jsonb      -- flexible: mmi, tsunami, felt, place, magType...
);
CREATE INDEX IF NOT EXISTS eq_geom_gist ON earthquakes USING GIST (geom);
CREATE INDEX IF NOT EXISTS eq_time_brin ON earthquakes USING BRIN (event_time);
CREATE INDEX IF NOT EXISTS eq_mag ON earthquakes (mag);
CREATE INDEX IF NOT EXISTS eq_extra_gin ON earthquakes USING GIN (extra);

-- Plate boundaries (Bird 2002, PB2002)
CREATE TABLE IF NOT EXISTS plate_boundaries (
  id    SERIAL PRIMARY KEY,
  name  TEXT,                              -- e.g. 'PA-NA'
  props JSONB DEFAULT '{}'::jsonb,
  geom  GEOGRAPHY(LineString,4326) NOT NULL
);
CREATE INDEX IF NOT EXISTS pb_geom_gist ON plate_boundaries USING GIST (geom);

-- Exposure: GeoNames cities >= 15k people (swap for WorldPop raster zonal stats if you want finer resolution)
CREATE TABLE IF NOT EXISTS cities (
  geonameid BIGINT PRIMARY KEY, name TEXT, pop BIGINT, geom GEOGRAPHY(Point,4326) NOT NULL);
CREATE INDEX IF NOT EXISTS cities_geom_gist ON cities USING GIST (geom);
