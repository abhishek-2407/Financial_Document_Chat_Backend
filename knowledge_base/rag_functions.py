import os
import openai
import qdrant_client
import asyncio
import base64
import io
import PyPDF2
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
from utils.postgres_connection import ConnectDB



from fastapi import HTTPException
import qdrant_client.models

# Load environment variables
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
            size=768, 
            distance=qdrant_client.http.models.Distance.COSINE
            )
        
        logging.info("Qdrant client connected successfully.")
        return client
    except Exception as e:
        logging.error(f"Failed to connect to Qdrant: {e}")
        raise HTTPException(status_code=500, detail="Failed to connect to Qdrant.")


embeddings = AzureOpenAIEmbeddings(
            model="text-embedding-3-small",
            api_key=os.getenv("AZURE_OPENAI_API_KEY"),
            azure_endpoint=os.getenv("AZURE_OPENAI_ENDPOINT"),
            api_version=os.getenv("AZURE_OPENAI_VERSION"),
            dimensions=768,
        )

from typing import List
import numpy as np
from langchain_core.embeddings import Embeddings


# PDF Utilities
def extract_text_from_base64_pdf(base64_string: str) -> str:
    """
    Decodes a base64 string, extracts text from the PDF, and returns the text.

    Args:
        base64_string (str): The base64-encoded string of a PDF.

    Returns:
        str: The extracted text from the PDF.

    Raises:
        HTTPException: If the base64 string is invalid or text extraction fails.
    """
    try:
        pdf_bytes = base64.b64decode(base64_string)
        pdf_file = io.BytesIO(pdf_bytes)
        pdf_reader = PyPDF2.PdfReader(pdf_file)

        text = ""
        for page in pdf_reader.pages:
            text += page.extract_text() + "\n"

        return text.strip()
    except base64.binascii.Error:
        raise HTTPException(status_code=400, detail="Invalid base64 string")
    except Exception as e:
        logging.exception(f"Error processing PDF: {e}")
        raise HTTPException(status_code=500, detail=f"Error processing PDF: {str(e)}")

def process_multiple_pdfs(files: List[str], filenames: Optional[List[str]] = None) -> List[Dict[str, Any]]:
    """
    Processes multiple base64-encoded PDFs and extracts text from each.

    Args:
        files (List[str]): List of base64-encoded PDF strings.
        filenames (List[str], optional): List of corresponding filenames.

    Returns:
        List[Dict[str, Any]]: A list of dictionaries containing results for each file.
    """
    results = []
    if not filenames:
        filenames = [f"file_{i+1}.pdf" for i in range(len(files))]
    elif len(filenames) < len(files):
        filenames.extend([f"file_{i+1}.pdf" for i in range(len(filenames), len(files))])

    for i, (file_content, filename) in enumerate(zip(files, filenames)):
        try:
            extracted_text = extract_text_from_base64_pdf(file_content)
            results.append({
                "file_index": i,
                "filename": filename,
                "status": "success",
                "text": extracted_text,
                "text_length": len(extracted_text),
            })
        except Exception as e:
            logging.error(f"Error processing file '{filename}': {e}")
            results.append({
                "file_index": i,
                "filename": filename,
                "status": "error",
                "error": str(e),
            })

    return results

# Text Splitter
def split_documents(data: str) -> List[Dict[str, Any]]:
    """
    Splits the given text into smaller chunks using recursive splitting.

    Args:
        data (str): The input text to split.

    Returns:
        List[Dict[str, Any]]: List of text chunks.
    """
    text_splitter = RecursiveCharacterTextSplitter(
        chunk_size=400,
        separators=["\n", "\n\n", ".", ":"],
    )
    return text_splitter.create_documents([data])


def check_and_create_collection(collection_name:str, size: int = 1536):
    client = connect_qdrant()
    if client.get_collection(collection_name = collection_name):
            client.delete_collection(collection_name = collection_name)
    
    collection_config = qdrant_client.http.models.VectorParams(
            size=size, 
            distance=qdrant_client.http.models.Distance.COSINE
            )
    client.create_collection(
            collection_name=collection_name,
            vectors_config=collection_config
        )
    
# RAG Utilities
def create_rag(chunked_data: List[Dict[str, Any]], thread_id: str) -> Dict[str, str]:
    """
    Creates a RAG (Retrieval-Augmented Generation) vector store with the chunked data in batches of 15.

    Args:
        chunked_data (List[Dict[str, Any]]): List of document chunks.
        thread_id (str): Unique thread identifier.

    Returns:
        Dict[str, str]: Status and collection name of the created vector store.
    """
    try:
        client = connect_qdrant()
        client.update_collection(collection_name=collection_name, timeout=120)

        logging.info(f"Starting to add documents to collection: {collection_name} in batches")

        vectorstore = QdrantVectorStore(
            client=client,
            collection_name=collection_name,
            embedding=embeddings,
        )

        # Process in batches of 15
        batch_size = 20
        for i in range(0, len(chunked_data), batch_size):
            batch = chunked_data[i:i + batch_size]
            vectorstore.add_documents(batch)
            logging.info(f"Added batch {i//batch_size + 1} with {len(batch)} documents")

        logging.info(f"Vector store created for collection: {collection_name} and thread_id: {thread_id}")
        return {"collection_name": collection_name, "vectorstore_status": "created"}

    except Exception as e:
        logging.exception(f"Failed to create vector store: {e}")
        return {"collection_name": collection_name, "vectorstore_status": "failed"}


