CREATE EXTENSION IF NOT EXISTS postgis;

-- raw: data as ingested | staging: intermediate cleaning | core: clean tables (the contract with the team)
CREATE SCHEMA IF NOT EXISTS raw;
CREATE SCHEMA IF NOT EXISTS staging;
CREATE SCHEMA IF NOT EXISTS core;
