# Google Maps Places & Sentiment Intelligence

منصة بتحدد أحسن مناطق لفتح كافيه/مطعم جديد في القاهرة (5 مناطق) بناءً على بيانات الأماكن وتحليل مشاعر الريفيوز، مع درجة فرصة (MOS) لكل خلية H3.

## التشغيل
```bash
cp .env.example .env      # عدّل الباسوردات
docker compose up -d
docker exec -it gmaps_db psql -U de_admin -d gmaps -c "SELECT area_code FROM core.dim_areas;"
```
لو غيرت الـ schema بعد أول تشغيل: `docker compose down -v` ثم `up -d` (بيمسح الداتا).

## الهيكل
- `sql/` الـ schema (بيتنفذ تلقائيًا بالترتيب أول مرة)
- `ingestion/` سكريبتات السحب (Overpass, RapidAPI)
- `notebooks/` تجارب الـ NLP والتحليل
- `docs/` التوثيق والقرارات

## قواعد الفريق
- مفيش مفاتيح أو باسوردات في الكود أو الـ commits.
- أي تعديل على الـ schema أو المعادلات يتناقش مع الفريق الأول.
- الـ DA بيستخدم `da_reader` (قراءة فقط).
- ©OpenStreetMap contributors في العرض.
