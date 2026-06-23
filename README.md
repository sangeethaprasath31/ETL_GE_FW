# Great Expectations 36-Table Data Quality Framework

This is a fresh Great Expectations framework for validating ETL data quality
across:

```text
SQL Server -> Open -> Bronze -> Silver -> Gold
```

It is JSON-config driven and designed for 36 tables. You add tables in
`config/table_config.json`; you do not need to create one Python test per table.

## What It Validates

- Not-null columns.
- Unique primary keys.
- Column-name comparison, excluding target metadata columns.
- Column-count comparison, excluding target metadata columns.
- Incremental-load percentage from SQL Server to Bronze for each job window.
- Primary-key value comparison.
- Sample dataframe comparison.
- Chunked full-table hash comparison for large tables.

## Metadata Columns

The JSON config excludes target layer metadata columns during business-column
comparison.

Open layer:

```text
SNOWFLAKE_INSERTED_DATE
SNOWFLAKE_UPDATED_DATE
SNOWFLAKE_DELETED
```

Bronze layer:

```text
META_SOURCE_ACTION
SNOWFLAKE_INSERTED_DATE
SNOWFLAKE_UPDATED_DATE
SNOWFLAKE_DELETED
```

Silver and Gold metadata columns can also be configured in
`layer_meta_columns`.

## Large Tables

For tables with millions of rows, the framework uses:

- `pandas.read_sql_query(..., chunksize=...)` for full-table hash comparison.
- `sample_limit` for Great Expectations checks that are safe to run on a sample.
- SQL `COUNT(*)` for incremental-load percentage checks.

Set these in `config/table_config.json`:

```json
"runtime": {
  "chunksize": 100000,
  "sample_limit": 10000,
  "fail_fast": false
}
```

## Configure Connections

Copy `config/connection_template.env` into your local environment variables.
Do not commit real passwords.

Required SQL Server variables:

```text
SQLSERVER_SERVER
SQLSERVER_DATABASE
SQLSERVER_USERNAME
SQLSERVER_PASSWORD
SQLSERVER_DRIVER
```

Required Snowflake variables:

```text
SNOWFLAKE_ACCOUNT
SNOWFLAKE_USER
SNOWFLAKE_PASSWORD
SNOWFLAKE_WAREHOUSE
SNOWFLAKE_DATABASE
SNOWFLAKE_SCHEMA
SNOWFLAKE_ROLE
```

## Add 36 Tables

In `config/table_config.json`, copy a table object and update:

- `name`
- `primary_key`
- `not_null_columns`
- `unique_columns`
- `incremental_column`
- `job_window`
- SQL for each layer under `layers`
- Layer hops under `comparisons`

Example comparisons:

```json
"comparisons": [
  {"source_layer": "source", "target_layer": "open"},
  {"source_layer": "source", "target_layer": "bronze"},
  {"source_layer": "bronze", "target_layer": "silver"},
  {"source_layer": "silver", "target_layer": "gold"}
]
```

## Run

Install dependencies:

```powershell
pip install -r requirements.txt
```

Run directly:

```powershell
python run_validations.py --config config/table_config.json
```

Run with pytest:

```powershell
pytest tests/test_dq_framework.py
```

Reports are written to:

```text
reports/GE_DQ_Report_*.html
```

