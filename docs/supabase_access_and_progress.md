# Shared Database: Progress (Nov 25-26) and How to Use It

Project: **Google Maps Places & Sentiment Intelligence** (Cairo cafés and restaurants)
Owner: Hagag Amr (DE / team leader)

> Passwords are **never** stored in this repo. Each team member receives their own role password privately.

---

## 1. What was done

### Nov 25
- Shared PostgreSQL + PostGIS database created on Supabase (project `gmaps-sentiment`, region `eu-west-1`), with the `schema-v1` tables.
- OpenStreetMap places for the 5 areas loaded: **486 places** (Maadi 180, Nasr City 151, Zamalek 80, New Cairo 52, Sheikh Zayed 23).
- H3 grid (resolution 8) built: **385 cells**; every place is linked to its cell.
- RapidAPI (Local Business Data) tested. Credits are charged **per returned result**, not per call.

### Nov 26
- Review sample selected: **40 places, 8 per area**, spread over different H3 cells (`raw.review_sample_plan`).
- Places matched on Google by name + coordinates (matches farther than 300 m rejected, closed places skipped).
- Reviews pulled (newest first, up to 10 per place) and loaded:
  - **391 reviews** in total, **176 with text** (the other 212 are star-rating only).
  - Text is the **original** text (Arabic, English, ...). Google's English translation is kept separately in `review_text_en`.
  - Reviewer identity (name, profile link, id) is **not stored**.
- Reviews flattened and loaded into `core.reviews_fact`.

### Schema change (additive, nothing removed)
`core.reviews_fact` got two nullable columns: `api_review_id` (unique, used to avoid duplicates) and `review_text_en`.

---

## 2. Where the data lives

| Object | What it holds |
|---|---|
| `core.dim_areas` | The 5 areas (`area_id`, `area_code`, `name_en`, `name_ar`, `bbox`) |
| `core.places_dim` | One row per place: name, category, `lat`/`lon`, `geom`, `area_id`, `h3_index`, `rapidapi_id` |
| `core.dim_h3_cells` | One row per H3 cell with the metrics columns (density, demand, CSI, MOS, cluster) |
| `core.reviews_fact` | One row per review (see columns below) |
| `core.fact_place_snapshots` | Rating and review count per place per snapshot date |
| `staging.v_reviews_flat` | Read-only view: reviews flattened from the raw API JSON, de-duplicated |
| `raw.*` | Untouched source data (OSM and API responses). Data engineering only |

Key columns in `core.reviews_fact`: `review_id`, `place_id`, `review_date`, `rating`, `review_text`, `language`, `review_text_en`, `sentiment_label`, `sentiment_score`, `topic`, `is_gold`, `gold_label`, `api_review_id`.

Join path: `reviews_fact.place_id` → `places_dim.place_id` → `places_dim.area_id` → `dim_areas.area_id` (and `places_dim.h3_index` → `dim_h3_cells.h3_index`).

---

## 3. How to connect

| Setting | Value |
|---|---|
| Host | the Supabase pooler host (same as `POSTGRES_HOST` in the team `.env.example`) |
| Port | `5432` |
| Database | `postgres` |
| SSL | required (`sslmode=require`) |
| User (DA) | `da_reader.xdhhzfrujoudaleuklxr` |
| User (DS) | `ds_user.xdhhzfrujoudaleuklxr` |
| Password | sent privately by the team leader |

`xdhhzfrujoudaleuklxr` is the Supabase project reference (the same suffix used in `POSTGRES_USER` in the `.env.example`). The pooler requires the user in the form `role.project_ref`.

Python example (credentials from your own local `.env`, never hard-coded):

```python
import os, psycopg2
from dotenv import load_dotenv

load_dotenv()
conn = psycopg2.connect(
    host=os.environ["POSTGRES_HOST"],
    port=os.environ.get("POSTGRES_PORT", "5432"),
    dbname=os.environ["POSTGRES_DB"],
    user=os.environ["POSTGRES_USER"],       # da_reader.xdhhzfrujoudaleuklxr  or  ds_user.xdhhzfrujoudaleuklxr
    password=os.environ["POSTGRES_PASSWORD"],
    sslmode="require",
)
```

Any SQL client (DBeaver, pgAdmin, Supabase SQL editor with your role) or Power BI / Streamlit can use the same settings.

---

## 4. Permissions

| Role | Can do |
|---|---|
| `da_reader` | Read `core.*` and `staging.v_reviews_flat`. Read-only |
| `ds_user` | Read the same objects, and **update only** `sentiment_label`, `sentiment_score`, `topic` in `core.reviews_fact` |
| Team leader | Owns the pipeline, the schema and the raw layer. Loads Gold Set labels (`is_gold`, `gold_label`) |

Any change to formulas or to the schema is discussed with the team before it is applied.

---

## 5. Example queries

Reviews with text per area and language:

```sql
SELECT a.name_en AS area, r.language, count(*) AS reviews
FROM core.reviews_fact r
JOIN core.places_dim  p USING (place_id)
JOIN core.dim_areas   a ON a.area_id = p.area_id
WHERE r.review_text IS NOT NULL
GROUP BY 1, 2
ORDER BY 1, 3 DESC;
```

Reviews waiting for sentiment (DS):

```sql
SELECT review_id, language, review_text
FROM core.reviews_fact
WHERE review_text IS NOT NULL AND sentiment_label IS NULL;
```

Writing model output (DS), one review at a time or in batches:

```sql
UPDATE core.reviews_fact
SET sentiment_label = 'negative', sentiment_score = -0.82, topic = 'wait_time'
WHERE review_id = 123;
```

Allowed `sentiment_label` values: `positive`, `neutral`, `negative`. Topic names are agreed in the first NLP meeting.

---

## 6. Things to know before analysing

- **Only 176 of 391 reviews have text.** Rating-only reviews still count for average rating (CSI) and for activity, but not for sentiment.
- **Sample, not the whole market:** 40 places out of 486. Most H3 cells have no sampled reviews, so results are indicators, not absolute truth.
- **Language detection is Google's.** Reviews labelled `en` may include Arabic written in Latin letters (Franco); the Gold Set must check this.
- **Demand needs care:** the sample holds at most the 10 newest reviews per place, so "reviews in the last 90 days" is almost always 10. A review-velocity measure (days between the newest and the 10th newest review) is proposed and will be discussed with the team.
- **OpenStreetMap coverage in Egypt can be incomplete**, so competition may be under-counted.
- **Attribution:** the dashboard and the final slides must credit "© OpenStreetMap contributors".
- Reviewer names and profiles are not stored and must not be added.

---

## 7. Next steps

1. DS: first sentiment experiments on the 176 text reviews.
2. Team meeting: Gold Set size, Demand formula change, topic names.
3. After the monthly API credits reset: pull additional review pages for places with many reviews.
4. DA: first dashboard version on top of `core.*`.
