"""
azure_form_parser.py

This module handles document extraction using local PDF/DOCX parsers.
Azure Form Recognizer is currently disabled for local-only testing.
"""

import os
import io
import tempfile
from dotenv import load_dotenv
import docx
import PyPDF2

# Load environment variables (not used here, but kept for compatibility)
load_dotenv()

def extract_text_from_docx(file_bytes):
    """Extract text from DOCX file using python-docx"""
    with tempfile.NamedTemporaryFile(delete=False, suffix='.docx') as temp_file:
        temp_file.write(file_bytes)
        temp_file_path = temp_file.name

    try:
        doc = docx.Document(temp_file_path)
        text = "\n".join([paragraph.text for paragraph in doc.paragraphs])
        return text
    finally:
        os.unlink(temp_file_path)

def extract_text_from_pdf(file_bytes):
    """Extract text from PDF file using PyPDF2"""
    pdf_file = io.BytesIO(file_bytes)
    text = ""

    try:
        pdf_reader = PyPDF2.PdfReader(pdf_file)
        for page in pdf_reader.pages:
            page_text = page.extract_text()
            if page_text:
                text += page_text + "\n"
        return text.strip()
    except Exception as e:
        return f"Error extracting text from PDF: {str(e)}"

def parse_document(file_bytes, file_type):
    """
    Main function to parse documents locally (no Azure).

    Args:
        file_bytes: The bytes of the uploaded file
        file_type: The file type ('pdf' or 'docx')

    Returns:
        str: Extracted text from the document
    """
    if file_type.lower() == "pdf":
        return extract_text_from_pdf(file_bytes)
    elif file_type.lower() == "docx":
        return extract_text_from_docx(file_bytes)
    else:
        raise ValueError("Unsupported file type. Please upload a PDF or DOCX file.")