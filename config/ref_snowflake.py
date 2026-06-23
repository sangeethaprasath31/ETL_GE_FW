from sqlalchemy import create_engine

def get_snowflake_engine():

    connection_string = (
        "snowflake://SANGITARMP:Angrybird@2026"
        "@OKGQXGH-XZ64723/EMPLOYEE/PUBLIC"
        "?warehouse=COMPUTE_WH"
    )

    return create_engine(connection_string)


def get_snowflake_engine():
    
    user = "SANGITARMP"
    #password = quote_plus("Angrybird@2026")

    connection_string = (f"snowflake://{user}:Angrybird@2026"
        "@OKGQXGH-XZ64723/EMPLOYEE/PUBLIC"
        "?warehouse=COMPUTE_WH"
    )

    return create_engine(connection_string)