import logging
from langchain_core.tools import tool
from functions.query_rag import retrieve_chunks
from utils.llm_calling import call_openai

@tool
async def fetch_standalone_data(standalone_user_query : str,file_id_list : list, top_k : int = 10) :
    """
    📄 Tool: fetch_standalone_data

    📌 Description:
    Extracts only **standalone data** (non-consolidated) from documents based on a user query.
    This tool should be triggered **only when the user asks for standalone figures** — not combined, summarized, or comparative insights.

    ✅ Use When:
    - The query is focused on a single entity or time period.
    - Only individual (non-aggregated) data points are required.

    🚫 Do Not Use When:
    - The query involves consolidated, summarized, or comparative data across multiple entities or periods.

    🛠️ Parameters:
    - `standalone_user_query` (str): Query asking for standalone data.
    - `file_id_list` (list): List of file IDs to retrieve chunks from.
    - `top_k` (int): Number of top relevant chunks to fetch (default: 10).

    🧾 Returns:
    - Markdown-formatted response with standalone data only.
    - Error response with status 500 if chunk retrieval or processing fails.

    📢 Note:
    Consolidated or combined data will be explicitly ignored in the response.
    """
    logging.info("Tool called : fetch_standalone_data")
    
    try :
        
        rag_response = await retrieve_chunks(user_query=standalone_user_query, file_id_list = file_id_list, top_k=top_k)

        response = {
            "status_code": 200,
            "chunks": rag_response["chunks"],
        }
        
        system_prompt = """You are a assisstant which only extract standalone Data for the Asked User Query
        
        ##Instructions :
        - Only Response with the standalone data. 
        - If you get any consolidated data then just Ignore it. Your response must only have Standalone data.
        - Only Extract information from dataset Provided to you.
        
        ##Response :
        - Provide the response in valid markdown down. NO Insights Should be Provided untill asked.
         """
         
        extracted_chunks = response["chunks"] 
        user_prompt = f"""
        
        Data : {extracted_chunks}
        
        User_query : {standalone_user_query}"""
         
        final_response = call_openai(system_prompt=system_prompt, user_prompt=user_prompt, model="gpt-4o")
        
        return final_response
        
        
    except Exception as e:
        response = {
            "status_code" : 500,
            "chunks" : "Not able to fetch the relevant chunks"
        }
        logging.info(f"Error : {e}")
        return response
    
    