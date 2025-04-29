import boto3
import logging
import os
import base64
import uuid

from pathlib import Path
from typing import List, Dict, Any, Optional
from botocore.exceptions import BotoCoreError
from fastapi import HTTPException
from dotenv import load_dotenv
from utils.postgres_connection import ConnectDB

load_dotenv()

AWS_ACCESS_KEY = os.getenv("AWS_ACCESS_KEY_ID")
AWS_SECRET_KEY = os.getenv("AWS_SECRET_ACCESS_KEY")
S3_BUCKET = os.getenv("S3_BUCKET_NAME")
S3_REGION = os.getenv("AWS_DEFAULT_REGION")

# Validate AWS configuration
if not AWS_ACCESS_KEY or not AWS_SECRET_KEY or not S3_BUCKET or not S3_REGION:
    logging.error("Missing AWS configuration in environment variables.")
    raise ValueError("AWS configuration is not properly set. Check your .env file.")

def get_s3_client():
    """
    Initialize and return a boto3 S3 client.
    """
    try:
        s3_client = boto3.client(
            "s3",
            aws_access_key_id=AWS_ACCESS_KEY,
            aws_secret_access_key=AWS_SECRET_KEY,
            region_name=S3_REGION,
        )
        logging.info("S3 client initialized successfully.")
        return s3_client
    except BotoCoreError as e:
        logging.error(f"Error initializing S3 client: {e}")
        raise RuntimeError("Failed to initialize S3 client.")
    

def get_presigned_urls_from_s3(user_id: str, file: Any, thread_id: str) -> Dict[str, str]:
    """
    Generate a presigned URL and file URL for an S3 object.

    Args:
        user_id (str): The ID of the user.
        file (Any): Object containing `fileName` and `fileType` attributes.

    Returns:
        Dict[str, str]: Dictionary with presigned URL, file URL, and file key.

    Raises:
        HTTPException: For invalid input or S3 errors.
    """
    if not hasattr(file, "fileName") or not hasattr(file, "fileType"):
        logging.error("Invalid file object. Missing 'fileName' or 'fileType' attributes.")
        raise HTTPException(
            status_code=400,
            detail="Invalid file object. 'fileName' and 'fileType' are required."
        )

    try:
        s3_client = get_s3_client()
        file_name = f"{user_id}/{thread_id}/{file.fileName}"
        file_id = uuid.uuid4()
        presigned_url = s3_client.generate_presigned_url(
            "put_object",
            Params={
                "Bucket": S3_BUCKET,
                "Key": file_name,
                "ContentType": file.fileType,
            },
            ExpiresIn=3600,  # this is URL expiration time in seconds (It will expire irrespective the content is uploaded or not)
        )

        file_url = f"https://{S3_BUCKET}.s3.{S3_REGION}.amazonaws.com/{file_name}"

        logging.info(f"Generated presigned URL and file URL for {file.fileName}.")
        return { 
                "presigned_url": presigned_url, 
                "file_url": file_url, 
                "file_key": file_name,
                "file_id" : file_id}


    except BotoCoreError as e:
        logging.error(f"Error generating presigned URL: {e}")
        raise HTTPException(status_code=500, detail="Error generating presigned URL.")

    except Exception as e:
        logging.error(f"Unexpected error generating presigned URL: {e}")
        raise HTTPException(status_code=500, detail="Unexpected error occurred.")


def list_s3_items() -> List[Dict[str, Any]]:
    """
    List all items available in the configured S3 bucket.

    Returns:
        List[Dict[str, Any]]: List of items in the bucket with metadata.

    Raises:
        HTTPException: For S3 operation failures.
    """
    try:
        s3_client = get_s3_client()
        response = s3_client.list_objects_v2(Bucket=S3_BUCKET)

        if "Contents" not in response:
            logging.info("Bucket is empty.")
            return []

        items = [
            {
                "Key": item["Key"],
                "LastModified": item["LastModified"].isoformat(),
                "Size": item["Size"],
                "StorageClass": item["StorageClass"]
            }
            for item in response["Contents"]
        ]

        logging.info(f"Retrieved {len(items)} items from S3 bucket '{S3_BUCKET}'.")
        return items

    except BotoCoreError as e:
        logging.error(f"Error listing items in S3 bucket: {e}")
        raise HTTPException(status_code=500, detail="Error listing items in S3 bucket.")

    except Exception as e:
        logging.error(f"Unexpected error while listing S3 items: {e}")
        raise HTTPException(status_code=500, detail="Unexpected error occurred.")


