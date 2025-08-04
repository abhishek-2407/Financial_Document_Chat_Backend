import fitz  # PyMuPDF
import pdfplumber
import pytesseract
from PIL import Image
import io
from typing import List


def extract_text_pymupdf(pdf_bytes: bytes) -> str:
    """Extract raw text using PyMuPDF - fastest method"""
    doc = fitz.open(stream=pdf_bytes, filetype='pdf')
    text = ""
    
    try:
        for page in doc:
            text += page.get_text()
    finally:
        doc.close()
    
    return text


def extract_text_pdfplumber(pdf_bytes: bytes) -> str:
    """Extract raw text using pdfplumber - better for complex layouts"""
    text = ""
    
    with pdfplumber.open(io.BytesIO(pdf_bytes)) as pdf:
        for page in pdf.pages:
            page_text = page.extract_text()
            if page_text:
                text += page_text
    
    return text


def extract_text_ocr(pdf_bytes: bytes, dpi: int = 300) -> str:
    """Extract text using OCR - for scanned PDFs"""
    doc = fitz.open(stream=pdf_bytes, filetype='pdf')
    text = ""
    
    try:
        for page in doc:
            # Convert page to image
            mat = fitz.Matrix(dpi/72, dpi/72)
            pix = page.get_pixmap(matrix=mat, alpha=False)
            img_data = pix.tobytes("ppm")
            
            # OCR the image
            img = Image.open(io.BytesIO(img_data))
            page_text = pytesseract.image_to_string(img)
            text += page_text
    finally:
        doc.close()
    
    return text


def extract_all_text(pdf_bytes: bytes, method: str = "auto") -> str:
    """
    Extract all text from PDF without any modifications
    
    Args:
        pdf_bytes: PDF file as bytes
        method: "pymupdf", "pdfplumber", "ocr", or "auto" (tries all methods)
    
    Returns:
        Raw extracted text as string
    """
    
    if method == "pymupdf":
        return extract_text_pymupdf(pdf_bytes)
    
    elif method == "pdfplumber":
        return extract_text_pdfplumber(pdf_bytes)
    
    elif method == "ocr":
        return extract_text_ocr(pdf_bytes)
    
    elif method == "auto":
        # Try PyMuPDF first (fastest)
        text = extract_text_pymupdf(pdf_bytes)
        
        # If no text found, try pdfplumber
        if not text.strip():
            text = extract_text_pdfplumber(pdf_bytes)
        
        # If still no text, try OCR
        if not text.strip():
            text = extract_text_ocr(pdf_bytes)
        
        return text
    
    else:
        raise ValueError("Method must be 'pymupdf', 'pdfplumber', 'ocr', or 'auto'")


def extract_text_by_pages(pdf_bytes: bytes, method: str = "auto") -> List[str]:
    """
    Extract text from each page separately
    
    Args:
        pdf_bytes: PDF file as bytes
        method: extraction method
    
    Returns:
        List of text strings, one per page
    """
    
    if method == "pymupdf" or method == "auto":
        doc = fitz.open(stream=pdf_bytes, filetype='pdf')
        pages = []
        
        try:
            for page in doc:
                pages.append(page.get_text())
        finally:
            doc.close()
        
        return pages
    
    elif method == "pdfplumber":
        pages = []
        with pdfplumber.open(io.BytesIO(pdf_bytes)) as pdf:
            for page in pdf.pages:
                page_text = page.extract_text() or ""
                pages.append(page_text)
        return pages
    
    elif method == "ocr":
        doc = fitz.open(stream=pdf_bytes, filetype='pdf')
        pages = []
        
        try:
            for page in doc:
                mat = fitz.Matrix(300/72, 300/72)
                pix = page.get_pixmap(matrix=mat, alpha=False)
                img_data = pix.tobytes("ppm")
                img = Image.open(io.BytesIO(img_data))
                page_text = pytesseract.image_to_string(img)
                pages.append(page_text)
        finally:
            doc.close()
        
        return pages


# Simple usage functions
def get_pdf_text(pdf_file_path: str) -> str:
    """Extract all text from PDF file"""
    with open(pdf_file_path, 'rb') as f:
        pdf_bytes = f.read()
    return extract_all_text(pdf_bytes)


def get_pdf_text_from_bytes(pdf_bytes: bytes) -> str:
    """Extract all text from PDF bytes"""
    return extract_all_text(pdf_bytes)


# Example usage
# if __name__ == "__main__":
#     # From file
#     text = get_pdf_text("/Users/abhisheksingh/Downloads/Ultratech 2024 Annual report (1).pdf")
#     print(text)
    
#     # From bytes
#     with open("/Users/abhisheksingh/Downloads/Ultratech 2024 Annual report (1).pdf", "rb") as f:
#         pdf_data = f.read()
    
#     text = get_pdf_text_from_bytes(pdf_data)
#     print(text)
    
#     # Page by page
#     pages = extract_text_by_pages(pdf_data)
#     for i, page_text in enumerate(pages, 1):
#         print(f"--- Page {i} ---")
#         print(page_text)
#         print()
# Example usage
