import os
import uuid
import io
import json
import logging
import time
import base64
import tempfile
import subprocess
import fitz
import concurrent.futures
from typing import List, Dict, Any, Tuple
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
from vertexai.generative_models import GenerativeModel, Part
import vertexai

from pdf2image import convert_from_bytes
# from IPython.display import Image, display


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

def _convert_pdf_to_images(pdf_bytes: bytes, dpi: int = 300, max_workers: int = 100) -> List[str]:
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

def _convert_image_to_base64(img: Image.Image, format: str = "PNG", optimize: bool = True, quality: int = 95) -> str:
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

    model = AzureChatOpenAI(model="gpt-4o-mini",
                            api_key=os.getenv("AZURE_OPENAI_API_KEY"),
                            azure_endpoint=os.getenv("AZURE_OPENAI_ENDPOINT"),
                            api_version=os.getenv("AZURE_OPENAI_VERSION"),
                            max_tokens=4000)

    prompt_template = """ You are Document scrapper who extract all the information from the given image.
    
    Extract all text from the given image exactly as it appears, maintaining the original wording, spelling, capitalization, numbers, and formatting.

If there are any charts, graphs, or bar plots, describe each of them specifically and accurately. Identify the type of each graph (e.g., bar plot, line chart, pie chart) and extract the data into table file foramte, including labels, axes, legends, and data values if visible.

If there are tables present, extract them in Markdown table format, ensuring that all values are correctly mapped to their respective rows and columns. Add a proper heading and table name above each table, do not miss any information.

If there are any random images (pictures unrelated to charts/graphs/tables), summarize them briefly in short paragraphs without adding any interpretation or assumption.

Important Instructions:
- Do not round any number.(Priority)
- Convert the chart and graph data in form of table which we can use later for retrieval.
- Do not miss any information.
- Do not add anything beyond the information visible in the image.
- Do not write statements like “There are no charts, graphs, or bar plots present in the image.”
- Extract and organize everything systematically: Headings > Full extracted text > Tables (Markdown format) > Graphs/Charts Description .

Focus on precision and completeness in extraction. """
    
    def process_single_image(image_data: Tuple[int, str]) -> Tuple[int, str]:
        """Process a single image and return its index and summary"""
        idx, image = image_data
        try:
            messages = [
                (
                    "user",
                    [
                        {"type": "text", "text": prompt_template},
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
    

def get_advance_chunk_gemini(base64_str: str, file_name: str, thread_id: str, file_id: str, file_type: str, extension: str) -> dict:
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

    # model = AzureChatOpenAI(model="gpt-4o-mini",
    #                         api_key=os.getenv("AZURE_OPENAI_API_KEY"),
    #                         azure_endpoint=os.getenv("AZURE_OPENAI_ENDPOINT"),
    #                         api_version=os.getenv("AZURE_OPENAI_VERSION"),
    #                         max_tokens=4000)

    prompt_template = """ You are Document scrapper who extract the information from the given image.
    
Extract text from the given image exactly as it appears, maintaining the original wording, spelling, capitalization, numbers, and formatting.

If there are any charts, graphs, or bar plots, describe each of them specifically and accurately in short. Identify the type of each graph (e.g., bar plot, line chart, pie chart) and extract the data into table file foramte, including labels, axes, legends, and data values if visible.

If there are tables present, extract them in Markdown table format, ensuring that all values are correctly mapped to their respective rows and columns. Add a proper heading and table name above each table, do not miss any information.

If there are any random images (pictures unrelated to charts/graphs/tables), summarize them in short paragraphs without adding any interpretation or assumption)

Important Instructions:
- Do not round any number.(Priority)
- Convert the chart and graph data in form of table which we can use later for retrieval.
- Do not miss any information.
- Do not add anything beyond the information visible in the image.
- Do not write statements like “There are no charts, graphs, or bar plots present in the image.”
- Extract and organize everything systematically: Headings > Full extracted text > Tables (Markdown format) > Graphs/Charts Description .


Focus on precision and completeness in extraction. """
    
    def process_single_image(image_data: Tuple[int, str]) -> Tuple[int, str]:
        """Process a single image and return its index and summary"""
        idx, image = image_data
        try:
            messages =  [
                prompt_template,  # Text part
                Part.from_data(
                    data=image,  # Raw bytes, not base64
                    mime_type="image/jpeg",
                ),
            ]
            
            MEDIA_ANALYSIS_MODEL = os.getenv("GOOGLE_VISION_MODEL")
            
            generation_config = {
                    "max_output_tokens": 3000, 
                }
                            
            model = GenerativeModel(MEDIA_ANALYSIS_MODEL)
            response = model.generate_content(messages, generation_config=generation_config)
            result = ""
            result = response.text

            # prompt = ChatPromptTemplate.from_messages(messages)
            # chain = prompt | model | StrOutputParser()
            # summary = chain.invoke({})
            logging.info(f"Successfully processed image {idx+1}/{len(images)}")
            return idx, result
            
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