#!/bin/bash
set -e
psql -v ON_ERROR_STOP=1 --username "$POSTGRES_USER" --dbname "$POSTGRES_DB" <<SQL
CREATE ROLE da_reader LOGIN PASSWORD '${DA_PASSWORD}';
CREATE ROLE ds_user   LOGIN PASSWORD '${DS_PASSWORD}';

GRANT USAGE ON SCHEMA core TO da_reader, ds_user;
GRANT SELECT ON ALL TABLES IN SCHEMA core TO da_reader, ds_user;
ALTER DEFAULT PRIVILEGES IN SCHEMA core GRANT SELECT ON TABLES TO da_reader, ds_user;

-- الـ DS بيكتب نتايج التحليل بس
GRANT UPDATE ON core.reviews_fact, core.dim_h3_cells TO ds_user;
SQL
