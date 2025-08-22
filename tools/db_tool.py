import logging
from langchain_core.tools import tool
from utils.postgres_connection import ConnectDB


@tool
def execute_sql(sql_query: str):
    """
    This function executes any select statement query which fetches data
    sql_query: Give me the sql query 
    """
    try:
        conn = ConnectDB()
        logging.info(f"[TOOL] Query: {sql_query}")

        response = conn.fetch(sql_query)

        logging.info(f"[TOOL] Execute SQL Response: {response}")

        return response
    except Exception as e:
        return None, f"SQL Error: {e}"

@tool
def list_particulars(file_id: str, table_name: str):
    """
    Fetch the list of particulars with SQL
    file_id: ID of the file in the database
    table_name: These are the options for the table_name (e.g. `balance sheet`, `cash flow statement`, `profit and loss`)
    """
    db = ConnectDB()
    query = f"""
        SELECT particulars, values, year, company_name from financial_statements 
        WHERE file_id = '{file_id}' AND table_name = '{table_name}';
    """
    try:
        logging.info(f"[TOOL] Query: {query}")

        response = db.fetch(query=query)

        logging.info(f"[TOOL] Execute List Particulars: {response}")

        return response
    except Exception as e:
        return e

 