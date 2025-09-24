import logging
from typing import List
from langchain_core.tools import tool
from functions.query_rag import retrieve_chunks
from utils.llm_calling import call_openai
from functions.notes_section.fetch_notes_page_from_vdb import get_notes_chunks

@tool
async def get_notes(notes_number: str, file_id_list: List, statement_type : str):
    
    """
    📄 Tool: get_notes

    📌 Description:
    Extracts the notes for the mentioned notes number.

    ✅ Use When:
    - The query asks to include notes section.

    🛠️ Parameters:
    - `notes_number` (str): Fetch the chunks with this Notes number.
    - `file_id_list` (list): List of file IDs to retrieve chunks from.
    - `statement_type` (int): mentioned consolidated or standalone.

    🧾 Returns:
    - Chunks with Notes section mentioned.

    """
    
    logging.info("Tool called : fetch_notes")
    
    try :
        
        rag_response = await get_notes_chunks(notes_number=notes_number, file_id_list=file_id_list, statement_type=statement_type)

        response = {
            "status_code": 200,
            "chunks": rag_response,
        }
        
        return response
        
        
    except Exception as e:
        response = {
            "status_code" : 500,
            "chunks" : "Not able to fetch the relevant chunks"
        }
        logging.info(f"Error : {e}")
        return response
    
    

