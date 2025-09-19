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
                            temperature=0,
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


async def retrieve_chunks(
            user_query: str = "" ,
            file_id_list : List[str] = [], 
            top_k: int = 10, 
            page_list: List[int] = [] , 
            statement_type : Optional[List[str]] = None, 
            is_financial_statement : str = None,
            notes : str = None,
            core_statements : str = None
            ) -> Dict[str, Any]:
    """
    Asynchronously retrieves chunks from the RAG vector store and uses OpenAI to respond.

    Args:
        query (str): The user query.
        collection_name (str): The name of the collection to query.

    Returns:
        Dict[str, Any]: The retrieved chunks and response.
    """
    try:
        
        
        
        logging.info(f"query: {user_query}, top k : {top_k}, Page_number : {page_list}, statement_type : {statement_type}, is_financial_statement : {is_financial_statement}, notes : {notes}, core_statements : {core_statements}")
        client = connect_qdrant()
        # vectorstore = QdrantVectorStore(
        #     client=client,
        #     collection_name=collection_name,
        #     embedding=embeddings,
        # )
        
        logging.info(f"file id list : {file_id_list}")
        
        filter_condition = [
                    qdrant_client.models.FieldCondition(
                        key="metadata.file_id",
                        match=qdrant_client.models.MatchAny(any=file_id_list),
                    ),
                    # qdrant_client.models.FieldCondition(
                    #     key="metadata.type",
                    #     match=qdrant_client.models.MatchValue(value="text"),
                    # )
                    # qdrant_client.models.FieldCondition(
                    #     key="metadata.thread_id",
                    #     match=qdrant_client.models.MatchValue(value=thread_id),
                    # ),
                    # qdrant_client.models.FieldCondition(
                    #     key="metadata.type",
                    #     match=qdrant_client.models.MatchValue(value="image"),
                    # ),
                ]
        
        if page_list:
            filter_condition.append(
                qdrant_client.models.FieldCondition(
                        key="metadata.page_number",
                        match=qdrant_client.models.MatchAny(any=page_list),
                    ))
            
        if statement_type:
            filter_condition.append(
                qdrant_client.models.FieldCondition(
                        key="metadata.statement_type",
                        match=qdrant_client.models.MatchAny(any=statement_type),
                    ))
            
        if is_financial_statement:
            filter_condition.append(
                qdrant_client.models.FieldCondition(
                        key="metadata.is_financial_statement",
                        match=qdrant_client.models.MatchValue(value=is_financial_statement),
                    ))
            
        if notes:
            filter_condition.append(
                qdrant_client.models.FieldCondition(
                        key="metadata.notes",
                        match=qdrant_client.models.MatchValue(value=notes),
                    ))
            
        if core_statements:
            filter_condition.append(
                qdrant_client.models.FieldCondition(
                        key="metadata.core_statements",
                        match=qdrant_client.models.MatchValue(value=core_statements),
                    ))
            
        # results = await vectorstore.asimilarity_search(
        #     user_query,
        #     k=top_k,
        #     filter=qdrant_client.models.Filter(
        #         must=filter_condition,
        #     ),
        # )

        text_embedding_small_3 = AzureOpenAIEmbeddings(
            model="text-embedding-3-small",
            api_key=os.getenv("AZURE_OPENAI_API_KEY"),
            azure_endpoint=os.getenv("AZURE_OPENAI_ENDPOINT"),
            api_version=os.getenv("AZURE_OPENAI_VERSION"),
            dimensions=1536,
        )
        # bm25_embedding_model = qdrant_client.models.SparseTextEmbedding("Qdrant/bm25")
        # colbert_embedding_model = qdrant_client.models.LateInteractionTextEmbedding("colbert-ir/colbertv2.0")


        results = client.query_points(
            limit=top_k,
            collection_name=collection_name,
            # query=next(colbert_embedding_model.query_embed(user_query)),
            query=text_embedding_small_3.embed_query(user_query),
            # using="colbert",
            using="text-embedding-3-small",
            # prefetch=[
            #    qdrant_client.models.Prefetch(
            #         query=text_embedding_small_3.embed_query(user_query),
            #         using="text-embedding-3-small",
            #         limit=20,
            #     ),
            #    qdrant_client.models.Prefetch(
            #         query=qdrant_client.models.SparseVector(**next(bm25_embedding_model.query_embed(user_query)).as_object()),
            #         using="bm25",
            #         limit=20,
            #     ),
            # ],
            query_filter=qdrant_client.models.Filter(
                must=[
                   *filter_condition,
                    #qdrant_client.models.FieldCondition(
                    #     key="metadata.page_number",
                    #     match=qdrant_client.models.MatchAny(any=[324]),
                    # ),
                   qdrant_client.models.FieldCondition(
                        key="metadata.type",
                        match=qdrant_client.models.MatchValue(value="text"),
                    ),
                ]
            ),
            with_payload=True,
        )

        smaller_chunks = results.points
        logging.info(f"Smaller chunks: {len(smaller_chunks)}")
        pages_of_fetched_chunks = set(r.payload['metadata']['page_number'] for r in results.points)
        logging.info(f"Initial pages fetched: {pages_of_fetched_chunks}")
        # logging.info(f"Initial pages fetched: {type(list(pages_of_fetched_chunks)[0])}")
        # for i in results.points:
        #     pages_of_fetched_chunks.add(i.payload['metadata']['page_number'] + 1)
        #     pages_of_fetched_chunks.add(i.payload['metadata']['page_number'] - 1)
        # logging.info(f"Populates pages fetched: {list(pages_of_fetched_chunks)}")


        # from rich import print
        # print(pages_of_fetched_chunks)

        results, _ = client.scroll(
            collection_name=collection_name,
            scroll_filter=qdrant_client.models.Filter(
                must=[
                   *filter_condition,
                    qdrant_client.models.FieldCondition(
                        key="metadata.file_id",
                        match=qdrant_client.models.MatchAny(any=file_id_list),
                    ),
                    qdrant_client.models.FieldCondition(
                        key="metadata.type",
                        match=qdrant_client.models.MatchValue(value="image"),
                        # match=qdrant_client.models.MatchValue(value="text"),
                    ),
                    qdrant_client.models.FieldCondition(
                        key="metadata.page_number",
                        match=qdrant_client.models.MatchAny(any=list(pages_of_fetched_chunks)),
                    )
                ]
            ),
        )

        response = {
            "status_code": 200,
            "message": "success",
            # "chunks": [result.payload for result in results.points],
            # "chunks": smaller_chunks,
            "chunks": [result.payload for result in results],
            # "chunks": results,
        }
        logging.info(f"Returning {len(results)} page chunks out of the original smaller chunks of {len(pages_of_fetched_chunks)}")
        # logging.info(f"No of chunks retrieved: {len(results.points)}")
        return response
        
    
    except Exception as e:
        logging.exception(f"Error retrieving chunks: {e}")
        return  {
            "status_code" : 500,
            "message" : "failed", 
        }
        

