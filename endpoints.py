import json
import logging
import os
import uuid
import asyncio
import time
import concurrent.futures

from datetime import datetime
from fastapi import APIRouter
from pydantic import BaseModel
from fastapi import Body, HTTPException
from fastapi import APIRouter , HTTPException, status
from fastapi.responses import JSONResponse, StreamingResponse
from typing import List, Dict,Optional, Literal

# from agents.rag_agent import doc_agents_chat,doc_agents_chat_stream
from agents.expense_agent import expense_agents_stream
from agents.revenue_agent import revenue_agents_stream
from agents.comparative_agent import comparative_agents_stream
from agents.summary_agent import summary_agents_stream
from agents.general_agent import general_agents_stream

from utils.s3_function import get_presigned_urls_from_s3,get_files_from_s3_in_base64_for_file,get_files_from_s3_in_base64
from knowledge_base.agentic_chunking import get_advance_chunk
from knowledge_base.rag_functions import create_rag
from dotenv import load_dotenv
from utils.postgres_connection import ConnectDB
from knowledge_base.update_vdb_s3 import delete_file_and_update_db

from functions.testing_multiagents import agentic_flow
from functions.router_llm_call import get_router_response



load_dotenv()

router = APIRouter()

class ChatResponse(BaseModel):
    query : str
    user_id : str
    ticket_id : str
    query_id : str
    file_id_list : List[str]
    stream : bool = False
    
    
class CreateTicket(BaseModel):
    query : str
    
class DeleteFileRequest(BaseModel):
    file_id: str
    thread_id: str
    
class GeneralChat(BaseModel):
    query : str
    user_id : str
    ticket_id : str
    
    
class FileRequest(BaseModel):
    fileName: str
    fileType: str

class MultiFileRequest(BaseModel):
    user_id: str
    files: List[FileRequest]
    thread_id: str
    file_id: str | None = None
    folder_name : str
    
class PDFRequest(BaseModel):
    user_id : str
    thread_id : str
    upload_type : str = "file" 
    file_id_list : Optional[List[str]] = None 
    
    
    
cluster_id = os.getenv("QDRANT_COLLECTION")


async def combined_stream(agent_streams):
    for idx, stream_func in enumerate(agent_streams):
        # Add a horizontal rule between agents (but not before the first one)
        if idx > 0:
            yield "\n\n---\n\n"

        async for chunk in stream_func:
            yield chunk

@router.post("/chat")
async def get_chat_response(chat_response: ChatResponse):
    selected_agent_list = get_router_response(user_query=chat_response.query)  
    # Example: [{"agent": "revenue_analyst", "prompt": "Provide detailed revenue analysis"}, ...]

    logging.info(f"Selected Agents : {selected_agent_list}")
    agent_streams = []
    selected_agent_list = json.loads(selected_agent_list)

    for agent_info in list(selected_agent_list):
        logging.info(f"Agent Name: {agent_info}")
        agent_name = agent_info["agent"]
        agent_prompt = agent_info["prompt"]

        if not agent_name or not agent_prompt:
            logging.warning(f"Invalid agent info: {agent_info}")
            continue

        logging.info(f"Triggered {agent_name} with prompt: {agent_prompt}")

        if agent_name == "revenue_analyst":
            agent_streams.append(revenue_agents_stream(
                query=agent_prompt,
                user_id=chat_response.user_id,
                thread_id=chat_response.ticket_id,
                query_id=chat_response.query_id,
                file_id_list=chat_response.file_id_list
            ))

        elif agent_name == "expense_analyst":
            agent_streams.append(expense_agents_stream(
                query=agent_prompt,
                user_id=chat_response.user_id,
                thread_id=chat_response.ticket_id,
                query_id=chat_response.query_id,
                file_id_list=chat_response.file_id_list
            ))

        elif agent_name == "comparative_analysis":
            agent_streams.append(comparative_agents_stream(
                query=agent_prompt,
                user_id=chat_response.user_id,
                thread_id=chat_response.ticket_id,
                query_id=chat_response.query_id,
                file_id_list=chat_response.file_id_list
            ))

        elif agent_name == "summary_agent":
            agent_streams.append(summary_agents_stream(
                query=agent_prompt,
                user_id=chat_response.user_id,
                thread_id=chat_response.ticket_id,
                query_id=chat_response.query_id,
                file_id_list=chat_response.file_id_list
            ))

        elif agent_name == "general_agent":
            agent_streams.append(general_agents_stream(
                query=agent_prompt,
                user_id=chat_response.user_id,
                thread_id=chat_response.ticket_id,
                query_id=chat_response.query_id,
                file_id_list=chat_response.file_id_list
            ))

    if not agent_streams:
        return {"error": "No valid agents found"}

    return StreamingResponse(combined_stream(agent_streams), media_type="text/event-stream")

    
    # router_llm_call = ""
    
    # if chat_response.stream:
    #     return StreamingResponse(
    #         doc_agents_chat_stream(
    #             query=str(chat_response.query),
    #             user_id=str(chat_response.user_id),
    #             file_id_list= chat_response.file_id_list,
    #             thread_id=str(chat_response.ticket_id), 
    #             query_id=str(chat_response.query_id)),
    #         media_type="text/event-stream"
    #         )
    # else :
    #     response = await doc_agents_chat(query=chat_response.query, user_id= chat_response.user_id, thread_id= chat_response.ticket_id, query_id=chat_response.query_id, file_id_list = chat_response.file_id_list)
    #     logging.info(response)
    
    #     return response
    # query = chat_response.query
    # file_id_list = chat_response.file_id_list
    
    # initial_state = {
    # "query": query,
    # "context": {"file_id_list": file_id_list },  
    # "retrieval_results": [],
    # "agent_outcomes": {},
    # "current_agent": "router",
    # "final_response": ""
    # }   
    
    # result = agentic_flow.invoke(initial_state)
    # return result


