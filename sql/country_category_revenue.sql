DROP TABLE IF EXISTS country_category_revenue;

CREATE TABLE country_category_revenue AS
WITH country_revenue AS (
    SELECT
        country,
        ROUND(SUM(net_amount_eur), 2) AS revenue_eur
    FROM orders_clean
    WHERE category IN ('Books', 'Electronics')
    GROUP BY country
),
filtered AS (
    SELECT
        country,
        revenue_eur
    FROM country_revenue
    WHERE revenue_eur > 40000
)
SELECT
    ROW_NUMBER() OVER (ORDER BY revenue_eur DESC) AS revenue_rank,
    country,
    revenue_eur
FROM filtered;
