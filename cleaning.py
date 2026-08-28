import pandas as pd
from database import fetch_orders_raw


SKU_FIXES = {
    "SKU-FA-O03": "SKU-FA-003",
    "SKU HK 003": "SKU-HK-003",
    "SKUEL001": "SKU-EL-001",
}


def parse_order_timestamp(series):
    values = series.astype("string").str.strip()

    result = pd.Series(
        pd.NaT,
        index=values.index,
        dtype="datetime64[ns, UTC]"
    )

    numeric = pd.to_numeric(values, errors="coerce")
    numeric_mask = numeric.notna()

    seconds_mask = (
        numeric_mask
        & (numeric.abs() < 100_000_000_000)
    )

    milliseconds_mask = numeric_mask & ~seconds_mask

    if seconds_mask.any():
        result.loc[seconds_mask] = pd.to_datetime(
            numeric.loc[seconds_mask],
            unit="s",
            errors="coerce",
            utc=True
        )

    if milliseconds_mask.any():
        result.loc[milliseconds_mask] = pd.to_datetime(
            numeric.loc[milliseconds_mask],
            unit="ms",
            errors="coerce",
            utc=True
        )

    text_mask = ~numeric_mask

    if text_mask.any():
        result.loc[text_mask] = pd.to_datetime(
            values.loc[text_mask],
            format="mixed",
            errors="coerce",
            utc=True
        )

    return result


