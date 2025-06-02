import os
import asyncio
import base64
import io
import PyPDF2
import logging
import json
import threading
import uuid
from pathlib import Path

from dotenv import load_dotenv
from typing import Optional, List, Dict, Any
from langchain_openai import OpenAI, AzureOpenAIEmbeddings, AzureChatOpenAI
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import StrOutputParser
from langchain_chroma import Chroma
from langchain_core.documents import Document
from utils.postgres_connection import ConnectDB

from fastapi import HTTPException

# Load environment variables
load_dotenv()

model = AzureChatOpenAI(model="gpt-4o",
                            api_key=os.getenv("AZURE_OPENAI_API_KEY"),
                            azure_endpoint=os.getenv("AZURE_OPENAI_ENDPOINT"),
                            api_version=os.getenv("AZURE_OPENAI_VERSION"),
                            max_tokens=4000)

# Local database path
LOCAL_DB_PATH = os.getenv("LOCAL_VECTOR_DB_PATH", "./local_vector_db")
collection_name = os.getenv("CHROMA_COLLECTION", "document_collection")

def connect_chroma():
    """Initialize local Chroma vector database"""
    try:
        # Ensure the directory exists
        Path(LOCAL_DB_PATH).mkdir(parents=True, exist_ok=True)
        
        vectorstore = Chroma(
            collection_name=collection_name,
            embedding_function=embeddings,
            persist_directory=LOCAL_DB_PATH
        )
        
        logging.info("Local Chroma database connected successfully.")
        return vectorstore
    except Exception as e:
        logging.error(f"Failed to connect to local Chroma database: {e}")
        raise HTTPException(status_code=500, detail="Failed to connect to local vector database.")

embeddings = AzureOpenAIEmbeddings(
            model="text-embedding-3-small",
            api_key=os.getenv("AZURE_OPENAI_API_KEY"),
            azure_endpoint=os.getenv("AZURE_OPENAI_ENDPOINT"),
            api_version=os.getenv("AZURE_OPENAI_VERSION"),
            dimensions=768,
        )

# PDF Utilities (unchanged)
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

# Text Splitter (unchanged)
def split_documents(data: str) -> List[Document]:
    """
    Splits the given text into smaller chunks using recursive splitting.

    Args:
        data (str): The input text to split.

    Returns:
        List[Document]: List of document chunks.
    """
    text_splitter = RecursiveCharacterTextSplitter(
        chunk_size=400,
        separators=["\n", "\n\n", ".", ":"],
    )
    return text_splitter.create_documents([data])

def check_and_create_collection(collection_name: str = None):
    """Initialize or reset the local collection"""
    try:
        vectorstore = connect_chroma()
        # Chroma automatically handles collection creation
        logging.info(f"Collection '{collection_name or 'default'}' initialized in local database")
        return vectorstore
    except Exception as e:
        logging.error(f"Failed to initialize collection: {e}")
        raise

# RAG Utilities
def create_rag(chunked_data: List[Document], thread_id: str) -> Dict[str, str]:
    """
    Creates a RAG (Retrieval-Augmented Generation) vector store with the chunked data.

    Args:
        chunked_data (List[Document]): List of document chunks.
        thread_id (str): Thread identifier for organizing documents.

    Returns:
        Dict[str, str]: Status and collection name of the created vector store.
    """
    try:
        vectorstore = connect_chroma()
        
        # Add thread_id to metadata for all documents
        for doc in chunked_data:
            if not doc.metadata:
                doc.metadata = {}
            doc.metadata['thread_id'] = thread_id
        
        # Add documents to the local vector store
        vectorstore.add_documents(chunked_data)
        
        logging.info(f"Local vector store updated for thread_id: {thread_id}")
        return {"collection_name": collection_name, "vectorstore_status": "created"}
    except Exception as e:
        logging.exception(f"Failed to create vector store: {e}")
        return {"collection_name": collection_name, "vectorstore_status": "failed"}

