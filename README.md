# Google Maps Places & Sentiment Intelligence

A data platform that answers one question: **where is the best place to open a new café or restaurant in Cairo?**

We combine place data from OpenStreetMap with the sentiment of customer reviews (Arabic dialects, Franco-Arabic, and English), turn both into an **opportunity score for every small map cell**, and show the result on an interactive dashboard.

---

## The Problem

Many business owners, investors, and expanding chains choose a new branch location based on intuition or surface-level information. They either open in a saturated area full of competitors, or miss a promising area with real demand and little competition.

At the same time, customer complaints about competitors (waiting time, prices, quality, crowding) are buried inside thousands of reviews in mixed dialects, and nobody uses them. This project turns that data into a clear, number-based decision.

## The Idea

An **opportunity area** is one where three things come together:

1. **High demand**: many recent reviews.
2. **Low competition**: few places relative to the area size.
3. **Low satisfaction**: weak ratings and negative sentiment about the existing places.

To keep the analysis precise, we split the map into small hexagonal cells using **Uber H3** (instead of only 5 large districts) and compute a **Market Opportunity Score (MOS)** for each cell.

## Scope

| Item | Details |
|---|---|
| Areas (5) | New Cairo / Fifth Settlement, Nasr City, Maadi, Sheikh Zayed, Zamalek |
| Place types | All cafés and restaurants (`amenity=cafe` and `amenity=restaurant` in OpenStreetMap). We do not filter for "Specialty Cafés" due to time constraints; it can be added later as a category on top of the same data. |
| Duration | 4 weeks, ending with a presentation to the supervisor |
| Out of scope | Other categories, other cities, a ready-to-sell commercial product |

## Pipeline

1. **Define the target**: bounding boxes for the 5 areas and the place types.
2. **Ingest**: all places with coordinates from OpenStreetMap (Overpass API, free), and ratings and reviews for a sample of places from RapidAPI.
3. **Load**: raw data is stored as-is, then loaded into the database.
4. **Clean**: unify Arabic and English names, remove duplicates across sources, and map every place to its area and H3 cell.
5. **Analyze (NLP)**: classify each review as positive / neutral / negative and extract complaint reasons.
6. **Compute**: satisfaction, demand, and competition metrics, then MOS and cell classification.
7. **Present**: an interactive dashboard with a map and filters.

We follow an **ELT** approach: load first, then transform inside the database with SQL (and Python where SQL is not a good fit). This lets us adjust the cleaning and re-run without burning API quota.

## Data Sources

| Source | Role and limits |
|---|---|
| OpenStreetMap (Overpass API) | Free; covers all places (name, coordinates, type). This is the foundation. Note: coverage in Egypt may be incomplete, so we measure the coverage rate. |
| RapidAPI: Local Business Data | 500 credits per month. Provides rating, review count, and review text (up to 100 per place). It is the only source of reviews, so it is very limited, which is why we pull a **sample** of places rather than all of them. |
| RapidAPI: TrueWay and Tripadvisor | Secondary sources for enrichment and validation, if time allows. |

## Database

PostgreSQL with the PostGIS extension.

| Table / Component | Purpose |
|---|---|
| `dim_areas`, `dim_h3_cells` | Areas and H3 cells with boundaries and metrics per cell |
| `places_dim` | Static place information (name, type, location) |
| `fact_place_snapshots` | Rating and review count at each refresh date, so we can track change over time |
| `reviews_fact` | Review text, language, rating, sentiment label, and topic |
| Views (e.g. `latest_places_v`) | Ready-made views that simplify work for the analysts and data scientists |

Schemas: `raw` (payloads exactly as fetched, DE only), `staging` (e.g. `v_reviews_flat`, the flattened API reviews), and `core` (clean tables, the contract with the team). Reviewer names and profiles are never stored.

## Analysis

- **Sentiment analysis**: a model (such as the Arabic-specialized MARBERT) classifies every review as positive, neutral, or negative. The challenge is that reviews mix Modern Standard Arabic, dialects, Franco-Arabic, and English.
- **Topic modeling**: applied to negative reviews to extract recurring complaint reasons (service speed, price, crowding, cleanliness, and so on).
- **K-Means clustering**: groups cells into types (saturated / growth / underserved) based on competition, demand, and satisfaction.
- **Gold set**: about 200 reviews labeled manually, used to measure model accuracy (F1 per language).

## Metrics

| Metric | Formula | Meaning |
|---|---|---|
| Competitor Density (D) | places ÷ cell area (km²) | Competitors per square kilometer |
| Demand Score (S_demand) | log10(reviews in last 90 days + 1) | Current activity. The logarithm keeps very large numbers from dominating. |
| Customer Satisfaction Index (CSI) | 0 to 100: average stars (60%) + net sentiment, positive minus negative (40%) | A combined indicator of real customer satisfaction |
| Market Opportunity Score (MOS) | S_demand × (1 − CSI/100) ÷ (1 + D) | Demand increases the opportunity; satisfaction and competition reduce it. A higher MOS means a bigger opportunity. |

> **Important:** MOS is a *relative ranking* between cells, not a guaranteed forecast. It is rescaled to 0–100 on the dashboard to make it easier to read.

## Deliverables

- An interactive dashboard with a hexagon map colored by MOS, plus filters (area, rating, sentiment, and more).
- A ranked list of top opportunity cells, with an explanation of why each one is an opportunity.
- A slide deck covering the idea, results, and potential business model.
- Documentation for the pipeline, the database, and key decisions.

