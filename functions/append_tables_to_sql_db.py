

from functions.query_rag import retrieve_chunks,retrieve_chunks_sync
from pydantic import BaseModel, Field
from typing import List, Dict, Any, Literal, Tuple
from langchain_openai import AzureChatOpenAI,ChatOpenAI
import os 
from dotenv import load_dotenv
from utils.llm_calling import call_openai
import json
import uuid
import psycopg2
from utils.postgres_connection import ConnectDB
import logging

load_dotenv()

consolidated_user_query = ["balance sheet", "cash flow statement", "profit and loss" ]

standalone_user_query = [ "balance sheet", "cash flow statement", "profit and loss"]


def fetch_consolidated_chunks(query: str, file_id_list):
    
    user_query = f"consolidated {query}"

    chunks = retrieve_chunks_sync(
        user_query=user_query, 
        file_id_list=file_id_list, 
        top_k=15, 
        statement_type=["consolidated", "both"], 
        is_financial_statement="Yes", 
        notes=None, 
        core_statements="Yes")
    
    # logging.info(f"chunks : {chunks}\n")
    
    class CheckResponse(BaseModel):
        successful_match: Literal["Yes", "No"] = Field(
            description=(
                f"Indicates whether the document is a consolidated {query}."
                "✅ Mark 'Yes' only if:"
                "- The file match found to be same."
                "- Before marking must check properly"
                f"❌ Do NOT mark 'Yes' if {query} words appear casually in running text, table or footnotes."
            )
        )      
    
    # Initialize the LLM model outside the loop for efficiency
    json_model = AzureChatOpenAI(
        model="gpt-4o",
        api_key=os.getenv("AZURE_OPENAI_API_KEY"),
        azure_endpoint=os.getenv("AZURE_OPENAI_ENDPOINT"),
        api_version=os.getenv("AZURE_OPENAI_VERSION"),
        max_tokens=1000
    ).with_structured_output(CheckResponse)
    
    matched_chunks = []
    # Find the first matching chunk
    for chunk in chunks["chunks"]:
        # print(f"chunkks start : {chunk} : chunks end")
        json_model_output = json_model.invoke(chunk.page_content)

        if json_model_output.successful_match == "Yes":
            # logging.info(chunk)
            matched_chunks.append(chunk)  # Return the chunk directly

    return matched_chunks

def fetch_standalone_chunks(query: str, file_id_list):
    
    user_query = f"standalone {query}"
    chunks = retrieve_chunks_sync(
        user_query=user_query, 
        file_id_list=file_id_list, 
        top_k=15, 
        statement_type=["standalone", "both"], 
        core_statements="Yes",
        is_financial_statement="Yes"
    )
    
    class CheckResponse(BaseModel):
        successful_match: Literal["Yes", "No"] = Field(
            description=(
                f"Indicates whether the document is a Standalone {query}."
                "✅ Mark 'Yes' only if:"
                "- The file match found to be same."
                "- Before marking must check properly"
                f"❌ Do NOT mark 'Yes' if {query} words appear casually in running text, table or footnotes."
            )
        )      
    
    # Initialize the LLM model outside the loop for efficiency
    json_model = AzureChatOpenAI(
        model="gpt-4o-mini",
        api_key=os.getenv("AZURE_OPENAI_API_KEY"),
        azure_endpoint=os.getenv("AZURE_OPENAI_ENDPOINT"),
        api_version=os.getenv("AZURE_OPENAI_VERSION"),
        max_tokens=1000
    ).with_structured_output(CheckResponse)
    
    matched_chunks = []
    # Find the first matching chunk
    for chunk in chunks["chunks"]:
        json_model_output = json_model.invoke(chunk.page_content)
        
        # Fixed: Check successful_match instead of core_statements
        if json_model_output.successful_match == "Yes":
            # logging.info(chunk)
            matched_chunks.append(chunk)
            # return chunk  # Return the chunk directly
    
    # If no matching chunk found
    return matched_chunks


