import os
import textwrap
import uuid
import io
import json
import logging
import time
import base64
import tempfile
import re
import subprocess
import fitz
import concurrent.futures
from typing import List, Dict, Any, Literal, Tuple
from google.genai.types import Content, GenerateContentConfig, GenerationConfig, ThinkingConfig, SafetySetting, HarmCategory, HarmBlockThreshold, Part
import numpy as np
import cv2

from io import BytesIO
from dotenv import load_dotenv  
from langchain_openai import AzureChatOpenAI,ChatOpenAI
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import StrOutputParser
from langchain.schema.document import Document
from langchain.text_splitter import RecursiveCharacterTextSplitter
from PIL import Image
from pydantic import BaseModel, Field
from rich.progress import BarColumn, MofNCompleteColumn, Progress, SpinnerColumn, TextColumn, TimeElapsedColumn, TimeRemainingColumn
from vertexai.generative_models import GenerativeModel
import vertexai
from utils.llm_calling import google_genai_client

from pdf2image import convert_from_bytes
# from IPython.display import Image, display
from knowledge_base.vision_prompt import vision_prompt_template_v2


load_dotenv()

os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = os.getenv("GOOGLE_APPLICATION_CREDENTIALS", "abg-pulse-oab-a5c1d2b4817c.json")
os.environ["VERTEXAI_PROJECT_ID"] = os.getenv("VERTEXAI_PROJECT_ID", "abg-pulse-oab")
vertexai.init(project="abg-pulse-oab")



def save_overall_summary(overall_summary, file_path="overall_summary.json"):
    indexed_summary = [{"index": idx, **item.metadata, "content": item.page_content} for idx, item in enumerate(overall_summary)]
    
    # Write to a JSON file
    with open(file_path, "w") as json_file:
        json.dump(indexed_summary, json_file, indent=4)

def base64_to_file_object(base64_str: str) -> io.BytesIO:
    """
    Converts a base64-encoded file into a file-like object.

    Parameters
    ----------
    base64_str : str
        The base64-encoded string representing the file.

    Returns
    -------
    io.BytesIO
        A file-like object that can be passed to functions expecting a file in bytes.
    """
    file_bytes = base64.b64decode(base64_str)
    file_obj = io.BytesIO(file_bytes)
    return file_obj

def split_pdf_to_image_base64_pages(base64_pdf: str, file_type: str, extension: str) -> list:
    """
    Splits a base64 PDF into individual pages, converts each page to an image,
    and encodes each image as a base64 string.
    
    Args:
        base64_pdf (str): Base64 encoded PDF string.
    
    Returns:
        list: List of base64 encoded strings for images of each PDF page.
    """
    pdf_data = base64.b64decode(base64_pdf)    
    images = convert_from_bytes(pdf_data)
    pages_base64 = []
    
    for image in images:
        image_stream = BytesIO()
        image.save(image_stream, format='PNG')  # Save as PNG for better compatibility
        image_stream.seek(0)
        image_base64 = base64.b64encode(image_stream.read()).decode('utf-8')
        pages_base64.append(image_base64)
    
    return pages_base64

def split_document_to_image_base64_pages(base64_doc: str, file_type :str, extension : str) -> list:
    """
    Splits a base64 encoded document (PDF, DOCX, PPT) into individual pages,
    converts each page to an image, and encodes each image as a base64 string.
    
    Args:
        base64_doc (str): Base64 encoded document string.
    
    Returns:
        list: List of base64 encoded strings for images of each document page.
    """
    # Decode base64 to bytes
    doc_bytes = base64.b64decode(base64_doc)
        
    pages_base64 = []
    try:
        if file_type == 'application/pdf':
            pages_base64 = _convert_pdf_to_images(doc_bytes)
                
   
        # elif file_type in ['application/vnd.openxmlformats-officedocument.presentationml.presentation',
        #                   'application/vnd.ms-powerpoint']:
        #     # Handle PPTX/PPT files
        #     pages_base64 = _convert_powerpoint_to_images(doc_bytes)            
        else:
            raise ValueError(f"Unsupported file type: {file_type}")
            
    except Exception as e:
        raise Exception(f"Error processing document: {str(e)}")
        
    return pages_base64

