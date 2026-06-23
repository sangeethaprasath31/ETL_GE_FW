from __future__ import annotations

import os
from contextlib import contextmanager
from pathlib import Path
from typing import Iterator
from urllib.parse import quote_plus

import pandas as pd
from sqlalchemy import create_engine, text
from sqlalchemy.engine import Engine


from dotenv import load_dotenv
load_dotenv(Path("config") / "connection_template.env")


def _env(prefix: str, name: str, default: str | None = None) -> str:
    value = os.getenv(f"{prefix}_{name}", default)
    if value is None:
        raise ValueError(f"Missing environment variable: {prefix}_{name}")
    return value

'''
def create_sqlserver_engine(prefix: str) -> Engine:
    print(os.getenv("SQLSERVER_SERVER"))
    driver = quote_plus(_env(prefix, "DRIVER", "ODBC Driver 18 for SQL Server"))
    server = _env(prefix, "SERVER")
    database = _env(prefix, "DATABASE")
    username = quote_plus(_env(prefix, "USERNAME"))
    password = quote_plus(_env(prefix, "PASSWORD"))
    url = (
        f"mssql+pyodbc://{username}:{password}@{server}/{database}"
        f"?driver={driver}&Encrypt=yes&TrustServerCertificate=yes"
    )
    return create_engine(url, fast_executemany=True, pool_pre_ping=True)
'''
def create_snowflake_engine(prefix: str) -> Engine:

    account = _env(prefix, "ACCOUNT")
    user = quote_plus(_env(prefix, "USER"))
    password = quote_plus(_env(prefix, "PASSWORD"))
    database = _env(prefix, "DATABASE")
    warehouse = _env(prefix, "WAREHOUSE")
    schema = _env(prefix, "SCHEMA", "PUBLIC")
    role = os.getenv(f"{prefix}ROLE")
    role_part = f"&role={quote_plus(role)}" if role else ""
   

    url = (
        f"snowflake://{user}:{password}@{account}/{database}/{schema}"
        f"?warehouse={warehouse}{role_part}"
    )
    
    return create_engine(url, pool_pre_ping=True)

'''
def get_snowflake_engine():
    
    user = "SANGITARMP"
    password = quote_plus("Angrybird@2026")

    connection_string = (f"snowflake://{user}:{password}"
        "@OKGQXGH-XZ64723/EMPLOYEE/PUBLIC"
        "?warehouse=COMPUTE_WH"
    )

    return create_engine(connection_string)

'''
def create_engines(connection_config: dict) -> dict[str, Engine]:
    engines: dict[str, Engine] = {}
    for connection_name, details in connection_config.items():
        print(connection_name)
        print(details)
        connection_type = details["type"].lower()
        prefix = details["env_prefix"]

        if connection_type == "snowflake":
            engines[connection_name] = create_snowflake_engine(prefix)
        elif connection_type == "snowflake":
            engines[connection_name] = create_snowflake_engine(prefix)
        else:
            raise ValueError(f"Unsupported connection type: {connection_type}")

    return engines


def dispose_engines(engines: dict[str, Engine]) -> None:
    for engine in engines.values():
        engine.dispose()

def read_dataframe(engine: Engine, query: str, limit: int | None = None) -> pd.DataFrame:
    dataframe = pd.read_sql_query(text(query), engine)
    return dataframe.head(limit) if limit else dataframe

def read_query_in_chunks(
    engine: Engine,
    query: str,
    chunksize: int,
) -> Iterator[pd.DataFrame]:
    yield from pd.read_sql_query(text(query), engine, chunksize=chunksize)

def scalar_query(engine: Engine, query: str):
    with engine.connect() as connection:
        return connection.execute(text(query)).scalar()

@contextmanager
def managed_engines(connection_config: dict):
    engines = create_engines(connection_config)
    try:
        yield engines
    finally:
        dispose_engines(engines)
