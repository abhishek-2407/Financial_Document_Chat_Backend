from utils.llm_calling import call_openai
from typing import List
from functions.query_rag import retrieve_chunks
from fastapi import Depends

import markdown
import logging
from models import SummaryReport, ReportStatus
from datetime import datetime
import uuid
import requests
from utils.db import SessionLocal
from sqlalchemy.orm import Session

db = SessionLocal()


from utils.s3_function import get_presigned_urls_from_s3

class FileObject:
    """Helper class to mimic file object for presigned URL generation"""
    def __init__(self, file_name: str, file_type: str = "text/html"):
        self.fileName = file_name
        self.fileType = file_type

async def summarize_document(thread_id: str, file_id_list: List, max_pages: int = 10):
    
    system_prompt = """
    You are a DISCUSSION POINTS extractor with amazing facts and figure. Compare and provide the analysis with proper reasons also.
    
    Use the data provide to you to generate the discussion points. No need to add any additional information. 
    
    **Instructions 1:**
      - Must provide reasons for the point if mentioned in the document.
      - Provide the best analysis from the information.
      - Do not mention the same things mentioned in the document.
      - The markdown format should be accurate.
      - Provide the most Highlights points from tables.
    
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

            🔸 **Key Details**  
            ✅ It supports multiple formats.  
            ❌ It does not work with outdated versions.  
            
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


def markdown_to_pdf_and_upload_to_s3(
    markdown_text: str, 
    user_id: str, 
    thread_id: str, 
    source_file_ids: List[str],
    file_name: str = None,
    db: Session = db
):
    """
    Convert markdown to HTML and upload to S3
    """
    try:
        if not file_name:
            timestamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
            file_name = f"summary_report_{timestamp}.html"
        
        if not file_name.endswith('.html'):
            file_name += '.html'
        
        logging.info(f"Starting HTML generation and upload for: {file_name}")
        
        html_content = markdown.markdown(markdown_text, extensions=['tables', 'fenced_code'])
        
        # Add CSS styling
        styled_html = f"""