@router.post("/get-presigned-urls")
async def get_presigned_urls(multi_file_request: MultiFileRequest):
    
    thread_id = multi_file_request.thread_id  #if exists then should be given from API gateway
    # user_id = str(uuid.uuid4()) #for testing purpose
    user_id = multi_file_request.user_id  #should be given from API gateway
    folder_name = multi_file_request.folder_name
    try:
        db = ConnectDB()
        urls = []
        for file in multi_file_request.files:
            file_name = f"{user_id}/{thread_id}/{file.fileName}"
            url = get_presigned_urls_from_s3(user_id,file,thread_id)
            urls.append(url)
            
            sql_query = [
                {
                    "query": """
                            INSERT INTO public.user_s3_mapping (
                                id, user_id, file_name, file_type, s3_file_url, created_at, cluster_id, thread_id, file_id, folder_name
                            ) VALUES (
                                gen_random_uuid(), %s, %s, %s, %s, CURRENT_TIMESTAMP, %s, %s, %s, %s
                            );
                            """,
                    "data": (str(user_id),file_name,file.fileType,url["file_url"],str(cluster_id),str(thread_id),str(url["file_id"]), str(folder_name))
                }
            ] 
            db.insert(sql_query)
        
        db.close_connection()
        
        return {
                "status_code" : 200, 
                "urls": urls, 
                "cluster_id": cluster_id,
                "thread_id": thread_id,
               }
        
    except Exception as e:
        logging.error(f"Error processing files: {e}")
        raise HTTPException(
            status_code=500,
            detail={
                "status_code": 500,
                "detail": "An internal server error occurred",
            }
        )

@router.get("/get-files-and-folders")
async def get_files():
    query = """Select split_part(file_name, '/', array_length(string_to_array(file_name, '/'), 1)) AS file_name, s3_file_url, file_id, thread_id, folder_name, rag_status from user_s3_mapping where deleted_at is NULL"""
    db =ConnectDB()
    try:
        response = db.fetch(query=query)
        
        return response
        
        
    except Exception as e:
        return {
             "status_code" : 500,
             "error" : e
         }
        
    finally : 
        db.close_connection()
        
@router.get("/get-final-files")
async def get_final_files():
    query = """Select file_name, s3_file_url, file_id, thread_id, folder_name, rag_status from user_s3_mapping where deleted_at is NULL and rag_status is true;"""
    db = ConnectDB()
    try:
        response = db.fetch(query=query)
        
        return response
        
    except Exception as e:
        return {
             "status_code" : 500,
             "error" : e
         }
        
    finally : 
        db.close_connection()
    


