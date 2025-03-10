import os
import tempfile
from pathlib import Path
import base64
from mistralai import Mistral
import fitz  # PyMuPDF
from PIL import Image
import io
import time

def process_pdf(api_key, pdf_path, output_path, page_by_page=False, chunk_size=5, 
                use_jpeg=True, jpeg_quality=85, image_dpi=150):
    """
    Process a PDF file using Mistral AI's OCR capabilities.
    
    Args:
        api_key (str): Mistral API key
        pdf_path (str): Path to the PDF file
        output_path (str): Path to save the output markdown file
        page_by_page (bool): Whether to process one page at a time
        chunk_size (int): Number of pages to process at once
        use_jpeg (bool): Whether to use JPEG (True) or PNG (False)
        jpeg_quality (int): JPEG quality (40-95)
        image_dpi (int): Image DPI (72-300)
        
    Returns:
        str: Path to the output markdown file
    """
    # Check for existing complete checkpoint
    pdf_dir = os.path.dirname(pdf_path)
    pdf_name = Path(pdf_path).stem
    checkpoint_dir = os.path.join(pdf_dir, f"{pdf_name}_checkpoints")
    complete_checkpoint = os.path.join(checkpoint_dir, f"{pdf_name}_complete.md")
    
    if os.path.exists(complete_checkpoint):
        # Use the existing complete checkpoint
        with open(complete_checkpoint, 'r', encoding='utf-8') as f:
            result = f.read()
    else:
        client = Mistral(api_key=api_key)
        
        # Create output directory if it doesn't exist
        output_dir = os.path.dirname(output_path)
        if output_dir and not os.path.exists(output_dir):
            os.makedirs(output_dir)
        
        # Process the PDF using the new OCR API
        if page_by_page:
            result = process_pdf_page_by_page_ocr(client, pdf_path)
        else:
            # Check if we need to process in chunks
            doc = fitz.open(pdf_path)
            total_pages = len(doc)
            doc.close()
            
            if total_pages > 1:
                # Use the OCR API directly with the PDF file
                result = process_pdf_with_ocr_api(client, pdf_path)
            else:
                result = process_pdf_with_ocr_api(client, pdf_path)
    
    # Save the result to the output file
    with open(output_path, 'w', encoding='utf-8') as f:
        f.write(result)
    
    return output_path

def process_pdf_with_ocr_api(client, pdf_path):
    """Process the PDF using Mistral's OCR API."""
    # Create a temporary file URL or use base64 encoding
    with open(pdf_path, 'rb') as f:
        pdf_bytes = f.read()
    
    # Convert to base64
    pdf_base64 = base64.b64encode(pdf_bytes).decode('utf-8')
    
    # Call the OCR API with the correct format
    response = client.ocr.process(
        model="mistral-ocr-latest",
        document={
            "type": "document_url",
            "document_url": f"data:application/pdf;base64,{pdf_base64}"
        }
    )
    
    # Extract the text content from the structured response
    if hasattr(response, 'pages') and response.pages:
        # Combine markdown from all pages
        result = []
        for page in response.pages:
            if hasattr(page, 'markdown'):
                result.append(page.markdown)
        return "\n\n".join(result)
    elif hasattr(response, 'text'):
        return response.text
    else:
        # Handle different response structure if needed
        return str(response)

def process_pdf_page_by_page_ocr(client, pdf_path):
    """Process the PDF one page at a time using OCR API."""
    doc = fitz.open(pdf_path)
    results = []
    
    # Create a checkpoint directory in the same folder as the PDF
    pdf_dir = os.path.dirname(pdf_path)
    pdf_name = Path(pdf_path).stem
    checkpoint_dir = os.path.join(pdf_dir, f"{pdf_name}_checkpoints")
    os.makedirs(checkpoint_dir, exist_ok=True)
    
    # Add rate limiting delay (in seconds)
    rate_limit_delay = 1.0  # 1 second delay between requests
    
    # Check for existing checkpoints
    existing_pages = []
    for filename in os.listdir(checkpoint_dir):
        if filename.startswith(f"{pdf_name}_page_") and filename.endswith(".md"):
            try:
                page_num = int(filename.replace(f"{pdf_name}_page_", "").replace(".md", ""))
                existing_pages.append(page_num)
            except ValueError:
                continue
    
    for page_num in range(len(doc)):
        # Check if we already have this page processed
        checkpoint_file = os.path.join(checkpoint_dir, f"{pdf_name}_page_{page_num}.md")
        if page_num in existing_pages:
            # Load existing checkpoint
            with open(checkpoint_file, 'r', encoding='utf-8') as f:
                page_content = f.read()
                results.append(page_content)
            continue
            
        # Extract the page as a separate PDF
        with tempfile.NamedTemporaryFile(suffix='.pdf', delete=False) as temp_file:
            temp_path = temp_file.name
        
        # Create a new PDF with just this page
        new_doc = fitz.open()
        new_doc.insert_pdf(doc, from_page=page_num, to_page=page_num)
        new_doc.save(temp_path)
        new_doc.close()
        
        # Process this single page
        with open(temp_path, 'rb') as f:
            pdf_bytes = f.read()
        
        # Convert to base64
        pdf_base64 = base64.b64encode(pdf_bytes).decode('utf-8')
        
        # Add delay before making the API request (except for the first request)
        if page_num > 0:
            time.sleep(rate_limit_delay)
        
        # Call the OCR API with the correct format
        try:
            response = client.ocr.process(
                model="mistral-ocr-latest",
                document={
                    "type": "document_url",
                    "document_url": f"data:application/pdf;base64,{pdf_base64}"
                },
                pages=[0]  # Only process the first page (since we extracted just one)
            )
            
            # Extract the text content from the structured response
            page_content = ""
            if hasattr(response, 'pages') and response.pages:
                for page in response.pages:
                    if hasattr(page, 'markdown'):
                        page_content = page.markdown
                        break
            elif hasattr(response, 'text'):
                page_content = response.text
            else:
                # Handle different response structure if needed
                page_content = str(response)
            
            # Save checkpoint for this page
            with open(checkpoint_file, 'w', encoding='utf-8') as f:
                f.write(page_content)
                
            results.append(page_content)
                
        except Exception as e:
            if "429" in str(e):  # Rate limit error
                # Wait longer and retry once
                time.sleep(rate_limit_delay * 2)  # Double the delay for retry
                response = client.ocr.process(
                    model="mistral-ocr-latest",
                    document={
                        "type": "document_url",
                        "document_url": f"data:application/pdf;base64,{pdf_base64}"
                    },
                    pages=[0]
                )
                
                page_content = ""
                if hasattr(response, 'pages') and response.pages:
                    for page in response.pages:
                        if hasattr(page, 'markdown'):
                            page_content = page.markdown
                            break
                elif hasattr(response, 'text'):
                    page_content = response.text
                else:
                    page_content = str(response)
                
                # Save checkpoint for this page
                with open(checkpoint_file, 'w', encoding='utf-8') as f:
                    f.write(page_content)
                    
                results.append(page_content)
            else:
                raise e
        
        # Clean up
        os.unlink(temp_path)
    
    # Combine all page results
    combined_result = "\n\n".join(results)
    
    # Save the combined result as a final checkpoint
    final_checkpoint = os.path.join(checkpoint_dir, f"{pdf_name}_complete.md")
    with open(final_checkpoint, 'w', encoding='utf-8') as f:
        f.write(combined_result)
    
    return combined_result