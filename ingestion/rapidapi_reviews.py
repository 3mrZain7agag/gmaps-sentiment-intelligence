"""
ingestion/rapidapi_reviews.py

Pull Google reviews (RapidAPI Local Business Data) for the places in
raw.review_sample_plan. Raw JSON is stored untouched in raw.reviews_raw.

Credits are charged per RETURNED result, so:
  search  -> limit=1  (1 credit)
  reviews -> limit=10 (10 credits)

Usage:
  python ingestion/rapidapi_reviews.py --phase pilot --dry-run
  python ingestion/rapidapi_reviews.py --phase pilot
  python ingestion/rapidapi_reviews.py --phase main --per-area 8 --max-credits 430

Env (.env, never in git): RAPIDAPI_KEY, POSTGRES_HOST, POSTGRES_PORT,
  POSTGRES_DB, POSTGRES_USER, POSTGRES_PASSWORD
"""
import argparse
import json
import math
import os
import sys
import time

import psycopg2
import psycopg2.extras
import requests
from dotenv import load_dotenv

load_dotenv()

HOST = "local-business-data.p.rapidapi.com"
BASE = f"https://{HOST}"
HEADERS = {"x-rapidapi-key": os.environ.get("RAPIDAPI_KEY", ""), "x-rapidapi-host": HOST}

REVIEWS_PER_PLACE = 10
MAX_MATCH_DISTANCE_M = 300  # reject a search hit farther than this from the OSM point
REVIEWS_ENDPOINT = "business-reviews-v2"  # path taken from the RapidAPI Playground code snippet

# Exclude author data (reviewer names / profiles are not stored). Adjust to the
# field names you used in the test call.
# Verified on a real response: reviews are NOT translated (translate_reviews=false), so review_text is the
# original text and review_language its language (review_text_translated holds the English version).
# Empty string = parameter not sent.
REVIEW_FIELDS = ""  # the API rejects our field list ("Invalid fields", HTTP 400); author data is removed by scrub_authors instead
REVIEWS_LANGUAGE = ""

# Names too generic to match a real Google place (they only waste a search credit).
GENERIC_NAMES = {
    "caf", "cafe", "café", "coffee", "coffee bar", "coffee & tea", "restaurant", "restaurants area",
    "food court", "cafeteria", "قهوه", "قهوة", "كافيه", "مطعم",
}
GENERIC_SUBSTR = ("vape", "جنب")


def is_generic(name):
    n = (name or "").strip().lower().rstrip(".")
    return len(n) < 3 or n in GENERIC_NAMES or any(x in n for x in GENERIC_SUBSTR)


def haversine_m(lat1, lon1, lat2, lon2):
    r = 6371000
    p1, p2 = math.radians(lat1), math.radians(lat2)
    dp, dl = p2 - p1, math.radians(lon2 - lon1)
    a = math.sin(dp / 2) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(dl / 2) ** 2
    return 2 * r * math.asin(math.sqrt(a))


def call(endpoint, params):
    resp = requests.get(f"{BASE}/{endpoint}", headers=HEADERS, params=params, timeout=60)
    if not resp.ok:
        raise RuntimeError(f"HTTP {resp.status_code} on /{endpoint}: {resp.text[:300]}")
    return resp.json()


def scrub_authors(obj):
    """Drop any key that identifies the reviewer (author_*, reviewer_*), recursively."""
    if isinstance(obj, dict):
        return {k: scrub_authors(v) for k, v in obj.items()
                if not k.lower().startswith(("author", "reviewer"))}
    if isinstance(obj, list):
        return [scrub_authors(v) for v in obj]
    return obj


def log_response(cur, place_id, endpoint, payload):
    """Store the untouched API response in raw.reviews_raw."""
    cur.execute(
        "INSERT INTO raw.reviews_raw (source, source_ref, payload) VALUES (%s, %s, %s)",
        (f"rapidapi_local_business_data:{endpoint}", str(place_id), json.dumps(payload)),
    )


def finish(cur, place_id, status, google_status=None, credits=0):
    cur.execute(
        "UPDATE raw.review_sample_plan "
        "SET status=%s, google_status=%s, credits_spent=credits_spent+%s, processed_at=now() "
        "WHERE place_id=%s",
        (status, google_status, credits, place_id),
    )


