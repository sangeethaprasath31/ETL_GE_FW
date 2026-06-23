from sqlalchemy import create_engine

def get_sqlserver_engine():

    connection_string = (
        "mssql+pyodbc://retaildbadmin:Dharmavaram1@"
        "@sqlserverretail756.database.windows.net/retaildb"
        "?driver=ODBC+Driver+18+for+SQL+Server"
    )

    return create_engine(connection_string)