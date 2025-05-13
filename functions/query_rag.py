import os
import openai
import qdrant_client
import asyncio
import base64
import io
import logging
import json
import threading

from dotenv import load_dotenv
from typing import Optional, List, Dict, Any
from langchain_openai import OpenAI, AzureOpenAIEmbeddings,AzureChatOpenAI
from langchain_qdrant import QdrantVectorStore
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain.chains import RetrievalQA
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import StrOutputParser
from knowledge_base.rag_functions import embeddings



from fastapi import HTTPException
import qdrant_client.models

load_dotenv()

model = AzureChatOpenAI(model="gpt-4o",
                            api_key=os.getenv("AZURE_OPENAI_API_KEY"),
                            azure_endpoint=os.getenv("AZURE_OPENAI_ENDPOINT"),
                            api_version=os.getenv("AZURE_OPENAI_VERSION"),
                            max_tokens=4000)

collection_name = os.getenv("QDRANT_COLLECTION")



def connect_qdrant():
    try:
        client = qdrant_client.QdrantClient(
            url=os.getenv("QDRANT_URL"),
            api_key=os.getenv("QDRANT_API_KEY")
        
        )
        collection_config = qdrant_client.http.models.VectorParams(
            size=1536, 
            distance=qdrant_client.http.models.Distance.COSINE
            )
        
        logging.info("Qdrant client connected successfully.")
        return client
    except Exception as e:
        logging.error(f"Failed to connect to Qdrant: {e}")
        raise HTTPException(status_code=500, detail="Failed to connect to Qdrant.")


async def retrieve_chunks(user_query: str ,file_id_list : List[str],query_id : str , top_k: int = 10) -> Dict[str, Any]:
    """
    Asynchronously retrieves chunks from the RAG vector store and uses OpenAI to respond.

    Args:
        query (str): The user query.
        collection_name (str): The name of the collection to query.

    Returns:
        Dict[str, Any]: The retrieved chunks and response.
    """
    try:
        
        
        
        logging.info(f"top k : {top_k}")
        client = connect_qdrant()
        vectorstore = QdrantVectorStore(
            client=client,
            collection_name=collection_name,
            embedding=embeddings,
        )
        
        filter_condition = [
                    qdrant_client.models.FieldCondition(
                        key="metadata.file_id",
                        match=qdrant_client.models.MatchAny(any=file_id_list),
                    ),
                    # qdrant_client.models.FieldCondition(
                    #     key="metadata.thread_id",
                    #     match=qdrant_client.models.MatchValue(value=thread_id),
                    # ),
                    # qdrant_client.models.FieldCondition(
                    #     key="metadata.type",
                    #     match=qdrant_client.models.MatchValue(value="image"),
                    # ),
                       
                ]
        
        
        results = await vectorstore.asimilarity_search(
            user_query,
            k=top_k,
            filter=qdrant_client.models.Filter(
                must=filter_condition,
            ),
        )
        
        response = {
            "status_code": 200,
            "message": "success",
            "chunks": results,
        }
        # logging.info(f"Chunks response : {response}")
        return response
        
    
    except Exception as e:
        logging.exception(f"Error retrieving chunks: {e}")
        return  {
            "status_code" : 500,
            "message" : "failed", 
        }