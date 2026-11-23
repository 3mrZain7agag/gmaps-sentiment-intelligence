-- الإحداثيات تقريبية ومحتاجة مراجعة بصرية (ST_MakeEnvelope: west, south, east, north)
INSERT INTO core.dim_areas (area_code, name_en, name_ar, bbox) VALUES
 ('new_cairo',   'New Cairo / Fifth Settlement', 'التجمع الخامس / القاهرة الجديدة', ST_MakeEnvelope(31.38, 29.98, 31.52, 30.06, 4326)),
 ('nasr_city',   'Nasr City',                    'مدينة نصر',                       ST_MakeEnvelope(31.28, 30.04, 31.38, 30.10, 4326)),
 ('maadi',       'Maadi',                        'المعادي',                         ST_MakeEnvelope(31.20, 29.93, 31.30, 29.99, 4326)),
 ('sheikh_zayed','Sheikh Zayed',                 'الشيخ زايد',                      ST_MakeEnvelope(30.92, 30.00, 31.01, 30.08, 4326)),
 ('zamalek',     'Zamalek',                      'الزمالك',                         ST_MakeEnvelope(31.213, 30.050, 31.230, 30.070, 4326));
