from utils.llm_calling import call_openai
from typing import List, Dict
from functions.query_rag import retrieve_chunks
from fastapi import Depends

from reportlab.lib.pagesizes import A4
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch
from reportlab.lib import colors
from reportlab.lib.enums import TA_LEFT, TA_CENTER, TA_JUSTIFY
import markdown
from markdown.extensions import codehilite
import re
from html import unescape
import logging
from models import SummaryReport, ReportStatus
from datetime import datetime
import uuid
import requests
from utils.db import SessionLocal
from sqlalchemy.orm import Session
from functions.doc_summary_prompts import dynamic_sections, fixed_section_prompt, word_file_prompt
from sqlalchemy import event, inspect
import requests
from models import UserS3Mapping
from utils.s3_function import get_presigned_urls_from_s3
import threading
from models import FileAttribute  # Make sure this matches your model import
from utils.db import get_db
import tempfile
import os

db = SessionLocal()

class FileObject:
    """Helper class to mimic file object for presigned URL generation"""
    def __init__(self, file_name: str, file_type: str = "application/pdf"):
        self.fileName = file_name
        self.fileType = file_type
        
        
async def get_dynamic_sections(file_id_list: List) :
    
    chunks = await retrieve_chunks(
                user_query="",
                file_id_list=file_id_list,
                top_k=70 
            )
    user_prompt = f"This is the document information : {chunks}"
    
    response = call_openai(system_prompt=dynamic_sections, user_prompt=user_prompt,model="gpt-4o", 
                temperature=0, parse_json=True)
    
    return response



def trigger_api_after_delay(file_id: str):
    try:
        # response = requests.post(
        #     "http://0.0.0.0:8001/doc-eval/get-dynamic-sections",
        #     json={"file_id_list": [str(file_id)], "user_id": "admin"}
        # )
        # response.raise_for_status()
        gen_section = get_dynamic_sections(file_id_list=[file_id])
        file_attr = FileAttribute(file_id=file_id, generated_section=gen_section)
        db.add(file_attr)
        
        logging.info(f"✅ File Attributes Triggered for file_id: {file_id}")
    except Exception as e:
        logging.error(f"❌ Error Triggering File Attributes for file_id {file_id}: {e}")


@event.listens_for(UserS3Mapping, 'after_update')
def after_update_rag_status(mapper, connection, target):
    state = inspect(target)
    rag_status_history = state.attrs.rag_status.history

    if rag_status_history.has_changes() and rag_status_history.added[0] is True:
        # Delay execution by 10 seconds using threading.Timer
        threading.Timer(5.0, trigger_api_after_delay, args=[str(target.file_id)]).start()
        

import asyncio

async def summarize_document_filters(
    thread_id: str,
    file_id_list: List,
    max_pages: int = 10,
    fixed_section_list: List[str] | None = None,
    dynamic_section_list: Dict | None = None,
):
    logging.info("▶️  Summarization started  | thread_id=%s  files=%s", thread_id, file_id_list)

    # 1️⃣  Pull the text once
    chunks = await retrieve_chunks(user_query="", file_id_list=file_id_list, top_k=50)
    user_prompt = f"This is the document information you have to work on: {chunks}"
    logging.info("✅  Chunks retrieved")

    # 2️⃣  Normalise section names (e.g. 'Volume Growth' → 'volume_growth')
    section_keys = [
        s.lower().replace(" ", "_") for s in (fixed_section_list or [])
    ]
    logging.info("ℹ️  Normalised sections: %s", section_keys)

    # 3️⃣  Flatten your fixed‑prompt list into a dict
    prompt_map: dict[str, str] = {}
    for item in fixed_section_prompt:   # fixed_section_prompt is your original list of dicts
        prompt_map.update(item)

    # 4️⃣  Define the worker that will run in a background thread
    async def get_summary(sec: str) -> str:
        if sec not in prompt_map:
            logging.warning("⚠️  No prompt found for section '%s'", sec)
            return f"## {sec}\n\nNo prompt found for this section.\n\n"

        logging.info("🧵  Submitting section '%s' to background thread", sec)
        # Run the blocking call in a thread.  For ≤3.8 replace with:
        # loop = asyncio.get_running_loop()
        # response = await loop.run_in_executor(None, call_openai, ...)
        response = await asyncio.to_thread(
            call_openai,
            model="gpt-4o",
            temperature=0,
            system_prompt=prompt_map[sec],
            user_prompt=user_prompt,
        )
        logging.info("✔️  Section '%s' completed", sec)
        return f"\n\n{response}\n\n ---"

    # 5️⃣  Fire off all workers concurrently
    summaries = await asyncio.gather(*(get_summary(sec) for sec in section_keys))
    logging.info("🏁  All sections processed")

    # 6️⃣  Collate the result
    if summaries:
        final = "\n\n --- \n\n\n" + "".join(summaries)
        logging.info("🎉  Final summary constructed")
        return final

    logging.warning("😕  No summaries generated")
    return "#\n\nNo content summarised."
            
            

