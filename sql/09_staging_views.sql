-- Flattens raw RapidAPI review responses (raw.reviews_raw) into one row per review.
-- Deduplicated by the API review id, keeping the most recently fetched copy.
-- raw.reviews_raw.source_ref holds core.places_dim.place_id for the review pulls.
-- No reviewer name / profile / id is read here (privacy decision).
CREATE OR REPLACE VIEW staging.v_reviews_flat AS
SELECT DISTINCT ON (r.value ->> 'review_id')
       rr.source_ref::bigint                                        AS place_id,
       r.value ->> 'review_id'                                      AS api_review_id,
       (r.value ->> 'review_datetime_utc')::timestamptz             AS reviewed_at,
       (r.value ->> 'rating')::integer                              AS rating,
       NULLIF(btrim(r.value ->> 'review_text'), '')                 AS review_text,
       r.value ->> 'review_language'                                AS review_language,
       r.value ->> 'review_text_translated'                         AS review_text_en,
       (r.value ->> 'like_count')::integer                          AS like_count,
       r.value -> 'service_quality'                                 AS service_quality,
       rr.fetched_at
FROM raw.reviews_raw rr,
     LATERAL jsonb_array_elements((rr.payload -> 'data') -> 'reviews') AS r(value)
WHERE rr.source LIKE '%business-reviews%'
ORDER BY r.value ->> 'review_id', rr.fetched_at DESC;
