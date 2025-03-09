from mistralai import Mistral
import os
import argparse
import sys
from pathlib import Path

def process_pdf(api_key, pdf_path, output_path=None):
    """Process a PDF file with Mistral OCR and save the extracted text as markdown."""
    client = Mistral(api_key=api_key)
    
    # Determine output path if not provided
    if output_path is None:
        output_path = Path(pdf_path).with_suffix('.md')
    
    # Upload the PDF file
    with open(pdf_path, "rb") as pdf_file:
        uploaded_pdf = client.files.upload(
            file={
                "file_name": Path(pdf_path).name,
                "content": pdf_file,
            },
            purpose="ocr"
        )
    print(f"File uploaded successfully. File ID: {uploaded_pdf.id}")

    # Get signed URL for the uploaded file
    signed_url = client.files.get_signed_url(file_id=uploaded_pdf.id)
    
    # Process the document with OCR using the signed URL
    ocr_response = client.ocr.process(
        model="mistral-ocr-latest",
        document={
            "type": "document_url",
            "document_url": signed_url.url,
        }
    )

    # Extract and combine markdown content from all pages
    markdown_content = ""
    for page in ocr_response.pages:
        markdown_content += page.markdown + "\n\n"

    # Save the markdown content to a file
    with open(output_path, "w", encoding="utf-8") as f:
        f.write(markdown_content)

    print(f"\nOCR Results saved to {output_path}")
    return output_path

def main():
    parser = argparse.ArgumentParser(description='Process PDF files with Mistral OCR')
    parser.add_argument('pdf_path', help='Path to the PDF file')
    parser.add_argument('--output', '-o', help='Output path for the markdown file')
    parser.add_argument('--api-key', help='Mistral API key (if not set in environment)')
    
    args = parser.parse_args()
    
    # Get API key from args or environment
    api_key = args.api_key or os.environ.get("MISTRAL_API_KEY")
    if not api_key:
        print("Error: Mistral API key not provided. Set MISTRAL_API_KEY environment variable or use --api-key")
        sys.exit(1)
    
    process_pdf(api_key, args.pdf_path, args.output)

if __name__ == "__main__":
    main()