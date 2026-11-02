-- Yield level and daily-change volatility by calendar year
SELECT substr(date,1,4) AS year,
       round(AVG(y10),2) AS avg_y10, round(MIN(y10),2) AS min_y10, round(MAX(y10),2) AS max_y10,
       round(MAX(y10)-MIN(y10),2) AS range_y10_pct,
       COUNT(dy10_bp) AS n_changes,
       round(sqrt(AVG(dy10_bp*dy10_bp) - AVG(dy10_bp)*AVG(dy10_bp)),2) AS stdev_dy10_bp
FROM yield_changes GROUP BY 1 ORDER BY 1;
