-- Load core.places_dim from raw.osm_places_raw.
--
-- * Uses the latest pull per OSM element (raw keeps one set of rows per day).
-- * Nodes carry lat/lon directly; ways and relations carry them in "center".
-- * Idempotent: safe to re-run (upsert on osm_type + osm_id).
-- * Does not touch h3_index or rapidapi_id; those are filled by later steps.
-- * Lives in sql/transforms/ on purpose: Docker only auto-runs the top-level files
--   in sql/ on first start, so this one is run manually.
--
-- Run:
--   docker compose exec -T db psql -U de_admin -d gmaps < sql/transforms/10_load_places_dim.sql

INSERT INTO core.places_dim
    (osm_type, osm_id, name, name_ar, name_en, category, lat, lon, geom, area_id)
SELECT
    t.osm_type,
    t.osm_id,
    t.name,
    t.name_ar,
    t.name_en,
    t.category,
    t.lat,
    t.lon,
    ST_SetSRID(ST_MakePoint(t.lon, t.lat), 4326),
    a.area_id
FROM (
    SELECT DISTINCT ON (payload->>'type', payload->>'id')
        payload->>'type'                                   AS osm_type,
        (payload->>'id')::bigint                           AS osm_id,
        NULLIF(btrim(payload->'tags'->>'name'), '')        AS name,
        NULLIF(btrim(payload->'tags'->>'name:ar'), '')     AS name_ar,
        NULLIF(btrim(payload->'tags'->>'name:en'), '')     AS name_en,
        payload->'tags'->>'amenity'                        AS category,
        COALESCE((payload->>'lat')::float8, (payload->'center'->>'lat')::float8) AS lat,
        COALESCE((payload->>'lon')::float8, (payload->'center'->>'lon')::float8) AS lon,
        area_code
    FROM raw.osm_places_raw
    ORDER BY payload->>'type', payload->>'id', fetched_at DESC
) t
JOIN core.dim_areas a ON a.area_code = t.area_code
WHERE t.lat IS NOT NULL
  AND t.lon IS NOT NULL
  AND t.category IN ('cafe', 'restaurant')
ON CONFLICT (osm_type, osm_id) DO UPDATE SET
    name     = EXCLUDED.name,
    name_ar  = EXCLUDED.name_ar,
    name_en  = EXCLUDED.name_en,
    category = EXCLUDED.category,
    lat      = EXCLUDED.lat,
    lon      = EXCLUDED.lon,
    geom     = EXCLUDED.geom,
    area_id  = EXCLUDED.area_id;
