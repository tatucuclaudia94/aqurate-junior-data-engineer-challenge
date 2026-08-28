import os
import requests
from dotenv import load_dotenv

load_dotenv()


def fetch_orders_raw():
    """Fetch raw orders from the Aqurate Supabase endpoint."""

    url = os.getenv("AQURATE_ORDERS_URL")

    if not url:
        raise ValueError(
            "AQURATE_ORDERS_URL lipseste din fisierul .env."
        )

    response = requests.get(url, timeout=30)
    response.raise_for_status()

    orders = response.json()

    if not isinstance(orders, list):
        raise ValueError(
            "Raspunsul API nu este o lista de comenzi."
        )

    return orders
