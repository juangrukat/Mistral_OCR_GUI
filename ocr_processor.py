import threading
import os
import math
import base64
import tempfile
from file_uploader import FileUploader
from ocr_api_client import OCRApiClient
from pdf_processor import PDFProcessor

class OCRProcessor:
    def __init__(self, api_key, api_base_url, aws_access_key, aws_secret_key, s3_bucket):
        self.file_uploader = FileUploader(aws_access_key, aws_secret_key, s3_bucket)
        self.api_client = OCRApiClient(api_key, api_base_url)
        self.pdf_processor = PDFProcessor()
        self.pages_per_chunk = 2  # Reduced from 5 to 2 pages per chunk
        self.max_retries = 3
        
    def process_document(self, file_path, model_id, callback=None):
        """Process a document with progress updates via callback"""
        def process_thread():
            try:
                # Get total page count
                total_pages = self.pdf_processor.get_page_count(file_path)
                
                if total_pages <= self.pages_per_chunk:
                    # Process entire document if it's small enough
                    if callback:
                        callback("status", "Processing document...")
                    
                    # Try URL-based approach first
                    try:
                        if callback:
                            callback("status", "Uploading document...")
                        
                        url = self.file_uploader.upload_file(file_path)
                        if not url:
                            if callback:
                                callback("error", "Failed to upload document")
                            return
                        
                        result = self.api_client.process_document(
                            document_url=url,
                            document_name=os.path.basename(file_path),
                            model_id=model_id
                        )
                        
                        if callback:
                            callback("complete", result)
                    except Exception as e:
                        if "413" in str(e):
                            # Fallback to page-by-page processing
                            if callback:
                                callback("status", "Document too large, processing page by page...")
                            self._process_page_by_page(file_path, model_id, callback)
                        else:
                            raise e
                else:
                    # Process document in chunks
                    if callback:
                        callback("status", f"Document has {total_pages} pages. Processing in chunks...")
                    
                    # Try URL-based chunking first
                    try:
                        if callback:
                            callback("status", "Uploading document...")
                        
                        url = self.file_uploader.upload_file(file_path)
                        if not url:
                            if callback:
                                callback("error", "Failed to upload document")
                            return
                        
                        self._process_by_chunks(url, file_path, total_pages, model_id, callback)
                    except Exception as e:
                        if "413" in str(e):
                            # Fallback to page-by-page processing
                            if callback:
                                callback("status", "Chunks too large, processing page by page...")
                            self._process_page_by_page(file_path, model_id, callback)
                        else:
                            raise e
            
            except Exception as e:
                if callback:
                    callback("error", str(e))
        
        # Start processing in a background thread
        thread = threading.Thread(target=process_thread)
        thread.daemon = True
        thread.start()
        
        return thread
    
    def _process_by_chunks(self, url, file_path, total_pages, model_id, callback):
        """Process document in chunks using URL-based approach"""
        # Calculate number of chunks
        num_chunks = math.ceil(total_pages / self.pages_per_chunk)
        results = []
        
        for chunk_idx in range(num_chunks):
            start_page = chunk_idx * self.pages_per_chunk
            end_page = min((chunk_idx + 1) * self.pages_per_chunk - 1, total_pages - 1)
            
            if callback:
                callback("status", f"Processing pages {start_page}-{end_page} (chunk {chunk_idx+1}/{num_chunks})...")
            
            # Create page range for this chunk
            page_range = list(range(start_page, end_page + 1))
            
            # Process this chunk of pages
            chunk_result = self.api_client.process_document(
                document_url=url,
                document_name=os.path.basename(file_path),
                model_id=model_id,
                pages=page_range
            )
            
            if chunk_result:
                results.append(chunk_result)
        
        # Combine results from all chunks
        combined_result = self._combine_results(results)
        
        if callback:
            callback("complete", combined_result)
    
    def _process_page_by_page(self, file_path, model_id, callback):
        """Process document page by page using direct base64 encoding"""
        total_pages = self.pdf_processor.get_page_count(file_path)
        results = []
        
        for page_num in range(total_pages):
            if callback:
                callback("status", f"Processing page {page_num+1}/{total_pages}...")
            
            # Extract single page as a separate PDF
            temp_path = self._extract_single_page(file_path, page_num)
            
            try:
                # Convert to base64
                with open(temp_path, 'rb') as f:
                    pdf_bytes = f.read()
                    base64_pdf = base64.b64encode(pdf_bytes).decode('utf-8')
                
                # Process using base64
                page_result = self.api_client.process_document_base64(
                    document_base64=base64_pdf,
                    document_name=f"page_{page_num}.pdf",
                    model_id=model_id
                )
                
                # Adjust page numbers
                if page_result and "pages" in page_result:
                    for page in page_result["pages"]:
                        if "page_num" in page:
                            page["page_num"] = page_num
                
                if page_result:
                    results.append(page_result)
            finally:
                # Clean up temp file
                if os.path.exists(temp_path):
                    os.unlink(temp_path)
        
        # Combine results
        combined_result = self._combine_results(results)
        
        if callback:
            callback("complete", combined_result)
    
    def _extract_single_page(self, pdf_path, page_num):
        """Extract a single page from a PDF and save to a temporary file"""
        import PyPDF2
        
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
            
            return temp_path
    
    def _combine_results(self, results):
        """Combine multiple OCR results into one"""
        if not results:
            return None
        
        combined = {
            "text": "",
            "pages": []
        }
        
        for result in results:
            combined["text"] += result.get("text", "") + "\n"
            combined["pages"].extend(result.get("pages", []))
        
        # Sort pages by page number
        combined["pages"].sort(key=lambda p: p.get("page_num", 0))
        
        return combined