def _convert_pdf_to_images(pdf_bytes: bytes, dpi: int = 200, max_workers: int = 50) -> List[str]:
    """Convert PDF pages to images."""
    
    def process_page(page):
        """
        Convert a single PDF page to a base64 encoded image
        
        Args:
            page: PyMuPDF page object
        
        Returns:
            str: Base64 encoded image
        """
        # Render page with PyMuPDF (much faster than convert_from_bytes)
        pix = page.get_pixmap(matrix=fitz.Matrix(dpi/72, dpi/72))
        
        img_array = np.frombuffer(pix.samples, dtype=np.uint8).reshape(pix.height, pix.width, pix.n)
        
        if pix.n == 4:  # RGBA
            img_array = cv2.cvtColor(img_array, cv2.COLOR_RGBA2RGB)
        
        pil_image = Image.fromarray(img_array)
        
        return _convert_image_to_base64(pil_image)
    
    doc = fitz.open(stream=pdf_bytes, filetype='pdf')
    
    with concurrent.futures.ThreadPoolExecutor(max_workers=max_workers) as executor:
        pages_base64 = list(executor.map(process_page, doc))
    
    return pages_base64

def _convert_image_to_base64(img: Image.Image, format: str = "PNG", optimize: bool = True, quality: int = 85) -> str:
    """Helper function to convert PIL Image to base64 string."""
    
    img_byte_arr = io.BytesIO()
    
    img.save(img_byte_arr, format=format, optimize=optimize, quality=quality)    
    img_byte_arr.seek(0)
    return base64.b64encode(img_byte_arr.getvalue()).decode("utf-8")



def extract_text_from_base64(base64_str: str, file_type: str, extension: str) -> list:
    """
    Extract text from a base64-encoded file (PDF or DOCX) and return a list of texts by page.
    
    Args:
        base64_str (str): Base64-encoded string of the file
        file_type (str): Type of the file (e.g., 'application/pdf', 'application/vnd.openxmlformats-officedocument.wordprocessingml.document')
        extension (str): File extension (e.g., 'pdf', 'docx')
        
    Returns:
        list: List of extracted text strings, one per page
    """
    
    file_bytes = base64.b64decode(base64_str)
    file_io = io.BytesIO(file_bytes)
    
    extracted_texts = []
    
    if file_type == 'application/pdf' or extension.lower() == 'pdf':
        from PyPDF2 import PdfReader
        
        pdf_reader = PdfReader(file_io)
        
        # Extract text page by page
        for page_num in range(len(pdf_reader.pages)):
            page = pdf_reader.pages[page_num]
            text = page.extract_text()
            extracted_texts.append(text)
    
    # Handle DOCX files
    
    else:
        # Unsupported file type
        extracted_texts.append(f"Unsupported file type: {file_type} with extension {extension}")
    
    return extracted_texts