async def summarize_document_filters_2(
    thread_id: str,
    file_id_list: List[str],
    max_pages: int = 10,          # kept in case you later need it
) -> str:
    """
    For every prompt in `word_file_prompt`, call the model concurrently
    and return a single, collated response string.
    """
    logging.info("▶️  Summarization started | thread_id=%s files=%s", thread_id, file_id_list)

    chunks = await retrieve_chunks(user_query="", file_id_list=file_id_list, top_k=50)
    user_prompt = f"This is the document information you have to work on:\n\n{chunks}"
    logging.info("✅  Chunks retrieved")

    prompt_map: dict[str, str] = word_file_prompt    # <- key change
    section_keys = list(prompt_map.keys())

    async def get_summary(sec: str) -> str:
        sys_prompt = prompt_map.get(sec)
        if not sys_prompt:
            logging.warning("⚠️  No prompt found for section '%s'", sec)
            return f"## {sec}\n\nNo prompt found for this section.\n\n"

        logging.info("🧵  Submitting section '%s' to background thread", sec)
        response = await asyncio.to_thread(
            call_openai,
            model="gpt-4o",
            temperature=0,
            system_prompt=sys_prompt,
            user_prompt=user_prompt,
        )
        logging.info("✔️  Section '%s' completed", sec)
        return f"\n\n{response}\n\n---"

    summaries = await asyncio.gather(*(get_summary(sec) for sec in section_keys))
    logging.info("🏁  All sections processed")

    if summaries:
        final = "\n\n".join(summaries)
        logging.info("🎉  Final summary constructed")
        return final

    logging.warning("😕  No summaries generated")
    return "#\n\nNo content summarised."



