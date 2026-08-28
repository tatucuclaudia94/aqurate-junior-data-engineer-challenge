# Aqurate Junior Data Engineer Challenge

## Solution Overview

For this challenge I implemented an end-to-end ETL pipeline in Python and SQL.

The solution extracts raw ecommerce orders from the provided Supabase API, validates and cleans the data, enriches monetary values with daily FX rates, stores the processed information in SQLite and generates the analytical tables required by the task.

The complete flow is handled through a single pipeline entry point.

## Data Quality

The dataset contained duplicate rows, missing values, inconsistent SKU formats, mixed timestamp formats and invalid prices.

These issues were handled through normalization, validation rules, stable mappings and price repair where appropriate.

## Production Monitoring

In production I would monitor pipeline failures, API errors, execution time, processed row counts, missing values and FX conversion issues.

## Security

Dependency security is checked automatically using pip-audit.

Dependabot is also configured to monitor Python dependencies for security updates.

## AI Usage

AI was used as support for debugging, anomaly investigation and SQL review.

All final decisions and results were validated against the actual data and pipeline execution.