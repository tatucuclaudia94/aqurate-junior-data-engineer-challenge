import sqlite3
from pathlib import Path

import pandas as pd

DB_PATH = "aqurate.db"
SQL_DIR = Path("sql")


def refresh_analytical_tables():
    customer_sql = (SQL_DIR / "customer_spend.sql").read_text(encoding="utf-8")
    country_sql = (SQL_DIR / "country_category_revenue.sql").read_text(encoding="utf-8")

    with sqlite3.connect(DB_PATH) as con:
        con.executescript(customer_sql)
        con.executescript(country_sql)

        customer_spend = pd.read_sql_query(
            '''
            SELECT
                customer_id,
                customer_email,
                total_spend_eur
            FROM customer_spend_eur
            ORDER BY total_spend_eur DESC
            ''',
            con,
        )

        country_revenue = pd.read_sql_query(
            '''
            SELECT
                revenue_rank,
                country,
                revenue_eur
            FROM country_category_revenue
            ORDER BY revenue_rank
            ''',
            con,
        )

    customer_spend.to_csv("customer_spend_result.csv", index=False)
    country_revenue.to_csv("country_category_revenue_result.csv", index=False)

    print("=" * 60)
    print("AQURATE - ANALYTICAL TABLE REFRESH")
    print("=" * 60)

    print("\nTop customers by total spend EUR:")
    print(customer_spend.head(15).to_string(index=False))

    print("\nBooks + Electronics combined revenue > 40,000 EUR:")
    if country_revenue.empty:
        print("No countries exceeded 40,000 EUR.")
    else:
        print(country_revenue.to_string(index=False))

    print("\nTables refreshed:")
    print(f"customer_spend_eur: {len(customer_spend)} rows")
    print(f"country_category_revenue: {len(country_revenue)} rows")

    print("\nSaved:")
    print("customer_spend_result.csv")
    print("country_category_revenue_result.csv")


if __name__ == "__main__":
    refresh_analytical_tables()
