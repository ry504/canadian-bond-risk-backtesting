-- Row counts, date range, nulls per tenor
SELECT tenor_years, COUNT(*) AS n, MIN(date) AS first_date, MAX(date) AS last_date,
       SUM(yield_pct IS NULL) AS nulls, MIN(yield_pct) AS min_y, MAX(yield_pct) AS max_y
FROM yields_raw GROUP BY tenor_years;

-- Observations per calendar year (full years should be ~250-262 business days)
SELECT substr(date,1,4) AS year, COUNT(DISTINCT date) AS obs_days
FROM yields_raw GROUP BY 1 ORDER BY 1;

-- Duplicate keys (should return no rows)
SELECT date, series_id, COUNT(*) c FROM yields_raw GROUP BY 1,2 HAVING c > 1;
