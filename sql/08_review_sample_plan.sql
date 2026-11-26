-- Review sample plan: which places we pull reviews for from RapidAPI (Nov 26).
-- Structure matches the live Supabase table. The selection itself (8 places per
-- area, spread over distinct H3 cells, 1 pilot per area) was done once and is
-- stored in this table's rows, not in this file.
CREATE TABLE IF NOT EXISTS raw.review_sample_plan (
    place_id       BIGINT       PRIMARY KEY,
    area_id        INTEGER      NOT NULL,
    h3_index       TEXT         NOT NULL,
    pick_order     INTEGER      NOT NULL,                  -- order of attempts inside the area
    phase          TEXT         NOT NULL,                  -- pilot / main
    status         TEXT         NOT NULL DEFAULT 'pending',
    google_status  TEXT,                                   -- e.g. OPERATIONAL / CLOSED_PERMANENTLY
    credits_spent  INTEGER      NOT NULL DEFAULT 0,        -- RapidAPI credits used for this place
    selected_at    TIMESTAMPTZ  NOT NULL DEFAULT now(),
    processed_at   TIMESTAMPTZ
);
