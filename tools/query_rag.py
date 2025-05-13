import logging

from langchain_core.tools import tool

from functions.query_rag import retrieve_chunks
from langchain_core.runnables.config import RunnableConfig


@tool
async def fetch_relevant_response(user_query: str, user_id: str, query_id: str, file_id_list : list, top_k : int):
    """
    Fetches the chunks from the vector database for the relevant user query.

    Args:
        user_query (str): User query for fetching the relevant chunks.
        query_id (str): A unique identifier for the query.
        file_id_list (list) : List of file id to filter the chunks using the metadata.
        thread_id (str): A unique identifier for the chat thread.
        user_id (str): A unique identifier for individual user.

    Returns:
        dict 200: A list of chunks for the relevant query inside the chunks key.
        dict 500: An error message for not getting the chunks for the relevant query.
    """    
    
    try:
        # logging.info(f" from tool logging top k : {top_k}, thread id : {thread_id}, query id : {query_id}, file id list : {file_id_list}, user query : {user_query}")

        # Fetch the RAG response and chunks asynchronously
        rag_response = await retrieve_chunks(user_query=user_query, file_id_list = file_id_list,query_id=query_id, top_k=top_k)

        final_response = {
            "status_code": 200,
            "chunks": rag_response["chunks"],
        }
        
        return final_response
    
    except Exception as e:
        final_response = {
            "status_code" : 500,
            "chunks" : "Not able to fetch the relevant chunks"
        }
        logging.info(f"Error : {e} for query_id : {query_id}")
        return final_response