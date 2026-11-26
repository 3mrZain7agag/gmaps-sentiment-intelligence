-- Additive change to core.reviews_fact (applied on Supabase on Nov 26).
-- Matches the live Supabase schema (types and index name verified).
ALTER TABLE core.reviews_fact ADD COLUMN IF NOT EXISTS api_review_id  TEXT;  -- id from the API, used for dedup
ALTER TABLE core.reviews_fact ADD COLUMN IF NOT EXISTS review_text_en TEXT;  -- Google's English translation (optional)
CREATE UNIQUE INDEX IF NOT EXISTS ux_reviews_fact_api_review_id
    ON core.reviews_fact (api_review_id);