def get_advance_chunk(base64_str: str, file_name: str, thread_id: str, file_id: str, file_type: str, extension: str) -> dict:
    start_time = time.time()
    # pdf_file = base64_to_file_object(base64_str)
    chunks_base64_list = split_document_to_image_base64_pages(base64_str, file_type, extension)
    logging.info(f"\nTime taken to split pdf to image: {time.time() - start_time}\n")

    # Extract text directly from PDF
    # try :
    #     extracted_texts = extract_text_from_base64(base64_str=base64_str, file_type=file_type, extension=extension)
    #     logging.info(f"Successfully extracted text from {len(extracted_texts)} pages")
        
    # except :
    #     logging.info("Error extracting text from document")

    images = chunks_base64_list

    model = AzureChatOpenAI(
        model="gpt-4o-mini",
        api_key=os.getenv("AZURE_OPENAI_API_KEY"),
        azure_endpoint=os.getenv("AZURE_OPENAI_ENDPOINT"),
        api_version=os.getenv("AZURE_OPENAI_VERSION"),
        max_tokens=4000
    )

    
    def process_single_image(image_data: Tuple[int, str]) -> Tuple[int, str]:
        """Process a single image and return its index and summary"""
        idx, image = image_data
        try:
            messages = [
                (
                    "user",
                    [
                        {"type": "text", "text": vision_prompt_template_v2},
                        {
                            "type": "image_url",
                            "image_url": {"url": f"data:image/jpeg;base64,{image}"},
                        },
                    ],
                )
            ]

            prompt = ChatPromptTemplate.from_messages(messages)
            chain = prompt | model | StrOutputParser()
            summary = chain.invoke({})
            logging.info(f"Successfully processed image {idx+1}/{len(images)}")
            return idx, summary
            
        except Exception as e:
            error_msg = f"Error processing image {idx+1}: {str(e)}"
            logging.error(error_msg)
            # Return error message as the summary for this image
            return idx, f"Error processing this image: {str(e)}"
    
    image_summaries = [None] * len(images)  
    
    # Create a list of (index, image) tuples for processing
    indexed_images = list(enumerate(images))
    
    with concurrent.futures.ThreadPoolExecutor(max_workers=50) as executor:
        future_to_image = {executor.submit(process_single_image, img_data): img_data for img_data in indexed_images}
        
        for future in concurrent.futures.as_completed(future_to_image):
            try:
                idx, summary = future.result()
                image_summaries[idx] = summary  
            except Exception as e:
                img_data = future_to_image[future]
                idx = img_data[0]
                logging.error(f"Unexpected error with image {idx+1}: {str(e)}")
                image_summaries[idx] = f"Unexpected error: {str(e)}"
    
    # Add image summaries
    img_ids = [str(uuid.uuid4()) for _ in images]
    summary_img = [
        Document(page_content=summary, 
                 metadata={
                     "doc_id": img_ids[i], 
                     "thread_id": thread_id, 
                     "file_id": file_id, 
                     "file_name": file_name,
                     "page_number": i + 1,
                     "type": "image"
                     }
                 ) for i, summary in enumerate(image_summaries)
    ]
    
    try:
        text_chunks = []
        # text_splitter = RecursiveCharacterTextSplitter(
        #     chunk_size=1000,
        #     chunk_overlap=100,
        #     length_function=len,
        #     separators=["\n\n", "\n", ". ", " ", ""]
        # )
        
        # for i, full_text in enumerate(extracted_texts):
        #     if not full_text:
        #         continue
            
        #     chunks = text_splitter.split_text(full_text)
            
        #     # Create a document for each chunk
        #     for j, chunk in enumerate(chunks):
        #         if not chunk.strip():
        #             continue
                    
        #         text_chunk_id = str(uuid.uuid4())
        #         text_chunks.append(
        #             Document(page_content=chunk.strip().replace("\n", ""),
        #                     metadata={
        #                         "doc_id": text_chunk_id,
        #                         "thread_id": thread_id,
        #                         "file_id": file_id,
        #                         "file_name": file_name,
        #                         "page_number": i + 1,
        #                         "chunk_number": j + 1,
        #                         "type": "text"
        #                     })
        #         )
                
        # overall_summary = summary_img + text_chunks
                
        overall_summary = summary_img
                
                
    except Exception as e:
        logging.info("Skipping text extraction")
        overall_summary = summary_img
    
    return {
        "overall_summary": overall_summary
    }
    
