import logging
from langchain_core.tools import tool
from functions.query_rag import retrieve_chunks
from utils.llm_calling import call_openai

@tool
async def fetch_consolidated_data(consolidated_user_query: str, file_id_list: list, top_k: int = 6, notes:str = None):
    """
    📄 Tool: fetch_consolidated_data

    📌 Description:
    Extracts only **consolidated data** from documents based on a user query.

    ✅ Use When:
    - The query asks for consolidated results .

    🚫 Do Not Use When:
    - The query is looking for specific standalone figures.

    🛠️ Parameters:
    - `consolidated_user_query` (str): Query asking for consolidated/summarized data.
    - `file_id_list` (list): List of file IDs to retrieve chunks from.
    - `top_k` (int): Number of top relevant chunks to fetch (default: 10).
    - `notes` ('No' or None): Including Notes section or not

    🧾 Returns:
    - Chunks with consolidated data only.
    - Error response with status 500 if chunk retrieval or processing fails.

    """
    logging.info("Tool called : fetch_consolidated_data")
    # logging.info(f"Notes : {notes}")

    top_k_default= 6


    try:
        rag_response = await retrieve_chunks(user_query=f"{consolidated_user_query}", file_id_list=file_id_list, top_k=top_k_default, statement_type=["consolidated", "both"], is_financial_statement="Yes", notes=notes)

        response = {
            "status_code": 200,
            "chunks": rag_response["chunks"],
        }

        return response

    except Exception as e:
        response = {
            "status_code": 500,
            "chunks": "Not able to fetch the relevant chunks"
        }
        logging.info(f"Error : {e}")
        return response