async def summarize_document(thread_id: str, file_id_list: List, max_pages: int = 10, fixed_section_list : List = None, dynamic_section_list : Dict = None):
    
    system_prompt = """
    You are a detailed Document Analyser with all amazing facts and figure.
    
    Use the data provide to you to generate a detailed summary of the document. No need to add any additional information.
    
    **Instructions 1:**
      - Provide the best analysis from the information.
      - Do not mention the same things mentioned in the document.
      - Mention the informations in Tables wherever needed.
      - The markdown format should be accurate.
    
    **Don't s:**
      - Do NOT add any conclusion.
      - (Important) Do not mention like this if anything is missing (No graphs, charts, or additional images were detected in the document).
      - Do not Mention Abstract, Overview, Summary section.
      - Do not mention metadata information.
      
    
    **Response Guideline: **
        ✅ **Emoji Formatting Rules:**  
            - First heading should be H2 font
            - ✅ Use checkmarks (✅) for key points and important statements.  
            - 🔶 Use "🔶" at the start of **big headings**.  
            - 🔸 Use "🔸" at the start of **smaller headings**.  
            - 🚀 Use additional relevant emojis to make responses engaging.  
            - ❌ Use "❌" for incorrect statements or warnings.  

            ✅ **Example Response Structure:**  
            🔶 **Overview**  
            ✅ This feature helps improve performance.  

            
    If you dont get any information from the document, just return "No information found"
    
    """

    page_start = 1
    batch_size = 5
    all_summaries = []
    processed_batches = 0
    
    logging.info("Starting document summarization...")
    
    while page_start <= max_pages:
        # Calculate the actual page range for current batch
        page_end = min(page_start + batch_size - 1, max_pages)
        page_list = list(range(page_start, page_end + 1))
        
        logging.info(f"📄 Processing batch {processed_batches + 1}: pages {page_list}")
        
        try:
            chunks = await retrieve_chunks(
                user_query="",
                file_id_list=file_id_list, 
                page_list=page_list, 
                top_k=50
            )
                        
            # Check if chunks are empty - BREAK if no chunks
            if not chunks or (isinstance(chunks, str) and chunks.strip() == ""):
                logging.info(f"❌ No chunks found for pages {page_list}. Stopping iteration.")
                break
            
            user_prompt = f"This is the document information you have to summarize: {chunks}"
            
            response = call_openai(
                model="gpt-4o", 
                temperature=0, 
                system_prompt=system_prompt, 
                user_prompt=user_prompt
            )
            
            if response.strip() == "No information found":
                logging.info(f"❌ No information found for pages {page_list}. Stopping iteration.")
                break
            
            page_summary = f"## 📄 Pages {page_start}-{page_end}\n\n{response}\n\n"
            all_summaries.append(page_summary)
            processed_batches += 1
            
            logging.info(f"✅ Successfully processed pages {page_list}")
            
        except Exception as e:
            logging.info(f"❌ Error processing pages {page_list}: {str(e)}")
            pass
            
        # Move to next batch
        page_start += batch_size
    
    logging.info(f"📊 Summary complete! Processed {processed_batches} batches out of maximum {max_pages} pages.")
    
    if all_summaries:
        final_summary = f"# 📋 Document Summary\n\n*Processed {processed_batches} page batches (Max: {max_pages} pages)*\n\n" + "\n".join(all_summaries)
        return final_summary
    else:
        return "❌ No information found in the document"
    
def markdown_to_pdf_method3(markdown_text, output_path):
    """
    Convert markdown to PDF using ReportLab
    Requires: pip install reportlab markdown
    """
    try:
        # Create PDF document
        doc = SimpleDocTemplate(output_path, pagesize=A4, topMargin=1.5*inch, bottomMargin=1*inch)
        
        # Get styles
        styles = getSampleStyleSheet()
        
        # Custom styles
        heading1_style = ParagraphStyle(
            'CustomHeading1',
            parent=styles['Heading1'],
            fontSize=18,
            spaceAfter=12,
            spaceBefore=12,
            textColor=colors.HexColor('#2c3e50')
        )
        
        heading2_style = ParagraphStyle(
            'CustomHeading2',
            parent=styles['Heading2'],
            fontSize=14,
            spaceAfter=10,
            spaceBefore=10,
            textColor=colors.HexColor('#2c3e50')
        )
        
        normal_style = ParagraphStyle(
            'CustomNormal',
            parent=styles['Normal'],
            fontSize=10,
            spaceAfter=6,
            alignment=TA_JUSTIFY
        )
        
        # Convert markdown to basic elements
        story = []
        lines = markdown_text.split('\n')
        
        for line in lines:
            line = line.strip()
            if not line:
                story.append(Spacer(1, 6))
                continue
                
            if line.startswith('# '):
                story.append(Paragraph(line[2:], heading1_style))
            elif line.startswith('## '):
                story.append(Paragraph(line[3:], heading2_style))
            elif line.startswith('### '):
                story.append(Paragraph(line[4:], heading2_style))
            else:
                # Clean up markdown formatting for basic text
                line = re.sub(r'\*\*(.*?)\*\*', r'<b>\1</b>', line)
                line = re.sub(r'\*(.*?)\*', r'<i>\1</i>', line)
                line = re.sub(r'`(.*?)`', r'<font name="Courier">\1</font>', line)
                story.append(Paragraph(line, normal_style))
        
        # Build PDF
        doc.build(story)
        logging.info(f"PDF saved to: {output_path}")
        
    except Exception as e:
        logging.error(f"Error converting markdown to PDF: {str(e)}")
        raise


