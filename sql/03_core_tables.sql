CREATE TABLE core.dim_areas (
    area_id     SERIAL PRIMARY KEY,
    area_code   TEXT UNIQUE NOT NULL,
    name_en     TEXT NOT NULL,
    name_ar     TEXT NOT NULL,
    bbox        GEOMETRY(Polygon, 4326) NOT NULL
);

CREATE TABLE core.dim_h3_cells (
    h3_index        TEXT PRIMARY KEY,
    resolution      SMALLINT NOT NULL,
    area_id         INT REFERENCES core.dim_areas(area_id),
    geom            GEOMETRY(Polygon, 4326) NOT NULL,
    cell_area_km2   NUMERIC,
    -- المقاييس (بتتملى في الأسبوع 3)
    place_count     INT,
    density         NUMERIC,       -- D
    demand_score    NUMERIC,       -- Sdemand
    csi             NUMERIC,       -- 0..100
    mos             NUMERIC,
    mos_0_100       NUMERIC,
    cluster_label   TEXT,
    metrics_at      TIMESTAMPTZ
);
CREATE INDEX ON core.dim_h3_cells USING GIST (geom);

CREATE TABLE core.places_dim (
    place_id        BIGSERIAL PRIMARY KEY,
    osm_type        TEXT,
    osm_id          BIGINT,
    rapidapi_id     TEXT,
    name            TEXT,
    name_ar         TEXT,
    name_en         TEXT,
    category        TEXT NOT NULL CHECK (category IN ('cafe','restaurant')),
    lat             DOUBLE PRECISION NOT NULL,
    lon             DOUBLE PRECISION NOT NULL,
    geom            GEOMETRY(Point, 4326) NOT NULL,
    area_id         INT REFERENCES core.dim_areas(area_id),
    h3_index        TEXT REFERENCES core.dim_h3_cells(h3_index),
    created_at      TIMESTAMPTZ NOT NULL DEFAULT now(),
    UNIQUE (osm_type, osm_id)
);
CREATE INDEX ON core.places_dim USING GIST (geom);
CREATE INDEX ON core.places_dim (h3_index);

CREATE TABLE core.fact_place_snapshots (
    snapshot_id     BIGSERIAL PRIMARY KEY,
    place_id        BIGINT NOT NULL REFERENCES core.places_dim(place_id),
    snapshot_date   DATE NOT NULL DEFAULT current_date,
    source          TEXT NOT NULL,
    rating          NUMERIC(2,1),
    reviews_count   INT,
    UNIQUE (place_id, snapshot_date, source)
);

-- ملاحظة خصوصية: مفيش عمود لاسم كاتب الريفيو (قرار المشروع)
CREATE TABLE core.reviews_fact (
    review_id       BIGSERIAL PRIMARY KEY,
    place_id        BIGINT NOT NULL REFERENCES core.places_dim(place_id),
    source          TEXT NOT NULL,
    review_date     DATE,
    rating          SMALLINT CHECK (rating BETWEEN 1 AND 5),
    review_text     TEXT,
    language        TEXT,            -- ar_msa / ar_dialect / franco / en
    sentiment_label TEXT CHECK (sentiment_label IN ('positive','neutral','negative')),
    sentiment_score NUMERIC,
    topic           TEXT,
    is_gold         BOOLEAN NOT NULL DEFAULT false,
    gold_label      TEXT CHECK (gold_label IN ('positive','neutral','negative')),
    created_at      TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE INDEX ON core.reviews_fact (place_id, review_date);
