-- Wide table of complete days only (all three tenors present). Dates with a missing tenor are dropped, not filled.
DROP VIEW IF EXISTS yields_wide;
CREATE VIEW yields_wide AS
SELECT date,
       MAX(CASE WHEN tenor_years = 2  THEN yield_pct END) AS y2,
       MAX(CASE WHEN tenor_years = 5  THEN yield_pct END) AS y5,
       MAX(CASE WHEN tenor_years = 10 THEN yield_pct END) AS y10
FROM yields_raw
GROUP BY date
HAVING COUNT(yield_pct) = 3
ORDER BY date;
