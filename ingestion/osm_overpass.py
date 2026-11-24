"""Pull cafes and restaurants from OpenStreetMap (Overpass API) into raw.osm_places_raw.

Each OSM element is stored as one row, exactly as returned by Overpass (JSONB),
together with the area it was pulled for and a fetched_at timestamp.

Idempotent per day: re-running for the same area on the same (UTC) day replaces
that day's rows for the area, so there are no duplicates. Rows from earlier days
are kept, which gives us history across runs.

Usage:
    python ingestion/osm_overpass.py --area maadi
    python ingestion/osm_overpass.py --all
"""
import argparse
import logging
import os
import sys
import time
from collections import Counter

import psycopg2
import requests
from dotenv import load_dotenv
from psycopg2.extras import Json, execute_values

OVERPASS_URLS = [
    "https://overpass-api.de/api/interpreter",
    "https://overpass.kumi.systems/api/interpreter",
]
USER_AGENT = (
    "gmaps-sentiment-intelligence/0.1 "
    "(student project; https://github.com/3mrZain7agag/gmaps-sentiment-intelligence)"
)
PAUSE_BETWEEN_AREAS_SEC = 10
MAX_ATTEMPTS = 3

log = logging.getLogger("osm_overpass")


def connect():
    """Connect with the credentials from .env (never hard-code secrets)."""
    load_dotenv()
    return psycopg2.connect(
        host=os.getenv("POSTGRES_HOST", "localhost"),
        port=os.getenv("POSTGRES_PORT", "5432"),
        dbname=os.environ["POSTGRES_DB"],
        user=os.environ["POSTGRES_USER"],
        password=os.environ["POSTGRES_PASSWORD"],
    )


def get_areas(conn, area_code=None):
    """Read area bounding boxes from core.dim_areas."""
    sql = (
        "SELECT area_code, ST_XMin(bbox), ST_YMin(bbox), ST_XMax(bbox), ST_YMax(bbox) "
        "FROM core.dim_areas"
    )
    params = ()
    if area_code:
        sql += " WHERE area_code = %s"
        params = (area_code,)
    sql += " ORDER BY area_id"
    with conn.cursor() as cur:
        cur.execute(sql, params)
        return cur.fetchall()


def build_query(west, south, east, north):
    # Overpass bbox order is: south, west, north, east
    bbox = f"{south},{west},{north},{east}"
    return (
        "[out:json][timeout:180];"
        f'nwr["amenity"~"^(cafe|restaurant)$"]({bbox});'
        "out center tags;"
    )


def fetch_elements(query):
    """Call Overpass, retrying and falling back to a mirror on failure."""
    last_error = None
    for attempt in range(1, MAX_ATTEMPTS + 1):
        for url in OVERPASS_URLS:
            try:
                resp = requests.post(
                    url,
                    data={"data": query},
                    headers={"User-Agent": USER_AGENT},
                    timeout=240,
                )
                resp.raise_for_status()
                return resp.json()["elements"]
            except (requests.RequestException, ValueError, KeyError) as exc:
                last_error = exc
                log.warning("Attempt %d failed on %s: %s", attempt, url, exc)
        time.sleep(15 * attempt)
    raise RuntimeError(f"Overpass failed after {MAX_ATTEMPTS} attempts: {last_error}")


def load_elements(conn, area_code, elements):
    """Replace today's rows for this area with the fresh pull, in one transaction."""
    with conn:  # commits on success, rolls back on error
        with conn.cursor() as cur:
            cur.execute(
                """
                DELETE FROM raw.osm_places_raw
                WHERE area_code = %s
                  AND (fetched_at AT TIME ZONE 'UTC')::date = (now() AT TIME ZONE 'UTC')::date
                """,
                (area_code,),
            )
            execute_values(
                cur,
                "INSERT INTO raw.osm_places_raw (area_code, payload) VALUES %s",
                [(area_code, Json(e)) for e in elements],
                page_size=500,
            )


def main():
    parser = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--area", help="area_code from core.dim_areas, e.g. maadi")
    group.add_argument("--all", action="store_true", help="pull all areas")
    args = parser.parse_args()

    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")

    conn = connect()
    try:
        areas = get_areas(conn, None if args.all else args.area)
        if not areas:
            sys.exit(f"No area found for '{args.area}'. Check core.dim_areas.")

        for i, (area_code, west, south, east, north) in enumerate(areas):
            if i:
                time.sleep(PAUSE_BETWEEN_AREAS_SEC)  # be polite to the public API
            log.info("Pulling %s ...", area_code)
            elements = fetch_elements(build_query(west, south, east, north))
            if not elements:
                log.warning("%s: Overpass returned 0 elements, keeping existing rows.", area_code)
                continue
            load_elements(conn, area_code, elements)
            by_type = Counter(e.get("tags", {}).get("amenity", "?") for e in elements)
            log.info("%s: loaded %d elements %s", area_code, len(elements), dict(by_type))
    finally:
        conn.close()


if __name__ == "__main__":
    main()