async def retrieve_chunks(user_query: str, file_id_list: List[str], query_id: str, top_k: int = 10) -> Dict[str, Any]:
    """
    Asynchronously retrieves chunks from the local vector store.

    Args:
        user_query (str): The user query.
        file_id_list (List[str]): List of file IDs to filter by.
        query_id (str): Query identifier for logging.
        top_k (int): Number of chunks to retrieve.

    Returns:
        Dict[str, Any]: The retrieved chunks and response.
    """
    try:
        logging.info(f"top k: {top_k}")
        
        vectorstore = connect_chroma()
        
        # Build filter conditions for metadata
        filter_conditions = {}
        
        # Add file_id filter if provided
        if file_id_list:
            filter_conditions["file_id"] = {"$in": file_id_list}
        
        # Perform similarity search with filters
        results = await asyncio.to_thread(
            vectorstore.similarity_search,
            user_query,
            k=top_k,
            filter=filter_conditions if filter_conditions else None
        )
        
        response = {
            "status_code": 200,
            "message": "success",
            "chunks": results,
        }
        
        return response
        
    except Exception as e:
        logging.exception(f"Error retrieving chunks: {e}")
        return {
            "status_code": 500,
            "message": "failed", 
        }
        
        
async def log_query_results(query_id: str, user_query: str, page_list: List[str], 
                           file_id_list: List[str], thread_id: str, top_k: int = 5):
    """Handles logging query results in the background."""
    try:
        db = ConnectDB()
        logging.info(f"top k: {top_k} and page_list: {page_list}")
        
        vectorstore = connect_chroma()
        
        # Build filter conditions
        filter_conditions = {
            "thread_id": thread_id,
            "type": "text"
        }
        
        if file_id_list:
            filter_conditions["file_id"] = {"$in": file_id_list}
            
        if page_list:
            filter_conditions["page_number"] = {"$in": page_list}
        
        # Perform similarity search
        results = await asyncio.to_thread(
            vectorstore.similarity_search,
            user_query,
            k=top_k,
            filter=filter_conditions
        )

        # Convert results to JSON for logging
        chunks_data_json = json.dumps([{
            "page_content": doc.page_content,
            "metadata": doc.metadata
        } for doc in results])
        
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

def delete_documents_from_collection(file_id: str, thread_id: str):
    """
    Delete documents from the local collection based on file_id and thread_id.
    
    Args:
        file_id (str): The file ID to delete.
        thread_id (str): The thread ID to delete.
        
    Returns:
        Dict[str, str]: Status of the deletion operation.
    """
    try:
        vectorstore = connect_chroma()
        
        # Get all documents to find ones matching our criteria
        # Note: Chroma's delete method works differently than Qdrant
        all_docs = vectorstore.get()
        
        # Find document IDs that match our criteria
        ids_to_delete = []
        for i, metadata in enumerate(all_docs['metadatas']):
            if (metadata.get('file_id') == file_id and 
                metadata.get('thread_id') == thread_id):
                ids_to_delete.append(all_docs['ids'][i])
        
        if ids_to_delete:
            vectorstore.delete(ids=ids_to_delete)
            logging.info(f"Deleted {len(ids_to_delete)} documents for file_id: {file_id} and thread_id: {thread_id}")
        else:
            logging.info(f"No documents found for file_id: {file_id} and thread_id: {thread_id}")
        
        return {"status": "success", "message": "Documents deleted successfully"}
        
    except Exception as e:
        logging.exception(f"Error deleting documents: {e}")
        return {"status": "error", "message": "Failed to delete documents"}

# Additional utility functions for local database management
def get_collection_stats() -> Dict[str, Any]:
    """Get statistics about the local collection."""
    try:
        vectorstore = connect_chroma()
        collection_data = vectorstore.get()
        
        return {
            "total_documents": len(collection_data['ids']),
            "collection_name": collection_name,
            "database_path": LOCAL_DB_PATH,
            "status": "active"
        }
    except Exception as e:
        logging.error(f"Error getting collection stats: {e}")
        return {"status": "error", "message": str(e)}

def backup_local_database(backup_path: str = None) -> Dict[str, str]:
    """Create a backup of the local vector database."""
    try:
        import shutil
        
        if not backup_path:
            backup_path = f"{LOCAL_DB_PATH}_backup_{int(asyncio.get_event_loop().time())}"
        
        shutil.copytree(LOCAL_DB_PATH, backup_path)
        
        logging.info(f"Database backed up to: {backup_path}")
        return {"status": "success", "backup_path": backup_path}
    except Exception as e:
        logging.error(f"Error creating backup: {e}")
        return {"status": "error", "message": str(e)}