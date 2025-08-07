import logging
from langchain_core.tools import tool
from functions.query_rag import retrieve_chunks
from utils.llm_calling import call_openai

@tool
async def fetch_consolidated_data(consolidated_user_query: str, file_id_list: list, top_k: int = 10):
    """
    📄 Tool: fetch_consolidated_data

    📌 Description:
    Extracts only **consolidated or summarized data** from documents based on a user query.
    This tool should be triggered **only when the user is asking for overall performance, comparison, or combined metrics** across multiple entities or time periods.

    ✅ Use When:
    - The query asks for consolidated results (e.g., YoY, QoQ, total/average performance).
    - The user is seeking summaries, combined financials, or comparative insights.

    🚫 Do Not Use When:
    - The query is looking for specific standalone figures for a single entity or time period.

    🛠️ Parameters:
    - `consolidated_user_query` (str): Query asking for consolidated/summarized data.
    - `file_id_list` (list): List of file IDs to retrieve chunks from.
    - `top_k` (int): Number of top relevant chunks to fetch (default: 10).

    🧾 Returns:
    - Markdown-formatted response with consolidated data only.
    - Error response with status 500 if chunk retrieval or processing fails.

    📢 Note:
    Standalone or isolated values should be excluded unless part of the overall consolidated insight.
    """

    logging.info("Tool called : fetch_consolidated_data")


    try:
        rag_response = await retrieve_chunks(user_query=consolidated_user_query, file_id_list=file_id_list, top_k=top_k)

        response = {
            "status_code": 200,
            "chunks": rag_response["chunks"],
        }

        system_prompt = """You are an assistant that extracts only **consolidated data for the given user query.

        ## Instructions:
        - Only return **consolidated data** metrics.
        - If you get any Standalone data then just Ignore it. Your response must only have **Consolidated** data from the document.
        - Do not generate insights unless explicitly asked — stick to raw consolidated facts from the provided dataset.
        
        Just extract the consolidated data only from the document that agent can proceed ahead. 

        ## Response:
        - Provide the response in valid markdown format. Avoid additional commentary.
        """

        extracted_chunks = response["chunks"]
        user_prompt = f"""

        Data : {extracted_chunks}

        User_query : {consolidated_user_query}
        """

        final_response = call_openai(system_prompt=system_prompt, user_prompt=user_prompt, model="gpt-4o")

        return final_response

    except Exception as e:
        response = {
            "status_code": 500,
            "chunks": "Not able to fetch the relevant chunks"
        }
        logging.info(f"Error : {e}")
        return response
