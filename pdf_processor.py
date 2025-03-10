import os
import PyPDF2
from pathlib import Path
import tempfile
import base64

class PDFProcessor:
    def __init__(self, max_size_mb=10):
        self.max_size_bytes = max_size_mb * 1024 * 1024  # Convert MB to bytes
        
    def is_pdf_too_large(self, pdf_path):
        """Check if PDF exceeds the maximum allowed size"""
        return os.path.getsize(pdf_path) > self.max_size_bytes
    
    def split_pdf(self, pdf_path, pages_per_chunk=10):
        """Split a PDF into smaller chunks"""
        chunks = []
        
        with open(pdf_path, 'rb') as file:
            reader = PyPDF2.PdfReader(file)
            total_pages = len(reader.pages)
            
            # Calculate number of chunks needed
            num_chunks = (total_pages + pages_per_chunk - 1) // pages_per_chunk
            
            for i in range(num_chunks):
                start_page = i * pages_per_chunk
                end_page = min((i + 1) * pages_per_chunk, total_pages)
                
                # Create a new PDF writer for this chunk
                writer = PyPDF2.PdfWriter()
                
                # Add pages to the chunk
                for page_num in range(start_page, end_page):
                    writer.add_page(reader.pages[page_num])
                
                # Save the chunk to a temporary file
                temp_file = tempfile.NamedTemporaryFile(suffix='.pdf', delete=False)
                with open(temp_file.name, 'wb') as output_file:
                    writer.write(output_file)
                
                chunks.append({
                    'path': temp_file.name,
                    'start_page': start_page,
                    'end_page': end_page - 1
                })
        
        return chunks
    
    def get_page_count(self, pdf_path):
        """Get the total number of pages in a PDF"""
        with open(pdf_path, 'rb') as file:
            reader = PyPDF2.PdfReader(file)
            return len(reader.pages)
    
    def extract_page_as_base64(self, pdf_path, page_num):
        """
        Extract a single page from a PDF and return it as a base64-encoded string
        
        Args:
            pdf_path: Path to the PDF file
            page_num: Page number to extract (0-indexed)
            
        Returns:
            Base64-encoded string of the PDF page
        """
        with open(pdf_path, 'rb') as file:
            reader = PyPDF2.PdfReader(file)
            if page_num >= len(reader.pages):
                raise ValueError(f"Page {page_num} does not exist in the PDF")
            
            # Create a new PDF with just this page
            writer = PyPDF2.PdfWriter()
            writer.add_page(reader.pages[page_num])
            
            # Write to a temporary file
            temp_file = tempfile.NamedTemporaryFile(suffix='.pdf', delete=False)
            temp_path = temp_file.name
            temp_file.close()
            
            with open(temp_path, 'wb') as output_file:
                writer.write(output_file)
            
            # Read the file and encode as base64
            with open(temp_path, 'rb') as f:
                pdf_bytes = f.read()
                base64_pdf = base64.b64encode(pdf_bytes).decode('utf-8')
            
            # Clean up the temporary file
            os.unlink(temp_path)
            
            return base64_pdf
    
    def get_page_chunks(self, pdf_path, pages_per_chunk=5):
        """
        Get page ranges for processing a PDF in chunks
        
        Args:
            pdf_path: Path to the PDF file
            pages_per_chunk: Number of pages per chunk
            
        Returns:
            List of page ranges, each containing start_page and end_page
        """
        total_pages = self.get_page_count(pdf_path)
        chunks = []
        
        for i in range(0, total_pages, pages_per_chunk):
            start_page = i
            end_page = min(i + pages_per_chunk - 1, total_pages - 1)
            chunks.append({
                'start_page': start_page,
                'end_page': end_page
            })
        
        return chunks