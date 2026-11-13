CREATE TABLE IF NOT EXISTS observations (
 series TEXT NOT NULL, period TEXT NOT NULL, geo TEXT NOT NULL, source_geo TEXT NOT NULL,
 dguide TEXT NOT NULL, metric TEXT NOT NULL CHECK(metric IN ('population','starts','completions','rent_2br','vacancy_pct')),
 value DOUBLE PRECISION CHECK(value >= 0), unit TEXT NOT NULL, status TEXT NOT NULL, source TEXT NOT NULL,
 PRIMARY KEY(series,period), CHECK(metric <> 'vacancy_pct' OR value <= 100)
);
CREATE INDEX IF NOT EXISTS obs_metric_geo ON observations(metric,geo,period);
