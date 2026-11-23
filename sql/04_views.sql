CREATE VIEW core.latest_places_v AS
SELECT DISTINCT ON (p.place_id)
       p.place_id, p.name, p.category, p.lat, p.lon, p.h3_index, a.name_en AS area,
       s.rating, s.reviews_count, s.snapshot_date
FROM core.places_dim p
LEFT JOIN core.dim_areas a ON a.area_id = p.area_id
LEFT JOIN core.fact_place_snapshots s ON s.place_id = p.place_id
ORDER BY p.place_id, s.snapshot_date DESC NULLS LAST;