def extract_table_data(chunk_text):
    """Extract table data from chunk text using OpenAI"""
    
    system_prompt = """
You are a json creator, extract the data out of the tables.

Go through the whole markdown chunk, from the table Fetch whole content.
You must provide the whole table content here.

Priority Instructions:
**Must Extract all the data from the table.
**Extract all the line items from the table.(Priority)
**Extract Line Items from Multiple Tables also.
**Provide in Json format only

Do NO MISS any information from Table.

Response Format:
This is the json format for your response.
[
{
    'particulars' : 'Each Line Items',
    'year_and_values' : [ {
        'year': 2024' in this format only, 'values' : 'actual value', (Numeric)}, so on
        ]'
    'notes' : 'notes number if mentioned',
}
]
"""
    
    user_prompt = f"Data : {chunk_text}"
    
    print("🔄 Initiated extraction")
    try:
        raw_response = call_openai(
            system_prompt=system_prompt,
            user_prompt=user_prompt,
            model='gpt-4o'
        )
        
        print("✅ Extracted Response")
        cleaned = raw_response.strip().replace("```json", "").replace("```", "").strip()
        data = json.loads(cleaned)
        print("✅ Data loaded successfully")
        return data
        
    except json.JSONDecodeError as e:
        print(f"❌ JSON parsing error: {e}")
        return None
    except Exception as e:
        print(f"❌ Extraction error: {e}")
        return None


def safe_float(val):
    """Convert string to float safely, return None if invalid"""
    if not val:
        return None
    
    # Handle string values
    if isinstance(val, str):
        val = val.replace(",", "").replace("(", "-").replace(")", "").strip()
    
    try:
        return float(val)
    except (ValueError, TypeError):
        return None

def insert_balance_sheet_items(data, company_name, data_type, file_id, table_name):
    """Insert balance sheet items into database"""
    try:
                
        db = ConnectDB()

        inserted_count = 0
        for item in data:
            try:
                # Validate required fields
                if not item.get("particulars") or not item.get("year_and_values"):
                    print(f"⚠️ Skipping item with missing particulars or year: {item}")
                    continue
                
                sql_query = [
                {
                    "query": """
                            INSERT INTO financial_statements (id, company_name, particulars, year_and_values, notes, data_type, file_id, table_name)
                            VALUES (%s, %s, %s, %s, %s, %s, %s, %s);
                            """,
                    "data": (str(uuid.uuid4()),
                    company_name,
                    item.get("particulars"),
                    json.dumps(item.get("year_and_values")),
                    # safe_float(item.get("values")),
                    item.get("notes") if item.get("notes") else None,
                    data_type,
                    file_id,
                    table_name)
                }
            ] 
                db.insert(sql_query)
                
                inserted_count += 1
                
            except Exception as e:
                print(f"⚠️ Error inserting item {item}: {e}")
                continue

        db.close_connection()
        
        print(f"✅ Data inserted successfully! {inserted_count} items inserted.")
        return True
        
    except Exception as e:
        print(f"❌ Database error: {e}")
        return False
    
def process_consolidated_data(query: str, file_id_list, company_name: str, data_type: str = "consolidated"):
    """Main function to process consolidated chunks and insert into database"""
    
    matching_chunk = fetch_consolidated_chunks(query, file_id_list)

    if  len(matching_chunk) < 1:
        print(matching_chunk)
        print(f"❌ No matching consolidated {query} found")
        return False
    
    data = extract_table_data(matching_chunk)
    
    if not data:
        print("❌ No data extracted from the chunk")
        return False
    
    success = insert_balance_sheet_items(data, company_name, data_type=data_type, file_id = file_id_list[0], table_name=query)
    return success


def process_standalone_data(query: str, file_id_list, company_name: str, data_type: str = "standalone"):
    """Main function to process consolidated chunks and insert into database"""
    
    matching_chunk = fetch_standalone_chunks(query, file_id_list)

    if  len(matching_chunk) < 1:
        print(f"❌ No matching standalone {query} found")
        return False
    
    data = extract_table_data(matching_chunk)
    
    if not data:
        print("❌ No data extracted from the chunk")
        return False
    
    success = insert_balance_sheet_items(data, company_name, data_type=data_type, file_id = file_id_list[0], table_name=query)
    return success
    
    