<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Document Summary Report</title>
    <style>
        body {{
            font-family: 'Segoe UI', Arial, sans-serif;
            line-height: 1.6;
            color: #2c3e50;
            max-width: 1200px;
            margin: 0 auto;
            padding: 20px;
            background-color: #f8f9fa;
        }}
        
        .container {{
            background-color: white;
            padding: 40px;
            border-radius: 8px;
            box-shadow: 0 2px 10px rgba(0,0,0,0.1);
        }}
        
        h1 {{
            color: #1a252f;
            font-size: 28px;
            font-weight: 700;
            margin: 1.5em 0 0.8em 0;
            padding-bottom: 0.3em;
            border-bottom: 3px solid #3498db;
        }}
        
        h2 {{
            color: #2c3e50;
            font-size: 22px;
            font-weight: 600;
            margin: 1.3em 0 0.7em 0;
            padding-bottom: 0.2em;
            border-bottom: 2px solid #95a5a6;
        }}
        
        h3 {{
            color: #34495e;
            font-size: 18px;
            font-weight: 600;
            margin: 1.2em 0 0.6em 0;
        }}
        
        h4 {{
            color: #34495e;
            font-size: 16px;
            font-weight: 600;
            margin: 1em 0 0.5em 0;
        }}
        
        h5, h6 {{
            color: #34495e;
            font-size: 14px;
            font-weight: 600;
            margin: 0.8em 0 0.4em 0;
        }}
        
        p {{
            margin: 0.8em 0;
            text-align: justify;
        }}
        
        code {{
            background-color: #f8f9fa;
            color: #e74c3c;
            padding: 2px 6px;
            border-radius: 4px;
            font-family: 'Consolas', 'Monaco', 'Courier New', monospace;
            font-size: 0.9em;
            border: 1px solid #e9ecef;
        }}
        
        pre {{
            background-color: #f8f9fa;
            color: #2c3e50;
            padding: 16px;
            border-radius: 6px;
            overflow-x: auto;
            border-left: 4px solid #3498db;
            font-family: 'Consolas', 'Monaco', 'Courier New', monospace;
            line-height: 1.4;
            margin: 1em 0;
        }}
        
        pre code {{
            background: none;
            padding: 0;
            border: none;
            color: inherit;
        }}
        
        blockquote {{
            border-left: 4px solid #3498db;
            margin: 1em 0;
            padding: 0.5em 0 0.5em 15px;
            background-color: #f8f9fa;
            color: #555;
            font-style: italic;
            border-radius: 0 4px 4px 0;
        }}
        
        table {{
            border-collapse: collapse;
            width: 100%;
            margin: 1em 0;
            background-color: white;
            box-shadow: 0 1px 3px rgba(0,0,0,0.1);
        }}
        
        th {{
            background: #34495e;
            color: white;
            font-weight: 600;
            padding: 12px 8px;
            text-align: left;
            border: 1px solid #2c3e50;
        }}
        
        td {{
            padding: 10px 8px;
            border: 1px solid #dee2e6;
            vertical-align: top;
        }}
        
        tr:nth-child(even) {{
            background-color: #f8f9fa;
        }}
        
        tr:hover {{
            background-color: #e8f4f8;
        }}
        
        ul, ol {{
            margin: 1em 0;
            padding-left: 2em;
        }}
        
        li {{
            margin: 0.3em 0;
            line-height: 1.5;
        }}
        
        a {{
            color: #3498db;
            text-decoration: none;
        }}
        
        a:hover {{
            color: #2980b9;
            text-decoration: underline;
        }}
        
        hr {{
            border: none;
            height: 2px;
            background: linear-gradient(to right, #3498db, #2ecc71, #3498db);
            margin: 2em 0;
        }}
        
        strong, b {{
            font-weight: 700;
            color: #2c3e50;
        }}
        
        em, i {{
            font-style: italic;
            color: #34495e;
        }}
        
        .header {{
            text-align: center;
            margin-bottom: 2em;
            padding-bottom: 1em;
            border-bottom: 2px solid #ecf0f1;
        }}
        
        .footer {{
            margin-top: 2em;
            padding-top: 1em;
            border-top: 1px solid #ecf0f1;
            text-align: center;
            color: #7f8c8d;
            font-size: 0.9em;
        }}
        
        @media print {{
            body {{
                background-color: white;
                padding: 0;
            }}
            .container {{
                box-shadow: none;
                padding: 20px;
            }}
        }}
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>📋 Discussion Points Report</h1>
            <p><em>Generated on {datetime.utcnow().strftime("%B %d, %Y at %H:%M UTC")}</em></p>
        </div>
        {html_content}
        <div class="footer">
            <p>Report generated from {len(source_file_ids)} source document(s)</p>
        </div>
    </div>
</body>
</html>
"""
        
        logging.info("Converting markdown to HTML...")
        html_bytes = styled_html.encode('utf-8')
        
        file_obj = FileObject(file_name, "text/html")
        
        logging.info("Getting presigned URL from S3...")
        presigned_data = get_presigned_urls_from_s3(user_id, file_obj, thread_id)
        
        file_id = presigned_data["file_id"]
        presigned_url = presigned_data["presigned_url"]
        s3_file_url = presigned_data["file_url"]
        file_key = presigned_data["file_key"]
        
        logging.info(f"Uploading HTML to S3: {file_key}")
        
        headers = {
            'Content-Type': 'text/html; charset=utf-8'
        }
        
        response = requests.put(
            presigned_url,
            data=html_bytes,
            headers=headers
        )
        
        if response.status_code != 200:
            logging.error(f"Failed to upload HTML to S3. Status code: {response.status_code}")
            raise Exception(f"S3 upload failed with status code: {response.status_code}")
        
        logging.info(f"✅ Successfully uploaded HTML to S3: {s3_file_url}")
        
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
        logging.error(f"❌ Error in HTML generation and upload: {str(e)}")
        
        if db and 'file_id' in locals():
            try:
                summary_report = SummaryReport(
                    file_id=file_id,
                    s3_url="",
                    file_name=file_name or "failed_upload.html",
                    created_at=datetime.utcnow(),
                    status=ReportStatus.inprogress,  # or create a 'failed' status
                    source_file_id=source_file_ids
                )
                db.add(summary_report)
                db.commit()
            except:
                pass
        
        raise Exception(f"HTML generation and upload failed: {str(e)}")


def markdown_to_pdf_method3(markdown_text, output_path):
    """
    Convert markdown to HTML file (replaces PDF functionality)
    Note: Function name kept for compatibility but now generates HTML
    """
    try:
        # Convert markdown to HTML
        html_content = markdown.markdown(markdown_text, extensions=['tables', 'fenced_code'])
        
        # Add CSS styling
        styled_html = f"""
<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Document Report</title>
    <style>
        body {{
            font-family: 'DejaVu Sans', Arial, sans-serif;
            line-height: 1.6;
            color: #333;
            max-width: 1000px;
            margin: 0 auto;
            padding: 20px;
        }}
        h1, h2, h3, h4, h5, h6 {{
            color: #2c3e50;
            margin-top: 1.5em;
            margin-bottom: 0.5em;
        }}
        code {{
            background-color: #f8f8f8;
            padding: 2px 4px;
            border-radius: 3px;
            font-family: 'Courier New', monospace;
            font-size: 0.9em;
        }}
        pre {{
            background-color: #f8f8f8;
            padding: 15px;
            border-radius: 5px;
            overflow-x: auto;
            border-left: 4px solid #3498db;
        }}
        blockquote {{
            border-left: 4px solid #bdc3c7;
            margin-left: 0;
            padding-left: 15px;
            color: #7f8c8d;
        }}
        table {{
            border-collapse: collapse;
            width: 100%;
            margin: 1em 0;
        }}
        th, td {{
            border: 1px solid #ddd;
            padding: 8px;
            text-align: left;
        }}
        th {{
            background-color: #f2f2f2;
            font-weight: bold;
        }}
        ul, ol {{
            margin: 1em 0;
            padding-left: 2em;
        }}
        @media print {{
            body {{ margin: 0; padding: 15px; }}
        }}
    </style>
</head>
<body>
    {html_content}
</body>
</html>
"""
        
        # Change output path to HTML if it has PDF extension
        if output_path.endswith('.pdf'):
            output_path = output_path.replace('.pdf', '.html')
        elif not output_path.endswith('.html'):
            output_path += '.html'
        
        with open(output_path, 'w', encoding='utf-8') as f:
            f.write(styled_html)
        
        logging.info(f"HTML file saved to: {output_path}")
        return output_path
        
    except Exception as e:
        logging.error(f"Error creating HTML file: {str(e)}")
        raise