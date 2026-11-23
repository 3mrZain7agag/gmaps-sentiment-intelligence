CREATE EXTENSION IF NOT EXISTS postgis;

-- raw: البيانات زي ما جت | staging: وسيط للتنضيف | core: الجداول النضيفة (العقد مع الفريق)
CREATE SCHEMA IF NOT EXISTS raw;
CREATE SCHEMA IF NOT EXISTS staging;
CREATE SCHEMA IF NOT EXISTS core;
