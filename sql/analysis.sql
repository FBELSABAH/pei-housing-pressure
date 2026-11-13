DROP VIEW IF EXISTS household_scenarios;
DROP VIEW IF EXISTS annual_supply;
DROP VIEW IF EXISTS rental_trends;
CREATE VIEW annual_supply AS
WITH p AS (
 SELECT CAST(SUBSTR(period,1,4) AS INTEGER) AS year,value AS population_jan1,
 LEAD(value) OVER(ORDER BY period) AS next_jan1,
 LEAD(CAST(SUBSTR(period,1,4) AS INTEGER)) OVER(ORDER BY period) AS next_year
 FROM observations WHERE metric='population' AND SUBSTR(period,6,5)='01-01'
), h AS (
 SELECT CAST(period AS INTEGER) AS year,
 MAX(CASE WHEN metric='starts' THEN value END) AS starts,
 MAX(CASE WHEN metric='completions' THEN value END) AS completions
 FROM observations WHERE geo='PEI' AND metric IN ('starts','completions') GROUP BY period
)
SELECT p.year,p.population_jan1,
 CASE WHEN next_year=p.year+1 THEN next_jan1-population_jan1 END AS population_change,
 h.starts,h.completions
FROM p LEFT JOIN h ON p.year=h.year WHERE p.year>=2018 ORDER BY p.year;
CREATE VIEW household_scenarios AS
WITH sizes AS (SELECT 2.0 AS household_size UNION ALL SELECT 2.5 UNION ALL SELECT 3.0)
SELECT a.year,s.household_size,a.population_change,a.completions,
 a.population_change/s.household_size AS illustrative_households,
 a.population_change/s.household_size-a.completions AS illustrative_pressure_balance
FROM annual_supply a CROSS JOIN sizes s
WHERE a.population_change IS NOT NULL AND a.completions IS NOT NULL
ORDER BY a.year,s.household_size;
CREATE VIEW rental_trends AS
WITH rents AS (
 SELECT CAST(period AS INTEGER) AS year,geo,value AS rent_2br,
 LAG(value) OVER(PARTITION BY geo ORDER BY period) AS previous_rent,
 LAG(CAST(period AS INTEGER)) OVER(PARTITION BY geo ORDER BY period) AS previous_year
 FROM observations WHERE metric='rent_2br'
)
SELECT r.year,r.geo,r.rent_2br,
 CASE WHEN r.previous_year=r.year-1 AND r.previous_rent>0 THEN 100.0*(r.rent_2br/r.previous_rent-1) END AS observed_rent_change_pct,
 v.value AS vacancy_pct
FROM rents r LEFT JOIN observations v ON v.metric='vacancy_pct' AND v.geo=r.geo AND v.period=CAST(r.year AS TEXT)
WHERE r.year>=2018 ORDER BY r.geo,r.year;
