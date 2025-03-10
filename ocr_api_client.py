import requests
import json
import time
import os
import base64
import tempfile
from PIL import Image
import PyPDF2
import io
import shutil
import uuid

class OCRApiClient:
    def __init__(self, api_key, base_url):
        self.api_key = api_key
        self.base_url = base_url
        self.headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json"
        }
        self.max_pages_per_chunk = 20  # Maximum pages per chunk
    
    def process_pdf_page_direct(self, pdf_base64, page_num, model_id, max_retries=3):
        """
        Process a single PDF page sent directly as base64
        
        Args:
            pdf_base64: Base64-encoded PDF data
            page_num: Original page number in the source document
            model_id: Model ID to use for OCR
            max_retries: Maximum number of retry attempts
            
        Returns:
            OCR result for the page
        """
        payload = {
            "model": model_id,
            "document": {
                "type": "document_base64",  # Using base64 instead of URL
                "document_base64": pdf_base64,
                "document_name": f"page_{page_num}.pdf",
                "include_image_base64": False
            }
        }
        
        result = self._make_api_request(payload, max_retries)
        
        # Adjust page numbers to match original document
        if result and "pages" in result:
            for page in result["pages"]:
                if "page_num" in page:
                    # The API will return page 0 for a single-page PDF
                    # We need to adjust it to the original page number
                    page["page_num"] = page_num
        
        return result
    
    def process_pdf(self, pdf_path, model_id, max_retries=3):
        """Process a PDF file, handling chunking if necessary"""
        pdf_processor = PDFProcessor()
        
        if pdf_processor.is_pdf_too_large(pdf_path):
            print(f"PDF is too large, splitting into chunks...")
            chunks = pdf_processor.split_pdf(pdf_path)
            return self._process_chunks(chunks, model_id, max_retries)
        else:
            return self._process_single_pdf(pdf_path, model_id, max_retries)
    
    def _process_single_pdf(self, pdf_path, model_id, max_retries=3):
        """Process a single PDF file"""
        payload = {
            "model": model_id,
            "document": {
                "type": "document_url",
                "document_url": self._get_document_url(pdf_path),
                "document_name": os.path.basename(pdf_path),
                "include_image_base64": False
            }
        }
        
        return self._make_api_request(payload, max_retries)
    
    def _process_chunks(self, chunks, model_id, max_retries=3):
        """Process multiple PDF chunks and combine results"""
        combined_results = {
            "text": "",
            "pages": []
        }
        
        for i, chunk in enumerate(chunks):
            print(f"Processing chunk {i+1}/{len(chunks)}...")
            
            payload = {
                "model": model_id,
                "document": {
                    "type": "document_url",
                    "document_url": self._get_document_url(chunk['path']),
                    "document_name": f"chunk_{i+1}",
                    "include_image_base64": False
                }
            }
            
            chunk_result = self._make_api_request(payload, max_retries)
            
            if chunk_result:
                # Adjust page numbers to match original document
                self._adjust_page_numbers(chunk_result, chunk['start_page'])
                
                # Combine results
                combined_results["text"] += chunk_result.get("text", "") + "\n"
                combined_results["pages"].extend(chunk_result.get("pages", []))
            
            # Clean up temporary file
            os.unlink(chunk['path'])
        
        return combined_results
    
    def _make_api_request(self, payload, max_retries=3):
        """Make API request with retry logic"""
        retry_count = 0
        
        while retry_count < max_retries:
            try:
                response = requests.post(
                    f"{self.base_url}/ocr",
                    headers=self.headers,
                    json=payload,
                    timeout=300  # 5-minute timeout for large files
                )
                
                if response.status_code == 200:
                    return response.json()
                elif response.status_code == 413:
                    raise ValueError("File is too large for API processing")
                else:
                    print(f"API error: {response.status_code} - {response.text}")
                    retry_count += 1
                    time.sleep(2 ** retry_count)  # Exponential backoff
            except Exception as e:
                print(f"Request error: {str(e)}")
                retry_count += 1
                time.sleep(2 ** retry_count)
        
        return None
    
    def _adjust_page_numbers(self, result, start_page):
        """Adjust page numbers in the result to match original document"""
        if "pages" in result:
            for page in result["pages"]:
                if "page_num" in page:
                    page["page_num"] += start_page
    
    def _get_document_url(self, pdf_path):
        """
        Convert local file path to a URL the API can access
        This is a placeholder - you'll need to implement file uploading
        to a temporary storage service that provides a URL
        """
        # Placeholder - implement your file upload logic here
        # For example, upload to S3 and return the URL
        pass
    
    # Add this method to your OCRApiClient class
    
    def process_document(self, document_url, document_name, model_id, pages=None, max_retries=3):
        """
        Process a document with optional page range specification
        
        Args:
            document_url: URL to the document
            document_name: Name of the document
            model_id: Model ID to use for OCR
            pages: Optional list of page numbers to process (0-indexed)
            max_retries: Maximum number of retry attempts
        
        Returns:
            OCR result dictionary
        """
        payload = {
            "model": model_id,
            "document": {
                "type": "document_url",
                "document_url": document_url,
                "document_name": document_name,
                "include_image_base64": False
            }
        }
        
        # Add pages parameter if specified
        if pages is not None:
            payload["document"]["pages"] = pages
        
        return self._make_api_request(payload, max_retries)
    
    # Add this method to your OCRApiClient class
    
    def process_document_base64(self, document_base64, document_name, model_id, max_retries=3):
        """
        Process a document with base64 encoding
        
        Args:
            document_base64: Base64-encoded document data
            document_name: Name of the document
            model_id: Model ID to use for OCR
            max_retries: Maximum number of retry attempts
        
        Returns:
            OCR result dictionary
        """
        payload = {
            "model": model_id,
            "document": {
                "type": "document_base64",  # Using base64 instead of URL
                "document_base64": document_base64,
                "document_name": document_name,
                "include_image_base64": False
            }
        }
        
        return self._make_api_request(payload, max_retries)
    
    def process_single_page(self, pdf_path, page_num, model_id, max_retries=3):
        """
        Process a single page from a PDF file
        
        Args:
            pdf_path: Path to the PDF file
            page_num: Page number to process (0-indexed)
            model_id: Model ID to use for OCR
            max_retries: Maximum number of retry attempts
            
        Returns:
            OCR result for the page
        """
        # Extract the page as an image to reduce size
        image_data = self._extract_page_as_image(pdf_path, page_num)
        
        # Convert image to base64
        buffered = io.BytesIO()
        image_data.save(buffered, format="PNG")
        img_base64 = base64.b64encode(buffered.getvalue()).decode('utf-8')
        
        # Process the image
        payload = {
            "model": model_id,
            "document": {
                "type": "image_base64",  # Using image instead of PDF
                "image_base64": img_base64,
                "document_name": f"page_{page_num}.png",
                "include_image_base64": False
            }
        }
        
        result = self._make_api_request(payload, max_retries)
        
        # Adjust page numbers to match original document
        if result and "pages" in result:
            for page in result["pages"]:
                if "page_num" in page:
                    page["page_num"] = page_num
        
        return result
    
    def _extract_page_as_image(self, pdf_path, page_num, dpi=150):  # Reduced DPI from 300 to 150
        """
        Extract a page from a PDF as an image
        
        Args:
            pdf_path: Path to the PDF file
            page_num: Page number to extract (0-indexed)
            dpi: Resolution for the extracted image
            
        Returns:
            PIL Image object
        """
        try:
            # Try using pdf2image if available (better quality)
            from pdf2image import convert_from_path
            images = convert_from_path(pdf_path, dpi=dpi, first_page=page_num+1, last_page=page_num+1)
            return images[0]
        except ImportError:
            # Fallback to a more basic approach
            import fitz  # PyMuPDF
            doc = fitz.open(pdf_path)
            page = doc.load_page(page_num)
            pix = page.get_pixmap(matrix=fitz.Matrix(1.5, 1.5))  # Reduced from 2.0 to 1.5
            img = Image.frombytes("RGB", [pix.width, pix.height], pix.samples)
            return img
        except ImportError:
            # If neither is available, raise an error
            raise ImportError("Please install either pdf2image or PyMuPDF to extract PDF pages as images")
    
    def process_document_in_parts(self, pdf_path, model_id, max_retries=3, callback=None, 
                             chunk_size=5, use_jpeg=True, jpeg_quality=85, 
                             image_dpi=150, single_page_mode=False):
        """
        Process a document page by page and combine results with configurable settings
        
        Args:
            pdf_path: Path to the PDF file
            model_id: Model ID to use for OCR
            max_retries: Maximum number of retry attempts
            callback: Optional callback function for progress updates
            chunk_size: Number of pages per chunk (ignored in single_page_mode)
            use_jpeg: Whether to use JPEG (True) or PNG (False) for images
            jpeg_quality: JPEG quality (0-100) when use_jpeg is True
            image_dpi: DPI for image extraction
            single_page_mode: Process one page at a time if True
            
        Returns:
            Combined OCR result
        """
        # Create a unique session ID for this processing job
        session_id = str(uuid.uuid4())
        
        # Create temporary directory for this session
        temp_dir = tempfile.mkdtemp(prefix=f"ocr_session_{session_id}_")
        progress_file = os.path.join(temp_dir, "progress.json")
        chunks_dir = os.path.join(temp_dir, "chunks")
        results_dir = os.path.join(temp_dir, "results")
        
        os.makedirs(chunks_dir, exist_ok=True)
        os.makedirs(results_dir, exist_ok=True)
        
        try:
            # Get total page count
            with open(pdf_path, 'rb') as file:
                reader = PyPDF2.PdfReader(file)
                total_pages = len(reader.pages)
            
            if callback:
                callback("status", f"PDF has {total_pages} pages. Preparing for processing...")
            
            # Initialize or load progress
            progress = self._initialize_or_load_progress(progress_file, total_pages)
            
            # Split PDF into chunks if needed
            if not progress["chunks_created"]:
                if callback:
                    callback("status", "Splitting PDF into manageable chunks...")
                
                # If single page mode, set chunk_size to 1
                actual_chunk_size = 1 if single_page_mode else chunk_size
                
                chunks = self._split_pdf_into_chunks(pdf_path, chunks_dir, actual_chunk_size)
                progress["chunks"] = chunks
                progress["chunks_created"] = True
                self._save_progress(progress_file, progress)
            
            # Process each chunk
            for i, chunk in enumerate(progress["chunks"]):
                chunk_path = chunk["path"]
                chunk_id = chunk["id"]
                result_path = os.path.join(results_dir, f"result_{chunk_id}.json")
                
                # Skip if already processed
                if chunk_id in progress["processed_chunks"]:
                    if callback:
                        callback("status", f"Chunk {i+1}/{len(progress['chunks'])} already processed. Skipping...")
                    continue
                
                if callback:
                    callback("status", f"Processing chunk {i+1}/{len(progress['chunks'])} (pages {chunk['start_page']+1}-{chunk['end_page']+1})...")
                
                # Process this chunk
                try:
                    # Process with configured settings
                    chunk_result = self._process_chunk_as_images(
                        chunk_path, 
                        chunk["start_page"], 
                        model_id, 
                        max_retries,
                        callback,
                        use_jpeg=use_jpeg,
                        jpeg_quality=jpeg_quality,
                        image_dpi=image_dpi
                    )
                    
                    # Save result
                    with open(result_path, 'w') as f:
                        json.dump(chunk_result, f)
                    
                    # Update progress
                    progress["processed_chunks"].append(chunk_id)
                    self._save_progress(progress_file, progress)
                    
                except Exception as e:
                    if callback:
                        callback("error", f"Error processing chunk {i+1}: {str(e)}")
                    # Continue with next chunk instead of failing completely
            
            # Combine all results
            if callback:
                callback("status", "Combining results...")
            
            combined_result = self._combine_chunk_results(results_dir, progress)
            
            if callback:
                callback("complete", combined_result)
            
            return combined_result
            
        finally:
            # Clean up temporary directory
            try:
                shutil.rmtree(temp_dir)
            except Exception as e:
                print(f"Warning: Failed to clean up temporary directory: {str(e)}")
    
    def _initialize_or_load_progress(self, progress_file, total_pages):
        """Initialize or load progress from file"""
        if os.path.exists(progress_file):
            with open(progress_file, 'r') as f:
                return json.load(f)
        else:
            return {
                "total_pages": total_pages,
                "chunks_created": False,
                "chunks": [],
                "processed_chunks": []
            }
    
    def _save_progress(self, progress_file, progress):
        """Save progress to file"""
        with open(progress_file, 'w') as f:
            json.dump(progress, f)
    
    def _split_pdf_into_chunks(self, pdf_path, chunks_dir, pages_per_chunk):
        """Split PDF into chunks and save them to disk"""
        chunks = []
        
        with open(pdf_path, 'rb') as file:
            reader = PyPDF2.PdfReader(file)
            total_pages = len(reader.pages)
            
            # Calculate number of chunks needed
            num_chunks = (total_pages + pages_per_chunk - 1) // pages_per_chunk
            
            for i in range(num_chunks):
                start_page = i * pages_per_chunk
                end_page = min((i + 1) * pages_per_chunk - 1, total_pages - 1)
                
                # Create a new PDF writer for this chunk
                writer = PyPDF2.PdfWriter()
                
                # Add pages to the chunk
                for page_num in range(start_page, end_page + 1):
                    writer.add_page(reader.pages[page_num])
                
                # Generate a unique ID for this chunk
                chunk_id = f"chunk_{i}_{start_page}_{end_page}"
                chunk_path = os.path.join(chunks_dir, f"{chunk_id}.pdf")
                
                # Save the chunk
                with open(chunk_path, 'wb') as output_file:
                    writer.write(output_file)
                
                chunks.append({
                    "id": chunk_id,
                    "path": chunk_path,
                    "start_page": start_page,
                    "end_page": end_page
                })
        
        return chunks
    
    def _process_chunk_as_images(self, chunk_path, start_page, model_id, max_retries=3, callback=None,
                            use_jpeg=True, jpeg_quality=85, image_dpi=150):
        """Process a chunk by converting each page to an image with configurable settings"""
        # Get page count for this chunk
        with open(chunk_path, 'rb') as file:
            reader = PyPDF2.PdfReader(file)
            chunk_pages = len(reader.pages)
        
        results = []
        
        for i in range(chunk_pages):
            actual_page = start_page + i
            
            if callback:
                callback("status", f"Processing page {actual_page+1} as image...")
            
            # Extract page as image with configurable DPI
            image_data = self._extract_page_as_image(chunk_path, i, dpi=image_dpi)
            
            # Convert image to base64 using configured format and quality
            buffered = io.BytesIO()
            
            if use_jpeg:
                # Use JPEG with configurable quality
                image_data.save(buffered, format="JPEG", quality=jpeg_quality)
            else:
                # Use PNG (lossless)
                image_data.save(buffered, format="PNG")
                
            img_base64 = base64.b64encode(buffered.getvalue()).decode('utf-8')
            
            # Check if base64 size is too large (>4MB)
            if len(img_base64) > 4 * 1024 * 1024:
                # Try with lower quality or size reduction
                if use_jpeg:
                    # Reduce quality first
                    reduced_quality = max(40, jpeg_quality - 20)
                    buffered = io.BytesIO()
                    image_data.save(buffered, format="JPEG", quality=reduced_quality)
                    img_base64 = base64.b64encode(buffered.getvalue()).decode('utf-8')
                
                # If still too large, reduce dimensions
                if len(img_base64) > 4 * 1024 * 1024:
                    new_width = int(image_data.width * 0.75)
                    new_height = int(image_data.height * 0.75)
                    resized_img = image_data.resize((new_width, new_height), Image.LANCZOS)
                    
                    buffered = io.BytesIO()
                    if use_jpeg:
                        resized_img.save(buffered, format="JPEG", quality=reduced_quality)
                    else:
                        resized_img.save(buffered, format="PNG")
                        
                    img_base64 = base64.b64encode(buffered.getvalue()).decode('utf-8')
            
            # Process the image
            payload = {
                "model": model_id,
                "document": {
                    "type": "image_base64",
                    "image_base64": img_base64,
                    "document_name": f"page_{actual_page}.{'jpg' if use_jpeg else 'png'}",
                    "include_image_base64": False
                }
            }
            
            # Add retry logic specifically for 413 errors
            retry_count = 0
            result = None
            
            while retry_count < max_retries:
                try:
                    result = self._make_api_request(payload, 1)  # Single attempt per loop
                    break  # Success, exit loop
                except ValueError as e:
                    if "413" in str(e) and retry_count < max_retries - 1:
                        # Try with even lower quality on 413 error
                        if callback:
                            callback("status", f"Reducing image quality for page {actual_page+1}...")
                        
                        # Reduce image size by 25% each retry
                        new_width = int(image_data.width * (0.75 ** (retry_count + 1)))
                        new_height = int(image_data.height * (0.75 ** (retry_count + 1)))
                        resized_img = image_data.resize((new_width, new_height), Image.LANCZOS)
                        
                        buffered = io.BytesIO()
                        if use_jpeg:
                            # Reduce quality with each retry
                            reduced_quality = max(30, jpeg_quality - (20 * (retry_count + 1)))
                            resized_img.save(buffered, format="JPEG", quality=reduced_quality)
                        else:
                            # Switch to JPEG if PNG is too large
                            resized_img.save(buffered, format="JPEG", quality=60)
                            
                        img_base64 = base64.b64encode(buffered.getvalue()).decode('utf-8')
                        
                        # Update payload with smaller image
                        payload["document"]["image_base64"] = img_base64
                        payload["document"]["document_name"] = f"page_{actual_page}.jpg"  # Switch to jpg
                        
                        retry_count += 1
                    else:
                        raise  # Re-raise if not a 413 error or last retry
                except Exception as e:
                    if retry_count < max_retries - 1:
                        retry_count += 1
                        time.sleep(2 ** retry_count)
                    else:
                        raise
            
            # Adjust page numbers to match original document
            if result and "pages" in result:
                for page in result["pages"]:
                    if "page_num" in page:
                        page["page_num"] = actual_page
            
            if result:
                results.append(result)
        
        # Combine results from this chunk
        return self._combine_results(results)
    
    def _combine_chunk_results(self, results_dir, progress):
        """Combine results from all processed chunks"""
        results = []
        
        for chunk_id in progress["processed_chunks"]:
            result_path = os.path.join(results_dir, f"result_{chunk_id}.json")
            if os.path.exists(result_path):
                with open(result_path, 'r') as f:
                    results.append(json.load(f))
        
        return self._combine_results(results)
    
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