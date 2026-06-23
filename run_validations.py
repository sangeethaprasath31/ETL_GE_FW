from __future__ import annotations

import argparse
from datetime import datetime
from html import escape
from pathlib import Path

#from dotenv import load_dotenv
#load_dotenv()

from gx.expectations import validate_data_quality
from gx.ge_context import GXRuntime
from validation.compare import (
    comparable_columns,
    compare_column_names,
    compare_incremental_load_percentage,
    compare_large_table_hash,
    compare_primary_key_values,
    compare_sample_dataframes,
)
from validation.config_reader import read_config
from validation.db import managed_engines, read_dataframe

def merge_rules(default_rules: dict, table_config: dict) -> dict:
    rules = dict(default_rules)
    for key in [
        "primary_key",
        "not_null_columns",
        "unique_columns",
        "compare_columns",
        "compare_column_count",
        "compare_primary_key_values",
        "compare_data",
        "incremental_load_percentage",
    ]:
        if key in table_config:
            rules[key] = table_config[key]
    return rules

def write_report(results: list[dict], report_dir: str) -> Path:
    output_dir = Path(report_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    report_path = output_dir / f"GE_DQ_Report_{datetime.now():%Y%m%d_%H%M%S}.html"

    rows = []
    for item in results:
        status = "PASS" if item["success"] else "FAIL"
        status_class = "pass" if item["success"] else "fail"
        rows.append(
            "<tr>"
            f"<td>{escape(item['table'])}</td>"
            f"<td>{escape(item['layer'])}</td>"
            f"<td>{escape(item['check'])}</td>"
            f"<td class='{status_class}'>{status}</td>"
            f"<td>{escape(item['details'])}</td>"
            "</tr>"
        )

    report_path.write_text(
        """
<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <title>Great Expectations Data Quality Report</title>
  <style>
    body { font-family: Arial, sans-serif; margin: 32px; color: #1f2937; }
    h1 { font-size: 24px; margin-bottom: 4px; }
    .meta { color: #6b7280; margin-bottom: 24px; }
    table { border-collapse: collapse; width: 100%; font-size: 14px; }
    th, td { border: 1px solid #d1d5db; padding: 8px; text-align: left; vertical-align: top; }
    th { background: #f3f4f6; }
    .pass { color: #047857; font-weight: 700; }
    .fail { color: #b91c1c; font-weight: 700; }
  </style>
</head>
<body>
  <h1>Great Expectations Data Quality Report</h1>
  <div class="meta">SQL Server -> Open -> Bronze -> Silver -> Gold</div>
  <table>
    <thead>
      <tr><th>Table</th><th>Layer</th><th>Check</th><th>Status</th><th>Details</th></tr>
    </thead>
    <tbody>
"""
        + "\n".join(rows)
        + """
    </tbody>
  </table>
</body>
</html>
""",
        encoding="utf-8",
    )
    return report_path

def validate_table(table_config: dict, config: dict, engines: dict, runtime: GXRuntime) -> list[dict]:
    table_name = table_config["name"]
    rules = merge_rules(config["default_rules"], table_config)
    layer_meta_columns = config.get("layer_meta_columns", {})
    sample_limit = config["runtime"]["sample_limit"]
    #chunksize = config["runtime"]["chunksize"]
    results: list[dict] = []

    layer_samples = {}
    for layer_name, layer_config in table_config["layers"].items(): # source ,  
        engine = engines[layer_config["connection"]] # conntion : snowflake 
        sample_df = read_dataframe(engine, layer_config["query"] , limit=sample_limit)
        layer_samples[layer_name] = sample_df # layer_sample[soruce]

        expected_columns = [
            column
            for column in sample_df.columns
            if column not in set(layer_meta_columns.get(layer_name, []))
        ]
        dq_df = sample_df.loc[:, expected_columns]
        results.extend(
            validate_data_quality(
                runtime=runtime,
                table=table_name,
                layer=layer_name,
                dataframe=dq_df,
                rules=rules,
                expected_columns=expected_columns,
            )
        )
    '''
    for comparison in table_config.get("comparisons", []):
        source_layer = comparison["source_layer"]  # source
        target_layer = comparison["target_layer"]  # open
        source_config = table_config["layers"][source_layer] # source
        target_config = table_config["layers"][target_layer] # open 
        source_df = layer_samples[source_layer] 
        target_df = layer_samples[target_layer]
        target_meta_columns = layer_meta_columns.get(target_layer, [])
        primary_key = rules.get("primary_key", [])

        columns = comparable_columns(source_df.columns, target_df.columns, target_meta_columns)
        results.extend(
            compare_column_names(
                table_name,
                source_layer,
                target_layer,
                source_df,
                target_df,
                target_meta_columns,
            )
        )
        
       
        if rules.get("compare_primary_key_values", True):
            results.append(
                compare_primary_key_values(
                    table_name,
                    source_layer,
                    target_layer,
                    source_df,
                    target_df,
                    primary_key,
                )
            )
        
       
        if rules.get("compare_data", True):
            results.append(
                compare_sample_dataframes(
                    table_name,
                    source_layer,
                    target_layer,
                    source_df,
                    target_df,
                    columns,
                    primary_key,
                )
            )
            results.append(
                compare_large_table_hash(
                    table_name,
                    source_layer,
                    target_layer,
                    engines[source_config["connection"]],
                    engines[target_config["connection"]],
                    source_config["query"],
                    target_config["query"],
                    columns,
                    primary_key,
                    chunksize,
                )
            )
        
        incremental_rules = rules.get("incremental_load_percentage", {})
        is_source_to_bronze = source_layer == "source" and target_layer == "bronze"
        if incremental_rules.get("enabled") and is_source_to_bronze:
            results.append(
                compare_incremental_load_percentage(
                    table_name,
                    engines[source_config["connection"]],
                    engines[target_config["connection"]],
                    source_config["query"],
                    target_config["query"],
                    table_config["incremental_column"],
                    table_config["job_window"],
                    incremental_rules["min_percent"],
                    incremental_rules["max_percent"],
                )
            )
        '''

    return results

def run(config_path: str) -> int:
    config = read_config(config_path)
    runtime = GXRuntime()
    results: list[dict] = []

    with managed_engines(config["connections"]) as engines:
        for table_config in config["tables"]:
            if not table_config.get("enabled", True):
                continue
            table_results = validate_table(table_config, config, engines, runtime)
            results.extend(table_results)

            if config["runtime"].get("fail_fast") and any(
                not item["success"] for item in table_results
            ):
                break

    report_path = write_report(results, config["report_dir"])
    failed = [item for item in results if not item["success"]]
    print(f"Report written to: {report_path}")
    print(f"Total checks: {len(results)}")
    print(f"Passed: {len(results) - len(failed)}")
    print(f"Failed: {len(failed)}")
    return 1 if failed else 0

def main() -> int:
    parser = argparse.ArgumentParser(description="Run Great Expectations DQ validations.")
    parser.add_argument("--config", default="config/table_config.json")
    args = parser.parse_args()
    return run(args.config)

if __name__ == "__main__":
    raise SystemExit(main())
