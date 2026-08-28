import io
import requests
import pandas as pd
from pathlib import Path

INPUT_FILE = Path("orders_clean_preview.csv")
OUTPUT_FILE = Path("orders_clean_fx_preview.csv")
FX_API = "https://api.frankfurter.dev/v2/rates.csv"


def get_ron_eur_rates(min_date, max_date):
    """Download RON -> EUR historical rates from BNR."""

    today = pd.Timestamp.now().normalize()
    request_end = min(max_date, today)
    request_start = min_date - pd.Timedelta(days=10)

    params = {
        "base": "RON",
        "quotes": "EUR",
        "providers": "BNR",
        "from": request_start.strftime("%Y-%m-%d"),
        "to": request_end.strftime("%Y-%m-%d"),
    }

    headers = {
        "User-Agent": "Mozilla/5.0 Aqurate-Data-Pipeline/1.0",
        "Accept": "text/csv",
    }

    response = requests.get(
        FX_API,
        params=params,
        headers=headers,
        timeout=30
    )

    print(f"FX API status: {response.status_code}")
    response.raise_for_status()

    rates = pd.read_csv(
        io.StringIO(response.text),
        parse_dates=["date"]
    )

    if rates.empty:
        raise ValueError("Frankfurter nu a returnat cursuri BNR.")

    rates = rates[["date", "rate"]].copy()
    rates = rates.sort_values("date")
    rates = rates.drop_duplicates("date", keep="last")

    return rates


def add_fx_rates():
    if not INPUT_FILE.exists():
        raise FileNotFoundError(
            "orders_clean_preview.csv nu exista."
        )

    df = pd.read_csv(INPUT_FILE)

    df["fx_reference_date"] = pd.to_datetime(
        df["fx_reference_date"],
        errors="raise"
    ).dt.normalize()

    min_date = df["fx_reference_date"].min()
    max_date = df["fx_reference_date"].max()

    print("=" * 60)
    print("AQURATE - FX CONVERSION")
    print("=" * 60)
    print(f"Dataset FX period: {min_date.date()} -> {max_date.date()}")

    rates = get_ron_eur_rates(min_date, max_date)

    rates = rates.rename(columns={
        "date": "fx_reference_date",
        "rate": "fx_rate_to_eur"
    })

    calendar = pd.DataFrame({
        "fx_reference_date": pd.date_range(
            start=rates["fx_reference_date"].min(),
            end=max_date,
            freq="D"
        )
    })

    calendar = calendar.merge(
        rates,
        on="fx_reference_date",
        how="left"
    )

    # Weekend and future dates use last available BNR rate.
    calendar["fx_rate_to_eur"] = (
        calendar["fx_rate_to_eur"].ffill()
    )

    df = df.merge(
        calendar,
        on="fx_reference_date",
        how="left"
    )

    eur_mask = df["currency"].eq("EUR")
    ron_mask = df["currency"].eq("RON")

    # EUR already has EUR value.
    df.loc[eur_mask, "fx_rate_to_eur"] = 1.0

    unsupported = ~df["currency"].isin(["EUR", "RON"])

    if unsupported.any():
        currencies = sorted(
            df.loc[unsupported, "currency"].unique().tolist()
        )
        raise ValueError(f"Monede nesuportate: {currencies}")

    missing_rates = int(
        df.loc[ron_mask, "fx_rate_to_eur"].isna().sum()
    )

    if missing_rates > 0:
        raise ValueError(
            f"Lipsesc {missing_rates} cursuri RON/EUR."
        )

    df["line_total_eur"] = (
        df["line_total_original"]
        * df["fx_rate_to_eur"]
    ).round(2)

    df["net_amount_eur"] = df["line_total_eur"]

    refund_mask = df["status"].eq("refunded")

    df.loc[
        refund_mask,
        "net_amount_eur"
    ] = -df.loc[
        refund_mask,
        "line_total_eur"
    ]

    df.to_csv(OUTPUT_FILE, index=False)

    print(f"Rows processed: {len(df)}")
    print(f"EUR rows: {int(eur_mask.sum())}")
    print(f"RON rows: {int(ron_mask.sum())}")
    print(f"Missing FX rates: {missing_rates}")

    print("\nRON FX sample:")
    print(
        df.loc[
            ron_mask,
            ["fx_reference_date", "fx_rate_to_eur"]
        ]
        .drop_duplicates()
        .sort_values("fx_reference_date")
        .head(20)
        .to_string(index=False)
    )

    gross_total = df["line_total_eur"].sum()
    net_total = df["net_amount_eur"].sum()

    print("\nTotals:")
    print(f"Gross EUR: {gross_total:,.2f}")
    print(f"Net EUR:   {net_total:,.2f}")

    print(f"\nSaved: {OUTPUT_FILE}")

    return df


add_fx_rates()