async def retrieve_chunks(user_query: str, thread_id : str ,file_id_list : List[str],query_id : str, page_list: List[str] = [] , top_k: int = 4) -> Dict[str, Any]:
    """
    Asynchronously retrieves chunks from the RAG vector store and uses OpenAI to respond.

    Args:
        query (str): The user query.
        collection_name (str): The name of the collection to query.

    Returns:
        Dict[str, Any]: The retrieved chunks and response.
    """
    try:
        
        threading.Thread(
            target=start_background_logging,
            args=(query_id, user_query, thread_id, page_list, file_id_list),
            daemon=True  
        ).start()
        
        
        logging.info(f"top k : {top_k} and page_list : {page_list}")
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
                    qdrant_client.models.FieldCondition(
                        key="metadata.thread_id",
                        match=qdrant_client.models.MatchValue(value=thread_id),
                    ),
                    qdrant_client.models.FieldCondition(
                        key="metadata.type",
                        match=qdrant_client.models.MatchValue(value="image"),
                    ),
                       
                ]
        
        if page_list:
            filter_condition.append(
                qdrant_client.models.FieldCondition(
                        key="metadata.page_number",
                        match=qdrant_client.models.MatchAny(any=page_list),
                    ))
        
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

        return response
        
    
    except Exception as e:
        logging.exception(f"Error retrieving chunks: {e}")
        return  {
            "status_code" : 500,
            "message" : "failed", 
        }
        
async def log_query_results(query_id:str, user_query:str, page_list:List[str], file_id_list: List[str], thread_id: str, top_k:int = 5):
    """Handles logging query results in the background."""
    try:
        db = ConnectDB()
        logging.info(f"top k : {top_k} and page_list : {page_list}")
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
                    qdrant_client.models.FieldCondition(
                        key="metadata.thread_id",
                        match=qdrant_client.models.MatchValue(value=thread_id),
                    ),
                    qdrant_client.models.FieldCondition(
                        key="metadata.type",
                        match=qdrant_client.models.MatchValue(value="text"),
                    ),
                       
                ]
        
        if page_list:
            filter_condition.append(
                qdrant_client.models.FieldCondition(
                        key="metadata.page_number",
                        match=qdrant_client.models.MatchAny(any=page_list),
                    ))
        
        results = await vectorstore.asimilarity_search(
            user_query,
            k=top_k,
            filter=qdrant_client.models.Filter(must=filter_condition),
        )

        
        chunks_data_json = json.dumps([vars(doc) for doc in results])
        logging_query = [
            {
                "query": """
                    INSERT INTO doc_chat_query_logs (
                        id, query_id, status, module, chunks_data, user_query, created_at
                    ) VALUES (
                        gen_random_uuid(), %s, %s, %s, %s::jsonb, %s, CURRENT_TIMESTAMP
                    );
                """,
                "data": (str(query_id), "success", "doc_chat", chunks_data_json, user_query),
            }
        ]
        await asyncio.to_thread(db.insert, logging_query)

    except Exception as e:
        logging.error(f"Logging error: {e}")

    finally:
        db.close_connection()
        
        
def start_background_logging(query_id, user_query, thread_id, page_list, file_id_list):
    """Helper function to start the async logging function in a separate thread."""
    
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    
    try:
        loop.run_until_complete(
            log_query_results(
                query_id=query_id,
                user_query=user_query,
                thread_id=thread_id,
                page_list=page_list,
                file_id_list=file_id_list,
            )
        )
    except Exception as e:
        logging.error(f"Error in background logging thread: {e}")
    finally:
        loop.close()
    


def delete_documents_from_collection(file_id: str, thread_id:str) :
    try:
        client = connect_qdrant()
        delete_response = client.delete(
            collection_name = collection_name,
            points_selector = qdrant_client.models.FilterSelector(
                filter=qdrant_client.models.Filter(
                    must=[
                        qdrant_client.models.FieldCondition(
                            key="metadata.file_id",
                            match=qdrant_client.models.MatchValue(value=file_id),
                        ),
                        qdrant_client.models.FieldCondition(
                            key="metadata.thread_id",
                            match=qdrant_client.models.MatchValue(value=thread_id),
                        ),
                    ],
                )
            ),
        )
        logging.info(f"Delete response: {delete_response}")
        logging.info(f"Documents deleted successfully for file_id: {file_id} and thread_id: {thread_id}")
        
        return {"status": "success", "message": "Documents deleted successfully"}
        
    
    except Exception as e:
        logging.exception(f"Error deleting documents: {e}")
        return {"status": "error", "message": "Failed to delete documents"}
    
