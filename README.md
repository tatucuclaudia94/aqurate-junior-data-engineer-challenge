# Aqurate Junior Data Engineer Challenge

## Solution Overview

For this challenge I implemented an end-to-end ETL pipeline in Python and SQL.

The solution extracts raw ecommerce orders from the provided Supabase API, validates and cleans the data, enriches monetary values with daily FX rates, stores the processed information in SQLite and generates the analytical tables required by the task.

The complete flow can be executed through a single Python entry point:

```bash
python pipeline.py