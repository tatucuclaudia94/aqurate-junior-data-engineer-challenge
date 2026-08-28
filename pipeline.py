import subprocess
import sys
from datetime import datetime


STEPS = [
    ("Data cleaning", "cleaning.py"),
    ("FX conversion", "fx_rates.py"),
    ("SQL database load", "load_database.py"),
    ("SQL queries", "run_queries.py"),
]


def run_step(name, script):
    print("\n" + "=" * 70)
    print(f"START: {name}")
    print("=" * 70)

    subprocess.run(
        [sys.executable, script],
        check=True
    )

    print(f"\nOK: {name}")


def run_pipeline():
    started = datetime.now()

    print("=" * 70)
    print("AQURATE DATA PIPELINE")
    print("=" * 70)
    print(f"Started: {started:%Y-%m-%d %H:%M:%S}")

    try:
        for name, script in STEPS:
            run_step(name, script)

    except subprocess.CalledProcessError as exc:
        print("\nPIPELINE FAILED")
        print(f"Script: {exc.cmd}")
        print(f"Exit code: {exc.returncode}")
        raise SystemExit(exc.returncode)

    finished = datetime.now()
    duration = finished - started

    print("\n" + "=" * 70)
    print("AQURATE PIPELINE COMPLETED SUCCESSFULLY")
    print("=" * 70)
    print(f"Finished: {finished:%Y-%m-%d %H:%M:%S}")
    print(f"Duration: {duration}")


if __name__ == "__main__":
    run_pipeline()