class ChunkMetadataStructure(BaseModel):
    headings: str = Field(
        description="""
Fetch the complete main heading of the page content.
Mention the multiple heading if exists.
Mention the main heading in one line only, Do not keep it in single word.

"""
    )
    
    sub_headings: str = Field(
        description="""
Fetch the complete sub-heading of the page content.
Mention the multiple sub-heading if exists.
Mention the sub-heading in short only.

"""
    )
    
    is_financial_statement: Literal["Yes", "No"] = Field(
        description="""
Return "Yes" if the page is part of the official financial statements package.
This includes ANY of the following, regardless of where they appear in the document:
- Core financial statements (Balance Sheet, Profit and Loss, Cash Flow, Changes in Equity, Financial Highlights with numbers),
- Notes to the Financial Statements (sections explicitly headed as Notes),
- Supplementary schedules that are presented as part of the financial statements.

Return "No" only if the page is outside the financial statements,
such as:
- introductory sections, management discussion and analysis (MD&A), corporate info,
- directors’ report, governance, sustainability, or other narrative-only content,
- appendices or miscellaneous text not labelled as part of the statements.
"""
    )
    is_financial_statement_reasoning: str = Field(description="Explain why you feel it is not a financial statment")
    statement_type: Literal["consolidated", "standalone", "both", "none"] = Field(
        description=(
            "Specifies the type of financial statement. "
            "'consolidated' for combined company statements, "
            "'standalone' for individual company statements, "
            "'both' if both types are present, "
            "'none' if not a financial statement."
        )
    )
    statement_type_reasoning: str = Field(description="Explain why you categorized the statement_type as you did")
    notes: Literal["Yes", "No"] = Field(
        description="""
Mark "Yes" ONLY if the FIRST heading (H1–H3, '#', '##', '###') inside or outside the <page> tags explicitly names a Notes section, e.g.:
- "NOTES – CONSOLIDATED FINANCIAL STATEMENTS"
- "Notes to the Financial Statements"
- "Explanatory Notes to the Accounts"

Mark "No" in ALL other cases, even if the body or tables mention notes 
(e.g., "Notes forming part of..." or "refer Note 1").
"""
)
    notes_reasoning: str = Field(description="Explain why you did or didn't categorize this as notes")
    core_statements: Literal["Yes", "No"] = Field(
    description="""
Return "Yes" ONLY if the page contains the actual financial statement itself
(Balance Sheet, P&L, Cash Flow, Changes in Equity, or officially titled Financial Highlights)

Return "No" if the page only contains:
- Notes forming part of financial statements
- Descriptions, introductions, corporate information
- Lists of subsidiaries, associates, or entities
- References to financial statements without showing them
- Any text without numeric tables of financial figures
- Subsidiary AOC-1, notes, policies, or annexures.
"""
)
    core_statements_reasoning: str = Field(description="Explain why you did or didn't categorize this as core statements")

