-- Loads flattened API reviews into core.reviews_fact. Safe to re-run:
-- api_review_id has a unique index, existing reviews are skipped.
-- review_date is the UTC date of the review.
INSERT INTO core.reviews_fact
       (place_id, source, review_date, rating, review_text, language, api_review_id, review_text_en)
SELECT v.place_id,
       'google_maps',                        -- same source value as the rows already loaded
       (v.reviewed_at AT TIME ZONE 'UTC')::date,
       v.rating,
       v.review_text,
       v.review_language,
       v.api_review_id,
       v.review_text_en
FROM staging.v_reviews_flat v
WHERE v.rating BETWEEN 1 AND 5
ON CONFLICT (api_review_id) DO NOTHING;
