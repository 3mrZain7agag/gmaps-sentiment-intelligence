-- Access model on the shared Supabase database (matches the live grants).
-- Roles da_reader and ds_user already exist on Supabase. Their passwords are set
-- privately and are NEVER stored in this repo, e.g.:
--   CREATE ROLE da_reader LOGIN PASSWORD '<set privately>';
--   CREATE ROLE ds_user   LOGIN PASSWORD '<set privately>';
-- (On the Supabase pooler the login name is <role>.<project-ref>.)

-- raw is intentionally locked: no USAGE for the team (raw payloads stay with the DE).
GRANT USAGE ON SCHEMA core, staging TO da_reader, ds_user;

GRANT SELECT ON core.dim_areas,
                core.dim_h3_cells,
                core.fact_place_snapshots,
                core.latest_places_v,
                core.places_dim,
                core.reviews_fact,
                staging.v_reviews_flat
      TO da_reader, ds_user;

-- DS writes analysis results only (sentiment, topic, H3 metrics, clusters).
GRANT UPDATE ON core.reviews_fact, core.dim_h3_cells TO ds_user;
