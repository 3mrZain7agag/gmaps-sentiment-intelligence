"""Compare H3 resolutions 8 and 9 on core.places_dim (read-only)."""
import statistics
from collections import Counter, defaultdict

import h3
from osm_overpass import connect

conn = connect()
cur = conn.cursor()
cur.execute(
    "SELECT a.area_code, p.lat, p.lon "
    "FROM core.places_dim p JOIN core.dim_areas a USING (area_id)"
)
rows = cur.fetchall()

for res in (8, 9):
    cells = defaultdict(list)
    for area, lat, lon in rows:
        cells[h3.latlng_to_cell(lat, lon, res)].append(area)

    sizes = [len(v) for v in cells.values()]
    km2 = h3.cell_area(next(iter(cells)), unit="km^2")
    singles = sum(s == 1 for s in sizes)

    per_area = Counter()
    for v in cells.values():
        per_area[Counter(v).most_common(1)[0][0]] += 1

    print(f"\nresolution {res}: ~{km2:.2f} km2 per cell")
    print(f"  occupied cells : {len(cells)}")
    print(f"  places per cell: mean {statistics.mean(sizes):.1f}, "
          f"median {statistics.median(sizes)}, max {max(sizes)}")
    print(f"  cells with 1 place : {singles} ({100 * singles / len(sizes):.0f}%)")
    print(f"  cells with >=5 places: {sum(s >= 5 for s in sizes)}")
    print(f"  cells per area : {dict(per_area)}")