def retrieve_chunks_sync(
            user_query: str = "" ,
            file_id_list : List[str] = [], 
            top_k: int = 10, 
            page_list: List[int] = [] , 
            statement_type : List[str] = [], 
            is_financial_statement : str = None,
            notes : str = None,
            core_statements : str = None
            ) -> Dict[str, Any]:
    """
    Asynchronously retrieves chunks from the RAG vector store and uses OpenAI to respond.

    Args:
        query (str): The user query.
        collection_name (str): The name of the collection to query.

    Returns:
        Dict[str, Any]: The retrieved chunks and response.
    """
    try:
        
        
        
        logging.info(f"top k : {top_k}, Page_number : {page_list}, statement_type : {statement_type}, is_financial_statement : {is_financial_statement}, notes : {notes}, core_statements : {core_statements}")
        client = connect_qdrant()
        vectorstore = QdrantVectorStore(
            client=client,
            collection_name=collection_name,
            embedding=embeddings,
        )
        
        logging.info(f"file id list : {file_id_list}")
        
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
        
        if page_list:
            filter_condition.append(
                qdrant_client.models.FieldCondition(
                        key="metadata.page_number",
                        match=qdrant_client.models.MatchAny(any=page_list),
                    ))
            
        if statement_type:
            filter_condition.append(
                qdrant_client.models.FieldCondition(
                        key="metadata.statement_type",
                        match=qdrant_client.models.MatchAny(any=statement_type),
                    ))
            
        if is_financial_statement:
            filter_condition.append(
                qdrant_client.models.FieldCondition(
                        key="metadata.is_financial_statement",
                        match=qdrant_client.models.MatchValue(value=is_financial_statement.value()),
                    ))
            
        if notes:
            filter_condition.append(
                qdrant_client.models.FieldCondition(
                        key="metadata.notes",
                        match=qdrant_client.models.MatchValue(value=notes),
                    ))
            
        if core_statements:
            filter_condition.append(
                qdrant_client.models.FieldCondition(
                        key="metadata.core_statements",
                        match=qdrant_client.models.MatchValue(value=core_statements),
                    ))
            
        results = vectorstore.similarity_search(
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
