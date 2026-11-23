CREATE TABLE raw.osm_places_raw (
    id          BIGSERIAL PRIMARY KEY,
    area_code   TEXT        NOT NULL,
    fetched_at  TIMESTAMPTZ NOT NULL DEFAULT now(),
    payload     JSONB       NOT NULL          -- عنصر واحد من رد Overpass
);

CREATE TABLE raw.reviews_raw (
    id          BIGSERIAL PRIMARY KEY,
    source      TEXT        NOT NULL,         -- rapidapi_local_business, ...
    source_ref  TEXT,                         -- business_id عند المصدر
    fetched_at  TIMESTAMPTZ NOT NULL DEFAULT now(),
    payload     JSONB       NOT NULL
);

CREATE INDEX ON raw.osm_places_raw (area_code);
CREATE INDEX ON raw.reviews_raw (source, source_ref);
