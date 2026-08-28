DROP TABLE IF EXISTS customer_spend_eur;

CREATE TABLE customer_spend_eur AS
SELECT
    customer_id,
    customer_email,
    ROUND(SUM(net_amount_eur), 2) AS total_spend_eur
FROM orders_clean
GROUP BY customer_id, customer_email;
