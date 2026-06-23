import pandas as pd
import great_expectations as gx
from sqlalchemy import create_engine
from urllib.parse import quote_plus

from great_expectations.expectations import (
    ExpectColumnValuesToNotBeNull,
    ExpectColumnValuesToBeUnique,
    ExpectColumnToExist,
)

def fetch_employee_data():
    user = "SANGITARMP"
    password = quote_plus("Angrybird@2026")

    engine = create_engine(
        f"snowflake://{user}:{password}"
        "@OKGQXGH-XZ64723/EMPLOYEE/PUBLIC"
        "?warehouse=COMPUTE_WH"
    )

    query = """
        SELECT *
        FROM EMPLOYEE.COMPANY.EMPLOYEE
    """

    with engine.connect() as conn:
        return pd.read_sql(query, conn)


def validate_employee_data():

    # Fetch data from Snowflake
    df = fetch_employee_data()

    # Create GX Context
    context = gx.get_context(mode="ephemeral")

    # Create Datasource
    datasource = context.data_sources.add_pandas(
        name="employee_ds"
    )

    # Create Asset
    asset = datasource.add_dataframe_asset(
        name="employee_asset"
    )

    # Create Batch Definition
    batch_definition = asset.add_batch_definition_whole_dataframe(
        name="employee_batch"
    )
  
    # Create Batch
    batch = batch_definition.get_batch(
        batch_parameters={"dataframe": df}
    )
   

    # Create Expectation Suite
    suite = gx.ExpectationSuite(
        name="employee_dq_suite"
    )

    # DQ Checks
    suite.add_expectation(
        ExpectColumnToExist(
            column="emp_no"
        )
    )

    suite.add_expectation(
        ExpectColumnValuesToNotBeNull(
            column="emp_no"
        )
    )

    suite.add_expectation(
        ExpectColumnValuesToBeUnique(
            column="emp_no"
        )
    )

    # Validate
    result = batch.validate(suite)

    return result

def test_employee_dq():

    results = validate_employee_data()

    assert results.success, (
        f"Validation Failed:\n{results}"
    )