import asyncio
from concurrent.futures import ThreadPoolExecutor, as_completed
from functions.query_rag import retrieve_chunks, retrieve_chunks_sync
from pydantic import BaseModel, Field
from typing import List, Dict, Any, Literal, Tuple
from langchain_openai import AzureChatOpenAI
import os
from dotenv import load_dotenv
from utils.llm_calling import call_openai, call_openai_async
import json
import uuid
import logging
from utils.postgres_connection import ConnectDB

load_dotenv()

consolidated_user_query = ["balance sheet", "cash flow statement", "profit and loss"]
standalone_user_query = ["balance sheet", "cash flow statement", "profit and loss"]

async def fetch_consolidated_chunks(query: str, file_id_list):
    user_query = f"consolidated {query}"

    chunks = await retrieve_chunks(
        user_query=user_query,
        file_id_list=file_id_list,
        top_k=15,
        statement_type=["consolidated", "both"],
        is_financial_statement="Yes",
        core_statements="Yes"
    )

    class CheckResponse(BaseModel):
        successful_match: Literal["Yes", "No"] = Field(
            description=(
                f"Indicates whether the document is a consolidated {query}."
                "✅ Mark 'Yes' only if:"
                f"- (allow variations like 'Consolidated {query} (contd.)', 'Consolidated {query} – continued')."
                "- The file match found to be same."
                "- Before marking must check properly"
                f"❌ Do NOT mark 'Yes' if {query} words appear casually in running text, table or footnotes."
                f"❌ Do NOT mark 'Yes' if Notes of {query} is found in heading section."
            )
        )

    json_model = AzureChatOpenAI(
        model="gpt-4o",
        api_key=os.getenv("AZURE_OPENAI_API_KEY"),
        azure_endpoint=os.getenv("AZURE_OPENAI_ENDPOINT"),
        api_version=os.getenv("AZURE_OPENAI_VERSION"),
        max_tokens=1000
    ).with_structured_output(CheckResponse)

    async def check_chunk(chunk):
        json_model_output = await json_model.ainvoke(chunk.page_content)
        if json_model_output.successful_match == "Yes":
            return chunk
        return None

    # Run all chunk checks concurrently
    results = await asyncio.gather(*[check_chunk(chunk) for chunk in chunks["chunks"]])

    matched_chunks = [res for res in results if res is not None]
    logging.info(f"Total chunks used : {len(matched_chunks)}")

    return matched_chunks


async def fetch_standalone_chunks(query: str, file_id_list):
    user_query = f"standalone {query}"

    chunks = await retrieve_chunks(
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
                f"- (allow variations like 'Standalone {query} (contd.)', 'Standalone {query} – continued')."
                "- The file match found to be same."
                "- Before marking must check properly"
                f"❌ Do NOT mark 'Yes' if {query} words appear casually in running text, table or footnotes."
                f"❌ Do NOT mark 'Yes' if Notes of {query} is found in heading section."
            )
        )      

    json_model = AzureChatOpenAI(
        model="gpt-4o-mini",
        api_key=os.getenv("AZURE_OPENAI_API_KEY"),
        azure_endpoint=os.getenv("AZURE_OPENAI_ENDPOINT"),
        api_version=os.getenv("AZURE_OPENAI_VERSION"),
        max_tokens=1000
    ).with_structured_output(CheckResponse)

    async def check_chunk(chunk):
        json_model_output = await json_model.ainvoke(chunk.page_content)
        if json_model_output.successful_match == "Yes":
            return chunk
        return None

    results = await asyncio.gather(*[check_chunk(chunk) for chunk in chunks["chunks"]])
    matched_chunks = [res for res in results if res is not None]

    logging.info(f"Total chunks used : {len(matched_chunks)}")
    return matched_chunks

async def extract_table_data(chunk_text):
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

    **Ignore the rows if no particulars name is mentioned.

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
    
    try:
        raw_response = await call_openai_async(
            system_prompt=system_prompt,
            user_prompt=user_prompt,
            model='gpt-4o'
        )
        
        cleaned = raw_response.strip().replace("```json", "").replace("```", "").strip()
        data = json.loads(cleaned)
        return data
        
    except json.JSONDecodeError as e:
        print(f"❌ JSON parsing error: {e}")
        return None
    except Exception as e:
        print(f"❌ Extraction error: {e}")
        return None

def safe_float(val):
    if not val:
        return None
    
    if isinstance(val, str):
        val = val.replace(",", "").replace("(", "-").replace(")", "").strip()
    
    try:
        return float(val)
    except (ValueError, TypeError):
        return None

def insert_balance_sheet_items(data, company_name, data_type, file_id, table_name):
    try:
        db = ConnectDB()
        inserted_count = 0
        for item in data:
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
                             item.get("notes") if item.get("notes") else None,
                             data_type,
                             file_id,
                             table_name)
                }
            ] 
            db.insert(sql_query)
            inserted_count += 1
                
        db.close_connection()
        print(f"✅ Data inserted successfully! {inserted_count} items inserted.")
        return True
        
    except Exception as e:
        print(f"❌ Database error: {e}")
        return False

async def process_consolidated_data(query: str, file_id_list, company_name: str, data_type: str = "consolidated"):
    matching_chunk = await fetch_consolidated_chunks(query, file_id_list)
    if not matching_chunk:
        print(f"❌ No matching consolidated {query} found")
        return False

    # Concurrently extract table data
    extracted_results = await asyncio.gather(
        *[extract_table_data(chunk) for chunk in matching_chunk]
    )

    # Filter out None or empty results
    data = [d for d in extracted_results if d]

    if not data:
        print("❌ No data extracted from the chunk")
        return False

    # Process extracted data sequentially (or make this async too if needed)
    for d in data:
        success = insert_balance_sheet_items(
            d, company_name, data_type=data_type, file_id=file_id_list[0], table_name=query
        )
        if not success:
            return False

    return True

async def process_standalone_data(query: str, file_id_list, company_name: str, data_type: str = "standalone"):
    matching_chunk = await fetch_standalone_chunks(query, file_id_list)
    if not matching_chunk:
        print(f"❌ No matching standalone {query} found")
        return False

    # Concurrently extract table data
    extracted_results = await asyncio.gather(
        *[extract_table_data(chunk.page_content) for chunk in matching_chunk]
    )

    # Filter valid results
    data = [d for d in extracted_results if d]

    if not data:
        print("❌ No data extracted from the chunk")
        return False

    for d in data:
        success = insert_balance_sheet_items(
            d, company_name, data_type=data_type, file_id=file_id_list[0], table_name=query
        )
        if not success:
            return False

    return True

