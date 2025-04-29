
import logging

from botocore.exceptions import ClientError
from typing import Dict, Any

from utils.postgres_connection import ConnectDB
from utils.s3_function import delete_file_from_s3
from knowledge_base.rag_functions import delete_documents_from_collection
from utils.custom_exceptions import VectorDBError, S3Error, DatabaseError, FileOperationError


def delete_file_and_update_db(file_id: str, thread_id: str) -> Dict[str, str]:
    """
    Delete a file from S3 , Vector database
    
    Args:
        file_id (str): The unique identifier of the file
        thread_id (str): The thread identifier associated with the file
        
    Returns:
        Dict[str, str]: Status of the operation with detailed messages
        
    Raises:
        FileOperationError: If the operation fails at any stage
    """
    logger = logging.getLogger(__name__)
    db = None
    operation_status = {
        "status_code": 500,
        "status": "failed",
        "message": "",
        "details": {}
    }

    try:
        if not all([file_id, thread_id]):
            raise ValueError("file_id and thread_id cannot be empty")
            
        file_id = str(file_id).strip()
        thread_id = str(thread_id).strip()
        
        db = ConnectDB()
    
        # Update database
        update_query = [{
            "query": """UPDATE user_s3_mapping
                    SET deleted_at = NOW()  
                    WHERE thread_id = %s
                    AND file_id = %s;""",
            "data": (thread_id, file_id)
        }]
        
        db_update_response = db.update(update_query)
        if not db_update_response.get("status") == "success":
            raise DatabaseError("Failed to update deletion timestamp")
            
        # Fetch file name
        fetch_query = f"""SELECT file_name 
                        FROM user_s3_mapping 
                        WHERE thread_id = '{thread_id}' 
                        AND file_id = '{file_id}';"""
        db_response = db.fetch(fetch_query)
        
        if not db_response.get("data"):
            raise FileOperationError("File not found in database")
            
        file_name = db_response["data"][0]["file_name"]
        
        # Delete from vector database
        try:
            vector_db_response = delete_documents_from_collection(file_id, thread_id)
            logging.info(vector_db_response)
            if not vector_db_response["status"] == "success":
                raise VectorDBError("Failed to delete from vector database")
                
        except VectorDBError as e:
            logger.error(f"Vector DB deletion failed: {str(e)}")
            raise FileOperationError(f"Vector DB deletion failed: {str(e)}")
            
        # Delete from S3
        try:
            s3_response = delete_file_from_s3(file_name)
            if not s3_response["status"] == "success":
                raise S3Error("Failed to delete from S3")
                
        except (ClientError, S3Error) as e:
            logger.error(f"S3 deletion failed: {str(e)}")
            raise FileOperationError(f"S3 deletion failed: {str(e)}")
            
        
        operation_status.update({
            "status_code": 200,
            "status": "success",
            "message": "File deleted successfully",
            "details": {
                "file_name": file_name,
                "file_id": file_id,
                "thread_id": thread_id,
            }
        })
        
    
        
    except ValueError as e:
        logger.error(f"Input validation error: {str(e)}")
        operation_status["message"] = f"Invalid input: {str(e)}"
        
    except DatabaseError as e:
        logger.error(f"Database error: {str(e)}")
        operation_status["message"] = f"Database operation failed: {str(e)}"
        
    except FileOperationError as e:
        logger.error(f"File operation error: {str(e)}")
        operation_status["message"] = str(e)
        
    except Exception as e:
        logger.error(f"Unexpected error: {str(e)}")
        operation_status["message"] = "An unexpected error occurred"
        
    finally:
        if db:
            try:
                db.close_connection()
            except Exception as e:
                logger.error(f"Error closing database connection: {str(e)}")
                
        if operation_status["status"] == "success":
            logger.info(f"File deletion completed successfully: {operation_status}")
        else:
            logger.error(f"File deletion failed: {operation_status}")
            
    return operation_status
    
    
    