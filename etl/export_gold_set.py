#!/usr/bin/env python3
"""
Export a gold-set sample from Supabase (Postgres) to a CSV ready for Google Sheets.

Read-only: it only runs SELECT queries, nothing is written back to the DB.

Usage:
    python export_gold_set.py --inspect          # print columns of the tables used
    python export_gold_set.py                    # export up to 200 reviews -> data/gold_set.csv
    python export_gold_set.py --n 150 --seed 7 --out data/gold_set_v2.csv

Env (.env, never commit it) - same variables the rest of the repo uses:
    POSTGRES_HOST, POSTGRES_PORT, POSTGRES_DB, POSTGRES_USER, POSTGRES_PASSWORD
    (Supabase Session pooler details; a read-only role such as da_reader is enough.
     Optional fallback: DATABASE_URL=postgresql://USER:PASSWORD@HOST:PORT/DB)
"""
import argparse
import csv
import os
import random
import sys
from collections import defaultdict

import psycopg2
from dotenv import load_dotenv

# ---------------------------------------------------------------------------
# Column names match sql/03_core_tables.sql (verified).
# Deliberately NOT selected: author fields, model predictions (so labelers are not biased).
# ---------------------------------------------------------------------------
QUERY = """
SELECT
    r.review_id,
    a.name_en                                   AS area,
    p.name                                      AS place_name,
    r.language                                  AS language,
    r.rating                                    AS rating,
    r.review_date                               AS review_date,
    r.review_text                               AS review_text
FROM core.reviews_fact r
JOIN core.places_dim   p ON p.place_id = r.place_id
JOIN core.dim_areas    a ON a.area_id  = p.area_id
WHERE r.review_text IS NOT NULL
  AND length(btrim(r.review_text)) > 0
"""

INSPECT_TABLES = [("core", "reviews_fact"), ("core", "places_dim"), ("core", "dim_areas")]

# Columns the labelers fill in inside Google Sheets
LABEL_COLUMNS = ["sentiment_label", "complaint_topic", "labeled_by", "notes"]
# sentiment_label values: positive / neutral / negative / unclear


def bucket(lang):
    lang = (lang or "").lower()
    if lang.startswith("ar"):
        return "ar"
    if lang.startswith("en"):
        return "en"
    return "other"


def stratified_sample(rows, n, rng):
    """Take up to n/3 from each language bucket, then fill the rest randomly."""
    if len(rows) <= n:
        return list(rows)
    groups = defaultdict(list)
    for r in rows:
        groups[bucket(r["language"])].append(r)
    for g in groups.values():
        rng.shuffle(g)
    per = n // max(len(groups), 1)
    picked, leftovers = [], []
    for g in groups.values():
        picked += g[:per]
        leftovers += g[per:]
    rng.shuffle(leftovers)
    picked += leftovers[: n - len(picked)]
    return picked


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--n", type=int, default=200, help="target sample size")
    ap.add_argument("--seed", type=int, default=42)
    ap.add_argument("--out", default="data/gold_set.csv")  # data/ is git-ignored
    ap.add_argument("--inspect", action="store_true")
    args = ap.parse_args()

    load_dotenv()
    if os.environ.get("POSTGRES_HOST"):
        conn = psycopg2.connect(
            host=os.environ["POSTGRES_HOST"],
            port=os.environ.get("POSTGRES_PORT", "5432"),
            dbname=os.environ["POSTGRES_DB"],
            user=os.environ["POSTGRES_USER"],
            password=os.environ["POSTGRES_PASSWORD"],
            sslmode="require",
        )
    elif os.environ.get("DATABASE_URL"):
        conn = psycopg2.connect(os.environ["DATABASE_URL"])
    else:
        sys.exit("Set POSTGRES_* (or DATABASE_URL) in .env")
    conn.set_session(readonly=True)
    cur = conn.cursor()

    if args.inspect:
        for schema, table in INSPECT_TABLES:
            cur.execute(
                "SELECT column_name, data_type FROM information_schema.columns "
                "WHERE table_schema=%s AND table_name=%s ORDER BY ordinal_position",
                (schema, table),
            )
            print(f"\n{schema}.{table}")
            for col, typ in cur.fetchall():
                print(f"  {col:<25} {typ}")
        return

    cur.execute(QUERY)
    cols = [d[0] for d in cur.description]
    rows = [dict(zip(cols, rec)) for rec in cur.fetchall()]
    conn.close()

    print(f"Reviews with text available: {len(rows)}")
    rng = random.Random(args.seed)
    sample = stratified_sample(rows, args.n, rng)
    rng.shuffle(sample)

    counts = defaultdict(int)
    for r in sample:
        counts[bucket(r["language"])] += 1
    print(f"Sampled: {len(sample)}  by language bucket: {dict(counts)}")
    if len(rows) < args.n:
        print(f"NOTE: fewer than {args.n} reviews with text exist, exported all of them.")

    os.makedirs(os.path.dirname(args.out) or ".", exist_ok=True)
    fieldnames = ["gold_id"] + cols + LABEL_COLUMNS
    with open(args.out, "w", newline="", encoding="utf-8-sig") as f:
        w = csv.DictWriter(f, fieldnames=fieldnames)
        w.writeheader()
        for i, r in enumerate(sample, 1):
            row = {"gold_id": f"G{i:03d}", **r}
            for c in LABEL_COLUMNS:
                row[c] = ""
            w.writerow(row)
    print(f"Wrote {args.out}")


if __name__ == "__main__":
    main()
