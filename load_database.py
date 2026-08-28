from pathlib import Path
import sqlite3
import pandas as pd
from database import fetch_orders_raw

DB_FILE = Path("aqurate.db")
CLEAN_FILE = Path("orders_clean_fx_preview.csv")


def load_database():
    if not CLEAN_FILE.exists():
        raise FileNotFoundError(
            "orders_clean_fx_preview.csv nu exista."
        )

    print("=" * 60)
    print("AQURATE - SQL DATABASE LOAD")
    print("=" * 60)

    raw = pd.DataFrame(fetch_orders_raw())
    clean = pd.read_csv(CLEAN_FILE)

    fx_rates = (
        clean.loc[
            clean["currency"].eq("RON"),
            ["fx_reference_date", "fx_rate_to_eur"]
        ]
        .drop_duplicates()
        .sort_values("fx_reference_date")
        .rename(columns={
            "fx_rate_to_eur": "rate_to_eur"
        })
        .reset_index(drop=True)
    )

    fx_rates["base_currency"] = "RON"
    fx_rates["quote_currency"] = "EUR"
    fx_rates["provider"] = "BNR via Frankfurter"

    with sqlite3.connect(DB_FILE) as conn:
        raw.to_sql(
            "orders_raw",
            conn,
            if_exists="replace",
            index=False
        )

        clean.to_sql(
            "orders_clean",
            conn,
            if_exists="replace",
            index=False
        )

        fx_rates.to_sql(
            "fx_rates",
            conn,
            if_exists="replace",
            index=False
        )

        conn.execute(
            "CREATE INDEX IF NOT EXISTS "
            "idx_orders_clean_customer "
            "ON orders_clean(customer_id)"
        )

        conn.execute(
            "CREATE INDEX IF NOT EXISTS "
            "idx_orders_clean_order "
            "ON orders_clean(order_id)"
        )

        conn.execute(
            "CREATE INDEX IF NOT EXISTS "
            "idx_orders_clean_country_category "
            "ON orders_clean(country, category)"
        )

        conn.commit()

        raw_count = conn.execute(
            "SELECT COUNT(*) FROM orders_raw"
        ).fetchone()[0]

        clean_count = conn.execute(
            "SELECT COUNT(*) FROM orders_clean"
        ).fetchone()[0]

        fx_count = conn.execute(
            "SELECT COUNT(*) FROM fx_rates"
        ).fetchone()[0]

    print(f"Database: {DB_FILE}")
    print(f"orders_raw rows:   {raw_count}")
    print(f"orders_clean rows: {clean_count}")
    print(f"fx_rates rows:     {fx_count}")
    print("\nSQL database created successfully.")


if __name__ == "__main__":
    load_database()