def process_place(cur, row):
    pid = row["place_id"]
    name = row["name_en"] or row["name"]
    area = row["area_name"].split("/")[0].strip()  # "New Cairo / Fifth Settlement" -> "New Cairo"
    spent = 0

    # 1) Search by name + area, biased to the OSM coordinates (limit=1 -> 1 credit)
    sp = {"query": f"{name} {area}", "limit": 1, "lat": row["lat"], "lng": row["lon"],
          "zoom": 17, "region": "eg", "language": "en"}
    found = call("search", sp)
    hits = found.get("data") or []
    spent += len(hits)
    log_response(cur, pid, "search", found)
    cur.execute("UPDATE raw.review_sample_plan SET credits_spent = credits_spent + %s WHERE place_id=%s",
                (len(hits), pid))
    cur.connection.commit()  # keep the search response + its credits even if the reviews call fails

    if not hits:
        finish(cur, pid, "not_found", credits=0)
        return spent, "not_found"

    hit = hits[0]
    dist = haversine_m(row["lat"], row["lon"], hit.get("latitude", 0), hit.get("longitude", 0))
    if dist > MAX_MATCH_DISTANCE_M:
        finish(cur, pid, "not_found", hit.get("business_status"), 0)
        return spent, f"not_found (match {dist:.0f} m away)"

    gstatus = hit.get("business_status")
    cur.execute("UPDATE core.places_dim SET rapidapi_id=%s WHERE place_id=%s",
                (hit.get("business_id"), pid))
    cur.connection.commit()

    if gstatus and gstatus.startswith("CLOSED"):
        finish(cur, pid, "closed", gstatus, 0)
        return spent, f"closed ({gstatus})"

    # 2) Newest reviews, author data excluded (limit=10 -> 10 credits)
    rp = {"business_id": hit["business_id"], "limit": REVIEWS_PER_PLACE,
          "sort_by": "newest", "region": "eg"}
    if REVIEWS_LANGUAGE:
        rp["language"] = REVIEWS_LANGUAGE
    if REVIEW_FIELDS:
        rp["fields"] = REVIEW_FIELDS
    revs = call(REVIEWS_ENDPOINT, rp)
    data = revs.get("data") or {}
    reviews = data.get("reviews", []) if isinstance(data, dict) else data
    n = len(reviews)  # credits are charged per returned review
    spent += n
    log_response(cur, pid, "business-reviews", scrub_authors(revs))
    finish(cur, pid, "done", gstatus, n)
    return spent, f"done ({n} reviews)"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--phase", choices=["pilot", "main"], required=True)
    ap.add_argument("--max-credits", type=int, default=440)
    ap.add_argument("--per-area", type=int, default=8,
                    help="stop spending on an area once it has this many places with status done")
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()

    if not HEADERS["x-rapidapi-key"]:
        sys.exit("Set RAPIDAPI_KEY in .env")
    missing = [k for k in ("POSTGRES_HOST", "POSTGRES_DB", "POSTGRES_USER", "POSTGRES_PASSWORD")
               if not os.environ.get(k)]
    if missing:
        sys.exit(f"Missing in .env: {', '.join(missing)}")

    # Keyword args (no URL) so special characters in the password are safe.
    conn = psycopg2.connect(
        host=os.environ["POSTGRES_HOST"],
        port=os.environ.get("POSTGRES_PORT", "5432"),
        dbname=os.environ["POSTGRES_DB"],
        user=os.environ["POSTGRES_USER"],
        password=os.environ["POSTGRES_PASSWORD"],
        sslmode="require",
    )
    conn.autocommit = False
    cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)

    cur.execute(
        """
        SELECT s.place_id, s.area_id, p.name, p.name_en, p.lat, p.lon, a.name_en AS area_name
        FROM raw.review_sample_plan s
        JOIN core.places_dim p USING (place_id)
        JOIN core.dim_areas  a ON a.area_id = s.area_id
        WHERE s.phase = %s AND s.status = 'pending'
        ORDER BY s.pick_order, s.area_id  -- round-robin: all areas advance together
        """,
        (args.phase,),
    )
    rows = cur.fetchall()
    worst_case = len(rows) * (1 + REVIEWS_PER_PLACE)
    print(f"{len(rows)} pending places in phase '{args.phase}' | worst case {worst_case} credits")

    if args.dry_run:
        for r in rows:
            nm = r['name_en'] or r['name']
            flag = "  [skip: generic name]" if is_generic(nm) else ""
            print(f"  would query: {nm} | {r['area_name']}{flag}")
        return

    total = 0
    for r in rows:
        cur.execute("SELECT count(*) AS n FROM raw.review_sample_plan WHERE area_id=%s AND status='done'",
                    (r["area_id"],))
        if cur.fetchone()["n"] >= args.per_area:
            continue  # this area already has enough places with reviews
        nm = r["name_en"] or r["name"]
        if is_generic(nm):
            cur.execute("UPDATE raw.review_sample_plan SET status='skipped', processed_at=now() "
                        "WHERE place_id=%s", (r["place_id"],))
            conn.commit()
            print(f"  {nm}: skipped (generic name) | credits 0")
            continue
        if total + 1 + REVIEWS_PER_PLACE > args.max_credits:
            print(f"Stopping: next place could exceed --max-credits ({args.max_credits}).")
            break
        try:
            spent, msg = process_place(cur, r)
            conn.commit()
        except Exception as e:  # keep going; the place stays retryable
            conn.rollback()
            cur.execute("UPDATE raw.review_sample_plan SET status='error' WHERE place_id=%s",
                        (r["place_id"],))
            cur.execute("SELECT credits_spent FROM raw.review_sample_plan WHERE place_id=%s",
                        (r["place_id"],))
            total += cur.fetchone()["credits_spent"]
            conn.commit()
            print(f"  ERROR {r['place_id']}: {e}")
            continue
        total += spent
        print(f"  {r['name_en'] or r['name']}: {msg} | credits {spent} | total {total}")
        time.sleep(1)  # be gentle with the API

    print(f"Finished. Credits spent this run: {total}")


if __name__ == "__main__":
    main()