def delete_file_from_s3(file_key: str) -> Dict[str, str]:
    """
    Delete a specific file from the S3 bucket.

    Args:
        file_key (str): The key (path) of the file to delete in the S3 bucket.

    Returns:
        Dict[str, str]: Success message if deletion is successful.

    Raises:
        HTTPException: For S3 operation failures.
    """
    try:
        s3_client = get_s3_client()
        response = s3_client.delete_object(Bucket=S3_BUCKET, Key=file_key)

        if response.get("ResponseMetadata", {}).get("HTTPStatusCode") == 204:
            logging.info(f"File '{file_key}' deleted successfully from bucket '{S3_BUCKET}'.")
            return {"message": f"File '{file_key}' deleted successfully.", "status" : "success"}
        else:
            logging.error(f"Failed to delete file '{file_key}' from bucket '{S3_BUCKET}'.")
            raise HTTPException(
                status_code=500, detail=f"Failed to delete file '{file_key}' from S3."
            )

    except BotoCoreError as e:
        logging.error(f"Error deleting file from S3: {e}")
        raise HTTPException(status_code=500, detail="Error deleting file from S3.")

    except Exception as e:
        logging.error(f"Unexpected error while deleting file from S3: {e}")
        raise HTTPException(status_code=500, detail="Unexpected error occurred.")


def convert_pdf_list_to_base64_from_s3(file_data: List[Dict[str, str]]) -> List[Dict[str, str]]:
    """
    Convert PDF files from an S3 bucket to Base64 encoded strings and return the updated list.

    Args:
        file_data (List[Dict[str, str]]): List of dictionaries containing file details.

    Returns:
        List[Dict[str, str]]: The updated list with Base64 encoded strings added.
    """
    for file in file_data:
        file_name = file.get("file_name")
        
        if file_name:
            try:
                s3_client = get_s3_client()
                response = s3_client.get_object(Bucket=S3_BUCKET, Key=file_name)
                file_content = response["Body"].read()
                base64_encoded = base64.b64encode(file_content).decode("utf-8")
                file["base64_str"] = base64_encoded  # Add Base64 to the dictionary
                
            except Exception as e:
                logging.error(f"Error converting file '{file_name}' to Base64: {e}")
                file["base64"] = f"Error: {str(e)}"
    
    return file_data

def convert_files_to_base64_from_s3(file_data: List[Dict[str, str]]) -> List[Dict[str, str]]:
    """
    Convert various file types from an S3 bucket to Base64 encoded strings.
    Supports PDF, DOCX, PPT, PPTX, and other common file formats.

    Args:
        file_data (List[Dict[str, str]]): List of dictionaries containing file details.

    Returns:
        List[Dict[str, str]]: The updated list with Base64 encoded strings and file types added.
    """
    # List of supported file extensions
    SUPPORTED_EXTENSIONS = {
        '.pdf': 'application/pdf',
        '.docx': 'application/vnd.openxmlformats-officedocument.wordprocessingml.document',
        '.doc': 'application/msword',
        '.ppt': 'application/vnd.ms-powerpoint',
        '.pptx': 'application/vnd.openxmlformats-officedocument.presentationml.presentation'
    }

    for file in file_data:
        file_name = file.get("file_name")
        
        if not file_name:
            continue

        # Get file extension
        file_extension = Path(file_name).suffix.lower()
        
        # Check if file type is supported
        if file_extension not in SUPPORTED_EXTENSIONS:
            logging.warning(f"Unsupported file type for '{file_name}'")
            file["error"] = "Unsupported file type"
            continue

        try:
            # Get file from S3
            s3_client = get_s3_client()
            response = s3_client.get_object(Bucket=S3_BUCKET, Key=file_name)
            file_content = response["Body"].read()
            
            # Convert to base64
            base64_encoded = base64.b64encode(file_content).decode("utf-8")
            
            # Update the dictionary with file information
            file.update({
                "base64_str": base64_encoded,
                "file_type": SUPPORTED_EXTENSIONS[file_extension],
                "extension": file_extension[1:]  # Remove the leading dot
            })
            
            logging.info(f"Successfully converted {file_name} to base64")
            
        except Exception as e:
            error_message = f"Error converting file '{file_name}' to Base64: {str(e)}"
            logging.error(error_message)
            file.update({
                "error": error_message,
                "extension": file_extension[1:] if file_extension else "unknown"
            })
            
    # logging.info(f"file_data: {file_data}")
    return file_data


