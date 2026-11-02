-- Ten largest absolute daily moves in the 10-year yield (sanity check for data errors)
SELECT date, y10, round(dy10_bp,1) AS dy10_bp FROM yield_changes
WHERE dy10_bp IS NOT NULL ORDER BY abs(dy10_bp) DESC LIMIT 10;