def get_advance_chunk_gemini(base64_str: str, file_name: str, thread_id: str, file_id: str, file_type: str, extension: str) -> dict:
    start_time = time.time()
    # pdf_file = base64_to_file_object(base64_str)

    # === Split document into page images ===
    images = split_document_to_image_base64_pages(base64_str, file_type, extension)
    logging.info(f"\nTime taken to split pdf to image: {time.time() - start_time}\n")

    # Extract text directly from PDF
    # try :
    #     extracted_texts = extract_text_from_base64(base64_str=base64_str, file_type=file_type, extension=extension)
    #     logging.info(f"Successfully extracted text from {len(extracted_texts)} pages")
        
    # except :
    #     logging.info("Error extracting text from document")

    # model = AzureChatOpenAI(model="gpt-4o-mini",
    #                         api_key=os.getenv("AZURE_OPENAI_API_KEY"),
    #                         azure_endpoint=os.getenv("AZURE_OPENAI_ENDPOINT"),
    #                         api_version=os.getenv("AZURE_OPENAI_VERSION"),
    #                         max_tokens=4000)

    def process_single_image(image_data: Tuple[int, bytes]) -> Tuple[int, str]:
        """Process a single image and return its index and summary"""
        idx, image = image_data
        try:
            messages =  [
                Part.from_bytes(
                    data=image,  # Raw bytes, not base64
                    mime_type="image/jpeg",
                ),
                vision_prompt_template_v2,
            ]
            
            # MEDIA_ANALYSIS_MODEL = os.getenv("GOOGLE_VISION_MODEL", "gemini-1.5-pro")
            MEDIA_ANALYSIS_MODEL = "gemini-2.5-pro"

            response = google_genai_client.models.generate_content(
                model=MEDIA_ANALYSIS_MODEL,
                contents=messages,
                config=GenerateContentConfig(
                    temperature=0.3,
                    top_p=1.0,
                    top_k=1,
                    candidate_count=1,
                    max_output_tokens=8192,
                    # thinking_config=ThinkingConfig(
                    #     thinking_budget=0,
                    # ),
                ),
            )

            markdown_text = response.text.strip('```markdown').strip('```')

            json_model = google_genai_client.models.generate_content(
                model="gemini-2.5-flash-lite",
                contents=markdown_text,
                config=GenerateContentConfig(
                    response_mime_type="application/json",
                    response_schema=ChunkMetadataStructure,
                    temperature=0,
                    thinking_config=ThinkingConfig(
                        thinking_budget=0,
                    ),
                    # max_output_tokens=8192, # if output is too long try with this
                    safety_settings=[
                        SafetySetting(
                            category=HarmCategory.HARM_CATEGORY_HARASSMENT,
                            threshold=HarmBlockThreshold.BLOCK_NONE,
                        ),
                        SafetySetting(
                            category=HarmCategory.HARM_CATEGORY_HATE_SPEECH,
                            threshold=HarmBlockThreshold.BLOCK_NONE,
                        ),
                        SafetySetting(
                            category=HarmCategory.HARM_CATEGORY_SEXUALLY_EXPLICIT,
                            threshold=HarmBlockThreshold.BLOCK_NONE,
                        ),
                        SafetySetting(
                            category=HarmCategory.HARM_CATEGORY_DANGEROUS_CONTENT,
                            threshold=HarmBlockThreshold.BLOCK_NONE,
                        ),
                    ]
                ),
            )

            json_model_output = json_model.parsed
            
            # heading = json_model_output['headings']
            # logging.info(f"Headings : {heading}")
            final_meta_json =  json_model_output.model_dump() if json_model_output else {}
            result = {
                "page_data": markdown_text,
                **(json_model_output.model_dump() if json_model_output else {})
            }

            # prompt = ChatPromptTemplate.from_messages(messages)
            # chain = prompt | model | StrOutputParser()
            # summary = chain.invoke({})
            
            logging.info(f"Successfully processed image {idx+1}/{len(images)}")
            return idx, result, final_meta_json
            
        except Exception as e:
            error_msg = f"Error processing image {idx+1}: {str(e)}"
            logging.error(error_msg)
            # Return error message as the summary for this image
            return idx, f"Error processing this image: {str(e)}"
    
    image_summaries = [None] * len(images) 
    document_content_page = [None] * len(images) 
    
    # Create a list of (index, image) tuples for processing
    indexed_images = list(enumerate(images))
    
    with Progress(
        TextColumn("[progress.description]{task.description}"),
        BarColumn(),
        MofNCompleteColumn(),
        TimeRemainingColumn(),
        transient=False,
    ) as progress:

        overall_task = progress.add_task("Processing images...", total=len(indexed_images))

        # Secondary progress bar with spinners
        with Progress(
            SpinnerColumn(),
            TextColumn("{task.description}"),
            transient=True,
        ) as spinners:

            # Create spinner tasks per image
            spinner_tasks = {
                img_data[0]: spinners.add_task(
                    description=f"Image {img_data[0]}",
                    total=None
                )
                for img_data in indexed_images
            }

            # Submit and track futures
            with concurrent.futures.ThreadPoolExecutor(max_workers=50) as executor:
                future_to_idx = {
                    executor.submit(process_single_image, img_data): img_data[0]
                    for img_data in indexed_images
                }

                for future in concurrent.futures.as_completed(future_to_idx):
                    idx = future_to_idx[future]

                    try:
                        idx, summary, final_meta_data = future.result()

                        image_summaries[idx] = summary 
                        document_content_page[idx] = final_meta_data 

                    except Exception as e:
                        logging.error(f"Unexpected error with image {idx+1}: {str(e)}")
                        image_summaries[idx] = f"Unexpected error: {str(e)}"

                    # Hide spinner for this task
                    spinners.update(spinner_tasks[idx], completed=1, visible=False)
                    progress.advance(overall_task)


    logging.info("=== Processed all pages")
    
    # Add image summaries
    img_ids = [str(uuid.uuid4()) for _ in images]
    summary_img = [
        Document(page_content=summary["page_data"], 
                 metadata={
                     "doc_id": img_ids[i], 
                     "thread_id": thread_id, 
                     "file_id": file_id, 
                     "file_name": file_name,
                     "page_number": i + 1,
                     "type": "image",
                        **{k: v for k, v in summary.items() if k != "page_data"},

                    }
                 ) for i, summary in enumerate(image_summaries)
    ]
    
    logging.info(f'=== Meta data : {document_content_page}')
    
    
    simplified_list = [{"heading": item["headings"], "subheading": item["sub_headings"], "page_number": idx + 1} for idx, item in enumerate(document_content_page)]
    
    extracted_doc_content_page = [
        Document(page_content=f"{simplified_list}",
                 metadata={
                     "doc_id": 1234, 
                     "thread_id": thread_id, 
                     "file_id": file_id, 
                     "file_name": file_name,
                     "page_number": 0,
                     "type": "content_page",
                     "is_financial_statement" : "Yes"

                    })]
    
    summary_img.extend(extracted_doc_content_page)
    
    logging.info("=== Splitting chunks")
    try:
        text_chunks = []
        text_splitter = RecursiveCharacterTextSplitter(
            chunk_size=1000,
            chunk_overlap=100,
            length_function=len,
            separators=["\n\n", "\n", ". ", " ", ""]
        )
        
        for i, img in enumerate(summary_img):
            if not img:
                continue
            
            chunks = text_splitter.split_text(img.page_content)
            
            # Create a document for each chunk
            for j, chunk in enumerate(chunks):
                if not chunk.strip():
                    continue
                    
                text_chunks.append(
                    Document(
                        page_content=chunk,
                        metadata={
                            **img.metadata,
                            "doc_id": str(uuid.uuid4()),
                            "type": "text",
                            "chunk_index": j,
                        }
                    )
                )
        logging.info("=== Text chunks: {}".format(len(text_chunks)))
        summary_img.extend(text_chunks)
    except Exception as e:
        logging.info("Skipping text extraction")
    finally: 
        overall_summary = summary_img
    
    return {
        "overall_summary": overall_summary
    }