## Success Criteria

- **Level 1 (must):** clean data for the 5 areas, H3 grid, sentiment analysis with measured accuracy (F1 on the gold set), CSI and MOS for every cell, clustering, a dashboard with a map and at least one filter, and a supervisor presentation.
- **Level 2 (should):** topic modeling, more filters and drill-down, an automated weekly refresh with Airflow, and accumulated snapshot history.
- **Level 3 (if time allows):** extra enrichment sources (Tripadvisor / TrueWay), splitting cafés into Specialty and others, and population data.

## Limitations

- **API quota:** reviews come from a sample because of free-tier limits, so results are an indicator, not an absolute truth.
- **OpenStreetMap gaps:** some cafés may not be registered, so competition may be underestimated.
- **Dialects:** models can make mistakes on dialect and Franco-Arabic text, so we measure accuracy and report it.
- **Metric limits:** MOS does not measure population or foot traffic, and unmet demand is not visible in reviews.
- **Time:** 4 weeks, so the focus is on Level 1 first.
- **Legal:** API terms of use and review privacy are noted in the plan and become a priority if the project turns into a commercial product.

## Repository Structure

```
.
├── docs/             # Project documentation and decisions
├── etl/              # Small export jobs (e.g. gold-set sample from the database to CSV)
├── ingestion/        # Scripts that pull data from OpenStreetMap and RapidAPI
├── notebooks/        # Exploration and NLP experiments
├── sql/              # Database schema and transformation queries
├── docker-compose.yml
├── .env.example      # Template for environment variables (never commit real keys)
└── README.md
```

## Getting Started (local database, optional)

```bash
# 1. Clone the repo
git clone https://github.com/3mrZain7agag/gmaps-sentiment-intelligence.git
cd gmaps-sentiment-intelligence

# 2. Create your local environment file and fill in your own keys
cp .env.example .env

# 3. Start the database (PostgreSQL + PostGIS)
docker compose up -d
```

## Connect to the shared database (Supabase)

The team works on one shared PostgreSQL + PostGIS database on Supabase. You get your own **role** and password privately from the team leader; passwords are never committed.

1. `cp .env.example .env`
2. Fill the `POSTGRES_*` values. Use the **Session pooler** details (Supabase dashboard > Connect). The direct connection does not work on the free plan (IPv6 only).
   - `POSTGRES_USER` has the form `<role>.<project-ref>`, for example `da_reader.<project-ref>` (not just `da_reader`).
   - `POSTGRES_PASSWORD` is your role's password.
3. Connect with any client (DBeaver, psql, VS Code, Python):

```python
import os, psycopg2
from dotenv import load_dotenv

load_dotenv()
conn = psycopg2.connect(
    host=os.environ["POSTGRES_HOST"], port=os.environ.get("POSTGRES_PORT", "5432"),
    dbname=os.environ["POSTGRES_DB"], user=os.environ["POSTGRES_USER"],
    password=os.environ["POSTGRES_PASSWORD"], sslmode="require",
)
```

| Role | Who | Access |
|---|---|---|
| `da_reader` | Data Analysts | Read-only on `core.*` and `staging.v_reviews_flat` |
| `ds_user` | Data Scientist | Same as above, plus UPDATE on `core.reviews_fact` and `core.dim_h3_cells` (analysis results only) |

The `raw` schema is not accessible to the team. Never ask for, or use, the project's `postgres` password or the `service_role` key.

### Gold set

The gold set (about 200 manually labeled reviews used to measure sentiment model accuracy) lives in a Google Sheet, outside the database, so it can be edited freely. The sample is exported with `python etl/export_gold_set.py` (read-only, writes to the git-ignored `data/` folder). Review text is never committed to the repo.

## Team Workflow

- A short fixed meeting (15 minutes, twice a week) to track dependencies.
- The database schema is the contract between team members; it is delivered to everyone first, in its final version.
- All code lives on GitHub. **API keys and passwords are never committed.** They go in `.env` only.
- Database accounts use role-based permissions (read-only for analysts by default).
- Any change to formulas or the schema is discussed with the team before implementation.

## Team

| Member | Role | Responsibilities |
|---|---|---|
| Amr Hagag | Team Leader and Data Engineer | Pipeline, database, data quality, and coordination |
| Habiba Amr | Data Scientist | Sentiment analysis, topic modeling, and clustering |
| Rozan Ehab, Ahmed Hazem, Ali Qamar | Data Analysts | Metrics and SQL (D, S_demand, CSI, MOS, quality checks); the dashboard (tool, map, filters); quality and delivery (gold set, documentation, slide deck, presentation) |

## Glossary

| Term | Definition |
|---|---|
| H3 | Uber's system that divides the Earth into small hexagons, each with an ID. We use it as the unit of analysis. |
| PostGIS | A PostgreSQL extension that understands points, polygons, and distances. |
| Overpass API | The OpenStreetMap interface for querying places by conditions (e.g. `amenity=cafe`). |
| Haversine / Jaro-Winkler | Haversine measures the distance between two points; Jaro-Winkler measures the similarity between two names. We use them together to detect duplicate places. |
| Sentiment Analysis / NLP | Processing text and classifying its sentiment. |
| Gold set | Manually labeled reviews used to measure model accuracy. |
| CSI / MOS | Customer Satisfaction Index / Market Opportunity Score. |
| ELT | Load the data first, then transform it inside the database. |

## Attribution

Place data © [OpenStreetMap contributors](https://www.openstreetmap.org/copyright). We do not store review authors' names.