def clean_orders():
    raw = pd.DataFrame(fetch_orders_raw())
    df = raw.copy()

    raw_rows = len(df)

    df = df.replace(r"^\s*$", pd.NA, regex=True)

    text_columns = [
        "customer_email",
        "status",
        "channel",
        "sku",
        "product_name",
        "category",
        "currency",
        "country"
    ]

    for column in text_columns:
        df[column] = df[column].astype("string").str.strip()

    df["status"] = df["status"].str.lower()
    df["channel"] = df["channel"].str.lower()
    df["currency"] = df["currency"].str.upper()
    df["country"] = df["country"].str.upper()

    # Exact duplicates from the source
    exact_duplicates = int(df.duplicated().sum())
    df = df.drop_duplicates().copy()

    # Normalize known SKU formatting errors
    sku_fixed_rows = int(df["sku"].isin(SKU_FIXES).sum())
    df["sku"] = df["sku"].replace(SKU_FIXES)

    # Numeric conversions
    df["customer_id"] = pd.to_numeric(
        df["customer_id"],
        errors="coerce"
    ).astype("Int64")

    df["qty"] = pd.to_numeric(df["qty"], errors="coerce")
    df["unit_price"] = pd.to_numeric(
        df["unit_price"],
        errors="coerce"
    )

    # Recover customer_id from customer email
    customer_missing_before = int(df["customer_id"].isna().sum())

    email_ids = df["customer_email"].str.extract(
        r"customer(\d+)@",
        expand=False
    )

    email_ids = pd.to_numeric(
        email_ids,
        errors="coerce"
    ).astype("Int64")

    customer_mask = (
        df["customer_id"].isna()
        & email_ids.notna()
    )

    df.loc[customer_mask, "customer_id"] = (
        email_ids.loc[customer_mask]
    )

    # Recover missing category using stable SKU mappings
    category_missing_before = int(df["category"].isna().sum())

    known_categories = df.dropna(
        subset=["sku", "category"]
    ).copy()

    category_counts = known_categories.groupby("sku")[
        "category"
    ].nunique()

    stable_skus = category_counts[
        category_counts == 1
    ].index

    category_map = (
        known_categories[
            known_categories["sku"].isin(stable_skus)
        ]
        .drop_duplicates("sku")
        .set_index("sku")["category"]
    )

    category_mask = df["category"].isna()

    df.loc[category_mask, "category"] = (
        df.loc[category_mask, "sku"].map(category_map)
    )

    # Parse timestamps
    df["order_ts"] = parse_order_timestamp(df["order_ts"])

    df["fx_reference_date"] = pd.to_datetime(
        df["fx_reference_date"],
        format="mixed",
        errors="coerce"
    )

    # Remove non-production test records
    test_rows = int((df["status"] == "test").sum())
    df = df[df["status"] != "test"].copy()

    # Remove impossible quantities
    bad_qty = df["qty"].isna() | (df["qty"] <= 0)
    bad_qty_rows = int(bad_qty.sum())
    df = df[~bad_qty].copy()

    # Detect corrupted prices
    bad_price = (
        df["unit_price"].isna()
        | (df["unit_price"] <= 0)
        | (df["unit_price"] == 999999)
    )

    bad_price_rows = int(bad_price.sum())

    # Compute median valid price for each SKU + currency
    valid_prices = df.loc[~bad_price].copy()

    price_medians = (
        valid_prices
        .groupby(["sku", "currency"], as_index=False)
        ["unit_price"]
        .median()
        .rename(columns={
            "unit_price": "median_unit_price"
        })
    )

    df = df.merge(
        price_medians,
        on=["sku", "currency"],
        how="left"
    )

    bad_price = (
        df["unit_price"].isna()
        | (df["unit_price"] <= 0)
        | (df["unit_price"] == 999999)
    )

    repaired_prices = int(
        (bad_price & df["median_unit_price"].notna()).sum()
    )

    df.loc[bad_price, "unit_price"] = (
        df.loc[bad_price, "median_unit_price"]
    )

    unresolved_price = (
        df["unit_price"].isna()
        | (df["unit_price"] <= 0)
        | (df["unit_price"] == 999999)
    )

    unresolved_price_rows = int(unresolved_price.sum())
    df = df[~unresolved_price].copy()

    df = df.drop(columns=["median_unit_price"])

    # Remove rows whose dates cannot be interpreted
    bad_dates = (
        df["order_ts"].isna()
        | df["fx_reference_date"].isna()
    )

    bad_date_rows = int(bad_dates.sum())
    df = df[~bad_dates].copy()

    # Remaining critical missing data
    critical_missing = (
        df["customer_id"].isna()
        | df["category"].isna()
        | df["sku"].isna()
        | df["customer_email"].isna()
    )

    critical_missing_rows = int(critical_missing.sum())
    df = df[~critical_missing].copy()

    df["qty"] = df["qty"].astype("Int64")

    df["line_total_original"] = (
        df["qty"] * df["unit_price"]
    ).round(2)

    df = df.reset_index(drop=True)

    print("=" * 60)
    print("AQURATE - FINAL CLEANING RESULT")
    print("=" * 60)

    print(f"Raw rows: {raw_rows}")
    print(f"Exact duplicates removed: {exact_duplicates}")
    print(f"Malformed SKU rows normalized: {sku_fixed_rows}")
    print(f"Test rows removed: {test_rows}")
    print(f"Invalid qty rows removed: {bad_qty_rows}")
    print(f"Invalid prices detected: {bad_price_rows}")
    print(f"Invalid prices repaired: {repaired_prices}")
    print(f"Unresolved prices removed: {unresolved_price_rows}")
    print(f"Invalid date rows removed: {bad_date_rows}")
    print(f"Critical missing rows removed: {critical_missing_rows}")

    print("\nCustomer ID:")
    print(f"Missing before repair: {customer_missing_before}")

    print("\nCategory:")
    print(f"Missing before repair: {category_missing_before}")

    print("\nFinal validation:")
    print(f"Final clean rows: {len(df)}")
    print(f"Remaining missing values: {int(df.isna().sum().sum())}")
    print(f"unit_price = 999999: {int((df["unit_price"] == 999999).sum())}")
    print(f"unit_price <= 0: {int((df["unit_price"] <= 0).sum())}")

    malformed = ~df["sku"].astype(str).str.match(
        r"^SKU-[A-Z]{2}-\d{3}$"
    )

    print(f"Malformed SKU rows remaining: {int(malformed.sum())}")

    df.to_csv("orders_clean_preview.csv", index=False)

    print("\nSaved: orders_clean_preview.csv")

    return df


clean_orders()
