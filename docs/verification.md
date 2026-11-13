# Verification evidence

- 10 analytical tests passed locally.
- Real PostgreSQL 18 import matched all three reference SQL views.
- Three cached rebuilds: identical output SHA-256; median 0.489 s.
- Dashboard browser checks: rendered SVGs, area selector, household-size selector; source warnings visible.
- One-page PDF rendered and visually inspected.
- Native Tableau format corrected by declaring SheetIdentifierTracking and WindowsPersistSimpleIdentifiers; package reopened and charts rendered in Tableau Public.
- Native workbook uses a bundled Hyper file, not a developer-machine absolute connection.
- Automated GitHub Actions workflow included; local checks are independent of CI outcome.
