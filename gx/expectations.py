from __future__ import annotations

from typing import Any

import great_expectations as gx
import pandas as pd

from gx.ge_context import GXRuntime

def result(table: str, layer: str, check: str, success: bool, details: Any = "") -> dict:
    return {
        "table": table,
        "layer": layer,
        "check": check,
        "success": success,
        "details": str(details),
    }

def _validate(
    runtime: GXRuntime,
    table: str,
    layer: str,
    dataframe: pd.DataFrame,
    check: str,
    expectation,
) -> dict:
    batch = runtime.batch(f"{table}_{layer}_{check}", dataframe)
    validation_result = batch.validate(expectation)
    return result(
        table=table,
        layer=layer,
        check=check,
        success=bool(validation_result.success),
        details=getattr(validation_result, "result", {}),
    )

def validate_data_quality(
    runtime: GXRuntime,
    table: str,
    layer: str,
    dataframe: pd.DataFrame,
    rules: dict,
    expected_columns: list[str] | None = None,
) -> list[dict]:
    checks: list[dict] = []

    checks.append(
        _validate(
            runtime,
            table,
            layer,
            dataframe,
            "table_not_empty",
            gx.expectations.ExpectTableRowCountToBeBetween(min_value=1),
        )
    )

    if expected_columns:
        checks.append(
            _validate(
                runtime,
                table,
                layer,
                dataframe,
                "expected_columns",
                gx.expectations.ExpectTableColumnsToMatchSet(
                    column_set=expected_columns,
                    exact_match=True,
                ),
            )
        )

    return checks
