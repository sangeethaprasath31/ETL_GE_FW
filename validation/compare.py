from __future__ import annotations

from collections.abc import Iterable
from hashlib import sha256

import pandas as pd

from gx.expectations import result
from validation.db import read_query_in_chunks, scalar_query

def comparable_columns(
    source_columns: Iterable[str],
    target_columns: Iterable[str],
    target_meta_columns: Iterable[str],
) -> list[str]:
    source_set = set(source_columns)
    target_clean = [col for col in target_columns if col not in set(target_meta_columns)]
    return [col for col in target_clean if col in source_set]

def compare_column_names(
    table: str,
    source_layer: str,
    target_layer: str,
    source_df: pd.DataFrame,
    target_df: pd.DataFrame,
    target_meta_columns: list[str],
) -> list[dict]:
    target_business_columns = [
        column for column in target_df.columns if column not in set(target_meta_columns)
    ]
    source_columns = set(source_df.columns)
    target_columns = set(target_business_columns)

    return [
        result(
            table,
            f"{source_layer}->{target_layer}",
            "column_name_compare_excluding_target_meta",
            source_columns == target_columns,
            f"missing_in_target={sorted(source_columns - target_columns)}; "
            f"extra_in_target={sorted(target_columns - source_columns)}",
        ),
        result(
            table,
            f"{source_layer}->{target_layer}",
            "column_count_compare_excluding_target_meta",
            len(source_columns) == len(target_columns),
            f"source_count={len(source_columns)}; target_count={len(target_columns)}",
        ),
    ]

def compare_primary_key_values(
    table: str,
    source_layer: str,
    target_layer: str,
    source_df: pd.DataFrame,
    target_df: pd.DataFrame,
    primary_key: list[str],
) -> dict:
    missing = [
        column
        for column in primary_key
        if column not in source_df.columns or column not in target_df.columns
    ]
    if missing:
        return result(
            table,
            f"{source_layer}->{target_layer}",
            "primary_key_values_compare",
            False,
            f"missing_key_columns={missing}",
        )

    source_keys = set(map(tuple, source_df[primary_key].dropna().values.tolist()))
    target_keys = set(map(tuple, target_df[primary_key].dropna().values.tolist()))
    return result(
        table,
        f"{source_layer}->{target_layer}",
        "primary_key_values_compare",
        source_keys == target_keys,
        f"missing_in_target={sorted(source_keys - target_keys)[:20]}; "
        f"extra_in_target={sorted(target_keys - source_keys)[:20]}",
    )

def normalize_dataframe(df: pd.DataFrame, columns: list[str], primary_key: list[str]) -> pd.DataFrame:
    normalized = df.loc[:, columns].copy()
    sort_columns = [column for column in primary_key if column in columns] or columns
    if sort_columns:
        normalized = normalized.sort_values(by=sort_columns)
    return normalized.reset_index(drop=True)

def compare_sample_dataframes(
    table: str,
    source_layer: str,
    target_layer: str,
    source_df: pd.DataFrame,
    target_df: pd.DataFrame,
    columns: list[str],
    primary_key: list[str],
) -> dict:
    source_normalized = normalize_dataframe(source_df, columns, primary_key)
    target_normalized = normalize_dataframe(target_df, columns, primary_key)
    return result(
        table,
        f"{source_layer}->{target_layer}",
        "sample_dataframe_compare",
        source_normalized.equals(target_normalized),
        f"compared_columns={columns}; sample_rows={len(source_normalized)}",
    )

def dataframe_hash(df: pd.DataFrame, columns: list[str], primary_key: list[str]) -> str:
    normalized = normalize_dataframe(df, columns, primary_key)
    digest = sha256()
    for row in normalized.astype(str).itertuples(index=False, name=None):
        digest.update("|".join(row).encode("utf-8"))
        digest.update(b"\n")
    return digest.hexdigest()

def chunked_query_hash(engine, query: str, columns: list[str], primary_key: list[str], chunksize: int) -> str:
    digest = sha256()
    ordered_query = ordered_query_by_primary_key(query, primary_key)
    for chunk in read_query_in_chunks(engine, ordered_query, chunksize):
        available_columns = [column for column in columns if column in chunk.columns]
        chunk_hash = dataframe_hash(chunk, available_columns, primary_key)
        digest.update(chunk_hash.encode("utf-8"))
    return digest.hexdigest()

def ordered_query_by_primary_key(query: str, primary_key: list[str]) -> str:
    if not primary_key:
        return query
    order_by = ", ".join(primary_key)
    return f"SELECT * FROM ({query}) AS dq_ordered ORDER BY {order_by}"

def compare_large_table_hash(
    table: str,
    source_layer: str,
    target_layer: str,
    source_engine,
    target_engine,
    source_query: str,
    target_query: str,
    columns: list[str],
    primary_key: list[str],
    chunksize: int,
) -> dict:
    source_hash = chunked_query_hash(source_engine, source_query, columns, primary_key, chunksize)
    target_hash = chunked_query_hash(target_engine, target_query, columns, primary_key, chunksize)
    return result(
        table,
        f"{source_layer}->{target_layer}",
        "chunked_dataframe_hash_compare",
        source_hash == target_hash,
        f"source_hash={source_hash}; target_hash={target_hash}",
    )

def count_query(base_query: str) -> str:
    return f"SELECT COUNT(*) AS row_count FROM ({base_query}) AS dq_count"

def incremental_query(base_query: str, column: str, start: str, end: str) -> str:
    return (
        f"SELECT COUNT(*) AS row_count FROM ({base_query}) AS dq_incremental "
        f"WHERE {column} >= '{start}' AND {column} < '{end}'"
    )

def compare_incremental_load_percentage(
    table: str,
    source_engine,
    target_engine,
    source_query: str,
    target_query: str,
    incremental_column: str,
    job_window: dict,
    min_percent: float,
    max_percent: float,
) -> dict:
    start = job_window["start"]
    end = job_window["end"]
    source_count = scalar_query(source_engine, incremental_query(source_query, incremental_column, start, end))
    target_count = scalar_query(target_engine, incremental_query(target_query, incremental_column, start, end))
    percentage = 100 if source_count == 0 and target_count == 0 else (target_count / max(source_count, 1)) * 100
    return result(
        table,
        "source->bronze",
        "incremental_load_percentage",
        min_percent <= percentage <= max_percent,
        f"source_incremental_count={source_count}; target_incremental_count={target_count}; percentage={percentage:.2f}",
    )