@router.post("/create-knowledge-base")
async def extract_pdf_text(pdf_data: PDFRequest):
    """
    Endpoint to extract text from multiple base64 encoded PDF files and create RAG for the document.
    
    Returns:
        dict: Processing results with appropriate HTTP status code
    
    Raises:
        JSONResponse: When processing fails with error details
    """
    start_time = time.time()
    request_id = str(uuid.uuid4())
    user_id = pdf_data.user_id
    
    try:
        if pdf_data.upload_type == "file":
            files_dict = get_files_from_s3_in_base64_for_file(
                user_id=user_id,
                cluster_id=cluster_id,
                thread_id=pdf_data.thread_id,
                file_id_list=pdf_data.file_id_list
            )
            logging.info("Created RAG for upload_type : File")
        else:
            files_dict = get_files_from_s3_in_base64(
                user_id=user_id,
                cluster_id=cluster_id,
                thread_id=pdf_data.thread_id
            )
            logging.info("Created RAG for upload_type : Thread")

        if not files_dict:
            return JSONResponse(
                status_code=status.HTTP_404_NOT_FOUND,
                content={
                    "status_code": status.HTTP_404_NOT_FOUND,
                    "request_id": request_id,
                    "message": "No files found for processing",
                    "status": "failed"
                }
            )

        logging.info(f"Processing {len(files_dict)} files - Request ID: {request_id}")
        
        def process_single_file(filename, base64_str, thread_id, file_id, extension, file_type):
            try:
                logging.info(f"thread_id: {thread_id}, file_id: {file_id}")
                summaries = get_advance_chunk(
                    base64_str=base64_str,
                    file_name=filename,
                    thread_id=thread_id,
                    file_id=file_id,
                    file_type=file_type,
                    extension=extension
                )  
                rag_result = create_rag(summaries["overall_summary"], thread_id=thread_id) 
                
                db = ConnectDB()
                update_query = [{
                    "query" : """UPDATE public.user_s3_mapping
                                SET rag_status = TRUE
                                WHERE thread_id = %s
                                AND file_id = %s;""",
                    "data" : (str(thread_id), str(file_id))
                }]
                
                db_response = db.update(update_query)
                
                
                return {
                    "status_code": status.HTTP_200_OK,
                    "filename": filename,
                    "overall_summary": summaries["overall_summary"],
                    "chunk_summaries": summaries.get("chunk_summaries", []),
                    "rag_result": rag_result,
                    "status": "success"
                }
            except Exception as e:
                logging.error(f"Error processing file {filename} - Request ID: {request_id} - {str(e)}")
                return {
                    "status_code": status.HTTP_500_INTERNAL_SERVER_ERROR,
                    "file_id": file_id,
                    "error_message": str(e),
                    "status": "failed"
                }
            
            finally :
                db.close_connection()
        
        with concurrent.futures.ThreadPoolExecutor() as executor:
            futures = [
                executor.submit(
                    process_single_file,
                    items["file_name"],
                    items["base64_str"],
                    items["thread_id"],
                    items["file_id"],
                    items["extension"],
                    items["file_type"]
                )
                for items in files_dict
            ]
            results = [future.result() for future in concurrent.futures.as_completed(futures)]
        
        successful_results = [result for result in results if result["status"] == "success"]
        errors = [result for result in results if result["status"] == "failed"]
        
        # Determine appropriate status code based on results
        if not successful_results and errors:
            response_status_code = status.HTTP_500_INTERNAL_SERVER_ERROR
        elif errors:
            response_status_code = status.HTTP_207_MULTI_STATUS
        else:
            response_status_code = status.HTTP_200_OK
            
        response = {
            "status_code": response_status_code,
            "request_id": request_id,
            "total_files": len(files_dict),
            "successful_files": len(successful_results),
            "failed_files": len(errors),
            "status": "success" if not errors else "partial_success" if successful_results else "failed",
            "errors": errors if errors else None,
        }
        
        logging.info(
            f"Request completed - ID: {request_id} - "
            f"Processed: {len(successful_results)}/{len(files_dict)} files - "
            f"Processing time: {time.time() - start_time:.2f} seconds"
        )
        
        # Return JSONResponse for complete failure
        if response_status_code == status.HTTP_500_INTERNAL_SERVER_ERROR:
            return JSONResponse(
                status_code=response_status_code,
                content=response
            )
            
        return response

    except Exception as e:
        error_message = f"Failed to process request - {str(e)}"
        logging.error(f"{error_message} - Request ID: {request_id}")
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={
                "status_code": status.HTTP_500_INTERNAL_SERVER_ERROR,
                "request_id": request_id,
                "message": error_message,
                "status": "failed"
            }
        )


@router.post("/delete-file")
async def delete_file(delete_file_request: DeleteFileRequest):
    """
    Deletes a file from the S3 bucket.
    """
    
    if not delete_file_request.file_id or not delete_file_request.thread_id:
        return {
            "status": 400,
            "response": "file_id and thread_id are required"
        }
    
    if not delete_file_request.file_id or not delete_file_request.thread_id:
        return {
            "status": 400,
            "response": "file_id and thread_id are required"
        }

    response = delete_file_and_update_db(file_id=delete_file_request.file_id, thread_id=delete_file_request.thread_id)
    
    if response["status_code"] == 200:
        logging.info(f"File deleted successfully with file_id: {delete_file_request.file_id}")
        return {
            "status": 200,
            "response": "File deleted successfully"
        }
    else:
        logging.error(f"Error deleting file")
        return {
            "status": 500,
            "response": "Error deleting file"
        }