# async def ocr_with_gemini(image: Image.Image, model: str = "gemini-2.5-flash"):

#     image_buf = image_to_base64(image, format="PNG")
#     prompt = textwrap.dedent("""
#     Your task is to extract all text from the provided image and return it in **Markdown format**.

#     Key rules:

#     1. **Analyze Visual Layout:**
#     - First, analyze the overall visual layout of the image.
#     - If the image contains multiple distinct pages or sub-columns, split each section using the delimiters `<page>` and `</page>`.
#     - Even if it is a single page, it must be wrapped in `<page>`Content`</page>`.
#     - Ensure the content within each page is ordered logically from top to bottom and left to right.

#     2. **Tables:**
#     - If there are tables, format them properly using Markdown table syntax.
#     - Example:
#         `| Name | Age |`
#         `|--------|-----|`
#         `| Alice | 30 |`
#         `| Bob | 25 |`
#     - For complex tables with merged cells or multiple header rows, do your best to maintain the structure by aligning content in columns and rows.
#     - Do not use long horizontal rules (like multiple dashes or equals signs) to separate rows.
#     - If it's not possible to infer headers, just format it as-is in rows and columns using the pipe `|` syntax.

#     3. **Section and Hierarchy Splitting:**
#     - Label the hierarchy properly with Markdown format (e.g., `#`, `##`, `###` for headings).
#     - Use lists (`-` or `*`) to capture bullet points or numbered items.
#     - Capture the visual hierarchy exactly as it appears in the image.

#     4. **Formatting Cleanup:**
#     - Completely ignore decorative elements, horizontal separators (e.g., `-----`, `====`, `___`) and page numbers.
#     - Do not include any commentary, notes, or interpretation — just extract and format the raw content.

#     5. **Images and Charts:**
#     - If there is an image (like a photo), provide a one-sentence description.
#     - If it's a chart, summarize the key values or describe what the chart shows.
#     """)

#     response = await google_geni_client().aio.models.generate_content_stream(
#         model=model,
#         contents=[
#             Part.from_bytes(
#                 data=image_buf.getvalue(),
#                 mime_type="image/png",
#             ),
#             prompt
#         ],
#         config=GenerateContentConfig(
#             temperature=0,
#             thinking_config=ThinkingConfig(
#                 thinking_budget=0,
#             ),
#             # max_output_tokens=4000,
#         ),
#     )

#     final_response = ""

#     async for res in response:
#         final_response += res.text or ""
    
#     return final_response
