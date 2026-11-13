# PEI Housing Pressure Monitor

An official-data analytics project investigating population growth, new housing and urban rental pressure in Prince Edward Island. Python and SQL produce reproducible exports, an interactive dashboard, a native Tableau workbook and a decision brief.

## Findings from the source snapshot

- In 2025, the selected surveyed two-bedroom average rent was **$1,354/month in Charlottetown** and **$1,241 in Summerside**.
- Selected October vacancy rates were **1.7%** and **3.2%**, respectively. These cover privately initiated row/apartment structures of three or more units, not the whole housing stock.
- The selected StatCan completions series ends in **2022**. The monitor prevents a current supply-balance claim instead of substituting starts or treating missing data as zero.

![Dashboard preview](reports/dashboard.png)

[Interactive dashboard](dashboard.html) · [Decision brief](reports/decision_brief.pdf) · [Native Tableau workbook](tableau/PEI_Housing.twbx) · [Quality evidence](reports/data_quality.json)

Open `dashboard.html` locally in a browser; it is self-contained, with year/area controls, household-size scenarios and source provenance. A GitHub file preview does not execute HTML. Download the repository first.

## Questions and decisions

1. How has PEI's population change evolved? January-to-January changes match calendar-year supply flows.
2. How have covered urban rents and vacancy evolved? Provincial and urban figures are displayed separately, never silently merged as identical geography.
3. How sensitive is an illustrative household-equivalent comparison to household size? Historical scenarios use 2.0, 2.5 and 3.0 people per household, and only complete supply years.

The brief identifies where to investigate and what additional evidence is required. No causal population effect, official housing shortage, savings or policy impact is claimed.

## Reproduce

Python 3.12+ recommended (tested locally with 3.14).

```sh
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
python pipeline.py --refresh
python publish.py
python tableau/build.py
python -m unittest discover -s tests -v
```

`--refresh` downloads five full official CSV tables and records retrieval timestamps, checksums and URLs. Without it, the pipeline requires existing raw files and fails if unavailable. No scheduler is installed. For an updated snapshot, run all three build commands above; exporting data alone does not rebuild Tableau or dashboard artifacts.

### PostgreSQL

```sh
cp .env.example .env
# Set your local password in .env, then:
docker compose --env-file .env up -d --wait
export DATABASE_URL='postgresql://housing:YOUR_PASSWORD@localhost:55433/housing'
python pipeline.py --dsn "$DATABASE_URL"
```

The PostgreSQL schema has a `(series, period)` primary key, metric/range constraints and a metric/geography index. Import replaces observations transactionally rather than appending duplicates. All three SQL views are checked against the SQLite reference exports on every PostgreSQL run. Existing views are recreated in the same transaction. Use a dedicated database: this pipeline replaces its `observations` contents.

## Source contract

| Table | Purpose | Selected geography / universe |
|---|---|---|
| 17-10-0009-01 | Population estimates | PEI; January 1 snapshots for annual change; other quarterly observations retained |
| 34-10-0126-01 | Annual housing starts and completions | PEI, total units; no sum across overlapping dwelling categories |
| 34-10-0133-01 | Average observed two-bedroom rent | Charlottetown/Summerside survey areas; row/apartment structures 3+ units |
| 34-10-0131-01 | Vacancy rate | Charlottetown; row/apartment structures 3+ units, all covered unit sizes |
| 34-10-0132-01 | Vacancy rate | Summerside; same structural definition, all covered unit sizes |

[Source manifest](data/raw/manifest.json) records exact source pages, download URLs and SHA-256 hashes. Statistics Canada publishes the tables; housing/rental figures originate from CMHC. Data attribution: Statistics Canada and CMHC; reuse subject to their respective terms. This project is not endorsed by either organization. Code license is separate from data rights.

## Methodology and limitations

- Population change for year Y = January 1 of Y+1 minus January 1 of Y; absent next-year population means NULL. No annualization of partial years.
- Annual housing starts are construction commencements, not completed dwellings or net additions to stock.
- `illustrative_pressure_balance = population_change / household_size - completions`. This is a sensitivity calculation, not household formation or measured need. No scenario is emitted after the completions coverage ends.
- Rental geography is the publisher's survey area, not the city boundary. Source geographic labels, DGUID vintage and vector IDs are retained. Historical boundary/composition changes may affect comparisons; this release does not certify boundary stability. No rural or province-wide rent is inferred.
- Average rent changes can reflect sample/composition changes and are not fixed-sample inflation or asking rents. The 2022 Charlottetown average decline is retained, not smoothed away.
- Vacancy and rent share the selected structural universe but differ in bedroom coverage. Vacancy is all covered units; rent is two-bedroom.
- Official unavailable/suppressed values stay NULL. Duplicate selected keys or invalid value ranges fail the run. Out-of-scope records are filtered, not called errors.
- Estimates may be revised. Identical source snapshots should produce identical analytical hashes; refreshed data can legitimately change findings.

## Validation and measured performance

The corrected native Tableau package was opened in Tableau Public on the development Mac and rendered its four sheets after fixing the workbook format manifest. The browser dashboard area and household-size controls were also exercised.

Ten tests cover calendar alignment, duplicate rejection, Ontario look-alike geography exclusion, missing-value propagation, scenario arithmetic, and repeatability. A real local PostgreSQL run matched all three analytical views exactly; evidence is in `reports/run.json` and `reports/data_quality.json`.

Three cached-source rebuilds returned identical analytical hashes with a **0.489-second median** on the development Mac. Timing covers normalization, SQL and CSV exports only; excludes network, PDF, plotting and Tableau generation. This is processing performance, not measured time saved by an employer.

## Repository map

- `pipeline.py`: retrieval, normalization, quality checks, transactional loads, export and parity checks.
- `sql/`: constrained warehouse table and CTE/window-function analytical views.
- `data/processed/`: reviewed CSV outputs; raw downloads and local databases are excluded from Git.
- `publish.py`: local interactive dashboard, static preview, quality report and one-page PDF.
- `tableau/`: packaged native workbook, Hyper extract, CSV and reproducible builder.
- `tests/`: meaningful analytical/regression checks.

## Next evidence to add

Reconcile an updated direct CMHC provincial completions series before extending the supply comparison beyond 2022. That is an intentional published limitation, not a hidden substitute. Add household formation, demolitions/conversions and housing stock before attempting any unmet-need estimate. Seek feedback from a local planning or research team; no stakeholder adoption is claimed.
