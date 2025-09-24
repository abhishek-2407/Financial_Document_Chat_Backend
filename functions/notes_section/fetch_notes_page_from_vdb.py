
from functions.query_rag import retrieve_chunks
from typing import List
import logging
import re
import ast

def _notes_regex(notes_number: str) -> re.Pattern:
    """
    Build a regex that matches the exact notes number with boundaries:
    - Prevents matching inside a larger number or alphanumeric token (e.g., 16, 6A).
    - Allows separators after the number like '.', ')', ':', ' ', '-' etc.
    Examples:
      notes_number="6"   -> matches '6', '6.', '6)', '6:','6 -', '6.1' (allowed), but NOT '16' or '6A'
      notes_number="3A"  -> matches '3A', '3A.', '3A)' etc., but NOT '13A' or '3AB'
    """
    nn = re.escape(str(notes_number).strip())
    pattern = rf"(?<!\d){nn}(?![\dA-Za-z])"
    return re.compile(pattern, flags=re.IGNORECASE)



async def get_notes_chunks(
    notes_number: str,
    statement_type: str = None,
    file_id_list: List = None
):
    logging.info(f"notes_number : {notes_number}, statement_type : {statement_type}, file_id_list : {file_id_list}")
    get_chunks = await retrieve_chunks(
        file_id_list=file_id_list,
        page_list=[0],
        is_financial_statement="Yes"
    )

    result = []

    
    notes_pat = _notes_regex(notes_number)

    for chunk in get_chunks.get("chunks", []):
        page_content = getattr(chunk, "page_content", None)
        if not page_content:
            continue

        try:
            content_list = ast.literal_eval(page_content)
        except Exception as e:
            logging.warning(f"Failed to parse page_content with ast.literal_eval: {e}")
            continue

        for entry in content_list:
            if statement_type and entry.get("statement_type") != statement_type:
                continue

            heading = (entry.get("heading") or "").lower()
            subheading = entry.get("subheading") or ""
            notes = entry.get("notes").lower()

            if (("notes" in heading) or notes == "yes") and notes_pat.search(subheading):
                result.append(entry)

                
    logging.info(f"Extracted the Pages with mentioned notes section : {result}")
    
    page_number_list = [item["page_number"] for item in result]
    logging.info(f"Page_list for mentioned notes section : {page_number_list}")

    get_final_chunks = await retrieve_chunks(page_list=page_number_list, file_id_list=file_id_list)
    
    page_content = [item.page_content for item in get_final_chunks["chunks"]]

    return get_final_chunks




    

# get_notes_page_number(notes_number="3A",file_id_list=["1499f9f5-1c7e-4d20-8af4-eae4303ba36d"])