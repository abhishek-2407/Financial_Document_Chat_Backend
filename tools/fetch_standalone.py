import logging
from langchain_core.tools import tool
from functions.query_rag import retrieve_chunks
from utils.llm_calling import call_openai

@tool
async def fetch_standalone_data(standalone_user_query : str,file_id_list : list, top_k : int = 6, notes:str = None) :
    """
    📄 Tool: fetch_standalone_data

    📌 Description:
    Extracts only **standalone data** (non-consolidated) from documents based on a user query.

    🚫 Do Not Use When:
    - The query involves consolidated.

    🛠️ Parameters:
    - `standalone_user_query` (str): Query asking for standalone data.
    - `file_id_list` (list): List of file IDs to retrieve chunks from.
    - `top_k` (int): Number of top relevant chunks to fetch (default: 10).
    - `notes` ('Yes' or 'No'): Including Notes section or not

    🧾 Returns:
    - Chunks with standalone data only.
    - Error response with status 500 if chunk retrieval or processing fails.

    """
    logging.info("Tool called : fetch_standalone_data")
    logging.info(f"Notes : {notes}")

    top_k_default= 6
    
    try :
        
        rag_response = await retrieve_chunks(user_query=f"{standalone_user_query}", file_id_list = file_id_list, top_k=top_k_default, statement_type=["standalone","both"], is_financial_statement="Yes", notes=notes)

        response = {
            "status_code": 200,
            "chunks": rag_response["chunks"],
        }
        
        return response
        
        
    except Exception as e:
        response = {
            "status_code" : 500,
            "chunks" : "Not able to fetch the relevant chunks"
        }
        logging.info(f"Error : {e}")
        return response
    
    
