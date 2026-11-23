CREATE TABLE raw.osm_places_raw (
    id          BIGSERIAL PRIMARY KEY,
    area_code   TEXT        NOT NULL,
    fetched_at  TIMESTAMPTZ NOT NULL DEFAULT now(),
    payload     JSONB       NOT NULL          -- one element from the Overpass response
);

CREATE TABLE raw.reviews_raw (
    id          BIGSERIAL PRIMARY KEY,
    source      TEXT        NOT NULL,         -- rapidapi_local_business, ...
    source_ref  TEXT,                         -- business_id at the source
    fetched_at  TIMESTAMPTZ NOT NULL DEFAULT now(),
    payload     JSONB       NOT NULL
);

CREATE INDEX ON raw.osm_places_raw (area_code);
CREATE INDEX ON raw.reviews_raw (source, source_ref);
