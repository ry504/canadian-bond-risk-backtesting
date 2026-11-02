-- Daily yield change in basis points, using the previous available observation (window function).
DROP VIEW IF EXISTS yield_changes;
CREATE VIEW yield_changes AS
SELECT date, y2, y5, y10,
       (y2  - LAG(y2)  OVER (ORDER BY date)) * 100 AS dy2_bp,
       (y5  - LAG(y5)  OVER (ORDER BY date)) * 100 AS dy5_bp,
       (y10 - LAG(y10) OVER (ORDER BY date)) * 100 AS dy10_bp
FROM yields_wide;