def get_files_from_s3_in_base64(user_id: str, cluster_id : str ,thread_id : str) -> Dict[str, str]:
    """
    Retrieve Base64-encoded PDF files from S3 based on user and cluster IDs.

    Args:
        user_id (str): The user ID.
        cluster_id (Optional[str]): The cluster ID.

    Returns:
        Dict[str, str]: A dictionary with file names as keys and Base64 strings as values.
    """
    
    try:
        db = ConnectDB()

        query = f"""
        SELECT file_name, thread_id, file_id, file_type FROM user_s3_mapping 
        WHERE cluster_id = '{cluster_id}' AND user_id = '{user_id}' AND thread_id = '{thread_id}' AND deleted_at IS NULL;
        """
        db_response = db.fetch(query)
        # file_names = [item["file_name"] for item in db_response.get("data", [])]
        
        json_response = [
            {
                "file_name": item["file_name"],
                "thread_id": item["thread_id"],
                "file_id": item["file_id"],
                "file_type" : item["file_type"]  
            }
            for item in db_response.get("data", [])
        ]
        
        # base64_files_dict = convert_pdf_list_to_base64_from_s3(json_response)
        base64_files_dict = convert_files_to_base64_from_s3(json_response)
        logging.info(f"Converted files to Base64")
        
        return base64_files_dict
    
    finally:
        db.close_connection()
    

def get_files_from_s3_in_base64_for_file(user_id: str, cluster_id : str ,thread_id : str, file_id_list : List ) -> Dict[str, str]:
    """
    Retrieve Base64-encoded PDF files from S3 based on user and cluster IDs.

    Args:
        user_id (str): The user ID.
        cluster_id (Optional[str]): The cluster ID.

    Returns:
        Dict[str, str]: A dictionary with file names as keys and Base64 strings as values.
    """
    
    try:
        db = ConnectDB()
        file_id_filter = ", ".join(f"'{file_id}'" for file_id in file_id_list)

        query = f"""
        SELECT file_name, thread_id, file_id, file_type FROM user_s3_mapping 
        WHERE cluster_id = '{cluster_id}' 
        AND user_id = '{user_id}' 
        AND thread_id = '{thread_id}' 
        AND file_id IN ({file_id_filter}) 
        AND deleted_at IS NULL;
        """
        db_response = db.fetch(query)
        # file_names = [item["file_name"] for item in db_response.get("data", [])]
        
        json_response = [
            {
                "file_name": item["file_name"],
                "thread_id": item["thread_id"],
                "file_id": item["file_id"],
                "file_type" : item["file_type"]  
            }
            for item in db_response.get("data", [])
        ]
        
        # base64_files_dict = convert_pdf_list_to_base64_from_s3(json_response)
        base64_files_dict = convert_files_to_base64_from_s3(json_response)
        logging.info(f"Converted files to Base64")
        
        return base64_files_dict
    
    finally:
        db.close_connection()