def markdown_to_pdf_and_upload_to_s3(
    markdown_text: str, 
    user_id: str, 
    thread_id: str, 
    source_file_ids: List[str],
    file_name: str = None,
    db: Session = db
) :
   
    try:
        if not file_name:
            timestamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
            file_name = f"summary_report_{timestamp}.pdf"
        
        if not file_name.endswith('.pdf'):
            file_name += '.pdf'
        
        logging.info(f"Starting PDF generation and upload for: {file_name}")
        
        html_content = markdown.markdown(markdown_text, extensions=['tables', 'fenced_code'])
        
        # Add CSS styling
        styled_html = f"""
<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <style>
        @page {{
            size: A4;
            margin: 1.5cm;
        }}
        
        body {{
            font-family: 'DejaVu Sans', 'Segoe UI', Arial, sans-serif;
            line-height: 1.6;
            color: #2c3e50;
            font-size: 12px;
            margin: 0;
            padding: 0;
        }}
        
        /* Headings with progressive sizing */
        h1 {{
            color: #1a252f;
            font-size: 24px;
            font-weight: 700;
            margin: 1.5em 0 0.8em 0;
            padding-bottom: 0.3em;
            border-bottom: 3px solid #3498db;
        }}
        
        h2 {{
            color: #2c3e50;
            font-size: 20px;
            font-weight: 600;
            margin: 1.3em 0 0.7em 0;
            padding-bottom: 0.2em;
            border-bottom: 2px solid #95a5a6;
        }}
        
        h3 {{
            color: #34495e;
            font-size: 16px;
            font-weight: 600;
            margin: 1.2em 0 0.6em 0;
        }}
        
        h4 {{
            color: #34495e;
            font-size: 14px;
            font-weight: 600;
            margin: 1em 0 0.5em 0;
        }}
        
        h5, h6 {{
            color: #34495e;
            font-size: 13px;
            font-weight: 600;
            margin: 0.8em 0 0.4em 0;
        }}
        
        /* Paragraphs */
        p {{
            font-size: 12px;
            margin: 0.8em 0;
            text-align: justify;
        }}
        
        /* Inline code */
        code {{
            background-color: #f8f9fa;
            color: #e74c3c;
            padding: 2px 6px;
            border-radius: 4px;
            font-family: 'Consolas', 'Monaco', 'Courier New', monospace;
            font-size: 10px;
            border: 1px solid #e9ecef;
        }}
        
        /* Code blocks */
        pre {{
            background-color: #f8f9fa;
            color: #2c3e50;
            padding: 16px;
            border-radius: 6px;
            overflow-x: auto;
            border-left: 4px solid #3498db;
            font-family: 'Consolas', 'Monaco', 'Courier New', monospace;
            font-size: 10px;
            line-height: 1.4;
            margin: 1em 0;
            word-wrap: break-word;
            white-space: pre-wrap;
        }}
        
        pre code {{
            background: none;
            padding: 0;
            border: none;
            color: inherit;
        }}
        
        /* Blockquotes */
        blockquote {{
            border-left: 4px solid #3498db;
            margin: 1em 0;
            padding: 0.5em 0 0.5em 15px;
            background-color: #f8f9fa;
            color: #555;
            font-style: italic;
            border-radius: 0 4px 4px 0;
        }}
        
        /* Tables - Responsive and properly sized */
        .table-container {{
            width: 100%;
            overflow-x: auto;
            margin: 1em 0;
            border: 1px solid #dee2e6;
            border-radius: 6px;
        }}
        
        table {{
            border-collapse: collapse;
            width: 100%;
            font-size: 10px;
            background-color: white;
            min-width: 100%;
        }}
        
        th {{
            background: rgb(203, 203, 203);
            color: black;
            font-weight: 600;
            padding: 12px 8px;
            text-align: left;
            border: 1px solid #5a6c8a;
            font-size: 10px;
            word-wrap: break-word;
        }}
        
        td {{
            padding: 10px 8px;
            border: 1px solid #dee2e6;
            vertical-align: top;
            word-wrap: break-word;
            max-width: 200px;
            font-size: 10px;
            line-height: 1.4;
        }}
        
        /* Alternate row colors */
        tr:nth-child(even) {{
            background-color: #f8f9fa;
        }}
        
        tr:hover {{
            background-color: #e8f4f8;
        }}
        
        /* Lists */
        ul, ol {{
            margin: 1em 0;
            padding-left: 2em;
            font-size: 12px;
        }}
        
        li {{
            margin: 0.3em 0;
            line-height: 1.5;
        }}
        
        /* Nested lists */
        ul ul, ol ol, ul ol, ol ul {{
            margin: 0.3em 0;
        }}
        
        /* Links */
        a {{
            color: #3498db;
            text-decoration: none;
            border-bottom: 1px dotted #3498db;
        }}
        
        a:hover {{
            color: #2980b9;
            border-bottom: 1px solid #2980b9;
        }}
        
        /* Horizontal rules */
        hr {{
            border: none;
            height: 2px;
            background: linear-gradient(to right, #3498db, #2ecc71, #3498db);
            margin: 2em 0;
        }}
        
        /* Strong and emphasis */
        strong, b {{
            font-weight: 700;
            color: #2c3e50;
        }}
        
        em, i {{
            font-style: italic;
            color: #34495e;
        }}
        
        /* Page breaks */
        .page-break {{
            page-break-before: always;
        }}
        
        /* Prevent orphans and widows */
        h1, h2, h3, h4, h5, h6 {{
            page-break-after: avoid;
            orphans: 3;
            widows: 3;
        }}
        
        p, li {{
            orphans: 2;
            widows: 2;
        }}
        
        /* Better spacing for first elements */
        body > *:first-child {{
            margin-top: 0;
        }}
        
        body > *:last-child {{
            margin-bottom: 0;
        }}
        
        /* Table responsiveness for wide content */
        @media print {{
            .table-container {{
                overflow: visible;
            }}
            
            table {{
                table-layout: fixed;
                width: 100%;
            }}
            
            th, td {{
                word-break: break-word;
                hyphens: auto;
            }}
        }}
        
        /* Special styling for markdown tables that are too wide */
        .wide-table {{
            font-size: 9px;
        }}
        
        .wide-table th,
        .wide-table td {{
            padding: 6px 4px;
            font-size: 9px;
        }}
    </style>
</head>
<body>
    <div class="table-container">
        {html_content}
    </div>
</body>
</html>
"""
        
        logging.info("Converting HTML to PDF using ReportLab...")
        
        # Create PDF document in memory
        from io import BytesIO
        buffer = BytesIO()
        doc = SimpleDocTemplate(buffer, pagesize=A4, topMargin=1.5*inch, bottomMargin=1*inch)
        
        # Get styles
        styles = getSampleStyleSheet()
        
        # Custom styles
        heading1_style = ParagraphStyle(
            'CustomHeading1',
            parent=styles['Heading1'],
            fontSize=18,
            spaceAfter=12,
            spaceBefore=12,
            textColor=colors.HexColor('#2c3e50')
        )
        
        heading2_style = ParagraphStyle(
            'CustomHeading2',
            parent=styles['Heading2'],
            fontSize=14,
            spaceAfter=10,
            spaceBefore=10,
            textColor=colors.HexColor('#2c3e50')
        )
        
        heading3_style = ParagraphStyle(
            'CustomHeading3',
            parent=styles['Heading3'],
            fontSize=12,
            spaceAfter=8,
            spaceBefore=8,
            textColor=colors.HexColor('#34495e')
        )
        
        normal_style = ParagraphStyle(
            'CustomNormal',
            parent=styles['Normal'],
            fontSize=10,
            spaceAfter=6,
            alignment=TA_JUSTIFY
        )
        
        # Convert markdown to basic elements
        story = []
        lines = markdown_text.split('\n')
        
        i = 0
        while i < len(lines):
            line = lines[i].strip()
            if not line:
                story.append(Spacer(1, 6))
                i += 1
                continue
                
            if line.startswith('# '):
                # Remove emojis and clean text
                clean_text = re.sub(r'[^\w\s-]', '', line[2:]).strip()
                if clean_text:
                    story.append(Paragraph(clean_text, heading1_style))
            elif line.startswith('## '):
                clean_text = re.sub(r'[^\w\s-]', '', line[3:]).strip()
                if clean_text:
                    story.append(Paragraph(clean_text, heading2_style))
            elif line.startswith('### '):
                clean_text = re.sub(r'[^\w\s-]', '', line[4:]).strip()
                if clean_text:
                    story.append(Paragraph(clean_text, heading3_style))
            elif line.startswith('|') and '|' in line:
                # Handle table
                table_data = []
                while i < len(lines) and lines[i].strip().startswith('|'):
                    row_data = [cell.strip() for cell in lines[i].strip().split('|')[1:-1]]
                    if row_data and not all(cell in ['-', '--', '---'] for cell in row_data):
                        table_data.append(row_data)
                    i += 1
                
                if table_data:
                    table = Table(table_data)
                    table.setStyle(TableStyle([
                        ('BACKGROUND', (0, 0), (-1, 0), colors.grey),
                        ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
                        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
                        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
                        ('FONTSIZE', (0, 0), (-1, 0), 10),
                        ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
                        ('BACKGROUND', (0, 1), (-1, -1), colors.beige),
                        ('GRID', (0, 0), (-1, -1), 1, colors.black)
                    ]))
                    story.append(table)
                    story.append(Spacer(1, 12))
                i -= 1
            else:
                # Clean up markdown formatting for basic text
                line = re.sub(r'\*\*(.*?)\*\*', r'<b>\1</b>', line)
                line = re.sub(r'\*(.*?)\*', r'<i>\1</i>', line)
                line = re.sub(r'`(.*?)`', r'<font name="Courier">\1</font>', line)
                # Remove most emojis but keep basic formatting
                line = re.sub(r'[^\w\s\-\.\,\!\?\:\;\(\)\[\]<>/\'"=]', '', line)
                if line.strip():
                    story.append(Paragraph(line, normal_style))
            
            i += 1
        
        # Build PDF
        doc.build(story)
        
        # Get PDF bytes
        pdf_bytes = buffer.getvalue()
        buffer.close()
        
        file_obj = FileObject(file_name, "application/pdf")
        
        logging.info("Getting presigned URL from S3...")
        presigned_data = get_presigned_urls_from_s3(user_id, file_obj, thread_id)
        
        file_id = presigned_data["file_id"]
        presigned_url = presigned_data["presigned_url"]
        s3_file_url = presigned_data["file_url"]
        file_key = presigned_data["file_key"]
        
        logging.info(f"Uploading PDF to S3: {file_key}")
        
        headers = {
            'Content-Type': 'application/pdf'
        }
        
        response = requests.put(
            presigned_url,
            data=pdf_bytes,
            headers=headers
        )
        
        if response.status_code != 200:
            logging.error(f"Failed to upload PDF to S3. Status code: {response.status_code}")
            raise Exception(f"S3 upload failed with status code: {response.status_code}")
        
        logging.info(f"✅ Successfully uploaded PDF to S3: {s3_file_url}")
        
        if db:
            try:
                summary_report = SummaryReport(
                    file_id=file_id,
                    s3_url=s3_file_url,
                    file_name=file_name,
                    created_at=datetime.utcnow(),
                    status=ReportStatus.completed,
                    source_file_id=source_file_ids  # JSON field with list of source file IDs
                )
                
                db.add(summary_report)
                db.commit()
                
                logging.info(f"✅ Database updated with report ID: {file_id}")
                
            except Exception as db_error:
                logging.error(f"Database update failed: {str(db_error)}")
                db.rollback()
        
        return {
            "file_id": str(file_id),
            "s3_url": s3_file_url,
            "file_name": file_name,
            "file_key": file_key,
            "status": "completed",
            "source_file_ids": source_file_ids
        }
        
    except Exception as e:
        logging.error(f"❌ Error in PDF generation and upload: {str(e)}")
        
        if db and 'file_id' in locals():
            try:
                summary_report = SummaryReport(
                    file_id=file_id,
                    s3_url="",
                    file_name=file_name or "failed_upload.pdf",
                    created_at=datetime.utcnow(),
                    status=ReportStatus.inprogress,  # or create a 'failed' status
                    source_file_id=source_file_ids
                )
                db.add(summary_report)
                db.commit()
            except:
                pass
        
        raise Exception(f"PDF generation and upload failed: {str(e)}")