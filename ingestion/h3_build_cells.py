"""Build H3 res-8 cells for every area and link each place to its cell."""
import h3
from psycopg2.extras import execute_values
from osm_overpass import connect

RES = 8
conn = connect()
cur = conn.cursor()

cur.execute(
    "SELECT area_id, ST_XMin(bbox), ST_YMin(bbox), ST_XMax(bbox), ST_YMax(bbox) "
    "FROM core.dim_areas ORDER BY area_id"
)
areas = cur.fetchall()
cur.execute("SELECT place_id, area_id, lat, lon FROM core.places_dim")
places = cur.fetchall()

# 1) all cells covering each area's bounding box (empty cells included)
cell_area = {}
for area_id, w, s, e, n in areas:
    poly = h3.LatLngPoly([(s, w), (s, e), (n, e), (n, w)])
    for c in h3.polygon_to_cells(poly, RES):
        cell_area.setdefault(c, area_id)

# 2) the cell of every place (covers places near an area edge)
place_cell = []
for place_id, area_id, lat, lon in places:
    c = h3.latlng_to_cell(lat, lon, RES)
    cell_area.setdefault(c, area_id)
    place_cell.append((c, place_id))


def to_wkt(c):
    ring = [(lng, lat) for lat, lng in h3.cell_to_boundary(c)]
    ring.append(ring[0])
    return "POLYGON((" + ", ".join(f"{x} {y}" for x, y in ring) + "))"


rows = [
    (c, RES, a, to_wkt(c), h3.cell_area(c, unit="km^2"))
    for c, a in cell_area.items()
]
execute_values(
    cur,
    "INSERT INTO core.dim_h3_cells (h3_index, resolution, area_id, geom, cell_area_km2) "
    "VALUES %s ON CONFLICT (h3_index) DO NOTHING",
    rows,
    template="(%s, %s, %s, ST_GeomFromText(%s, 4326), %s)",
)
execute_values(
    cur,
    "UPDATE core.places_dim p SET h3_index = v.h3 "
    "FROM (VALUES %s) AS v(h3, pid) WHERE p.place_id = v.pid",
    place_cell,
)
conn.commit()
print(f"cells: {len(rows)}, places linked: {len(place_cell)}")
