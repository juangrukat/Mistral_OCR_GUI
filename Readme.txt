# Mistral OCR Application

## Overview

Mistral OCR is a desktop application that allows you to extract text from PDF documents using Mistral AI's OCR (Optical Character Recognition) capabilities. The application converts PDF files into markdown format, preserving the document's structure, formatting, and mathematical notations. It features robust error handling, checkpoint functionality for large documents, and advanced processing options.

## Features

- Process single or multiple PDF files at once
- Drag and drop interface for easy file selection
- Secure API key storage
- Progress tracking for batch processing
- Converts PDFs to well-formatted markdown files
- Checkpoint system for resuming interrupted processing
- Rate limiting to prevent API throttling
- Advanced image processing options
- Support for large documents with page-by-page processing

## Requirements

- Python 3.8 or higher
- Mistral AI API key (obtain from [https://mistral.ai](https://mistral.ai))
- Required Python packages (see Installation section)

## Installation

1. Clone or download this repository to your local machine
2. Install the required dependencies:

```bash
pip install -r requirements.txt
```

## Getting Started

### Obtaining a Mistral API Key

1. Sign up for an account at [https://mistral.ai](https://mistral.ai)
2. Navigate to your account settings or API section
3. Generate a new API key
4. Copy the API key for use in the application

### Running the Application

Launch the application by running:

```bash
python mistral_ocr_gui.py
```

### Using the Application

1. **Enter your API Key**
   - Enter your Mistral API key in the designated field
   - Click "Save Key" to securely store it for future use

2. **Select PDF Files**
   - Drag and drop PDF files onto the drop area, or
   - Click "Select PDF File" to choose individual files, or
   - Click "Select PDF Folder" to process all PDFs in a folder

3. **Choose Output Directory**
   - Click "Browse..." to select where the markdown files will be saved

4. **Configure Advanced Settings (Optional)**
   - Enable the "Advanced Settings" checkbox to access additional options
   - Adjust chunk size for processing multi-page documents
   - Toggle JPEG/PNG image format and quality settings
   - Set image DPI for optimal OCR results
   - Enable single-page mode for processing very large documents

5. **Process Files**
   - Click "Process Files" to start the OCR conversion
   - The progress bar will show the current status
   - You can cancel the process at any time by clicking "Cancel"

6. **View Results**
   - Once processing is complete, the markdown files will be available in your selected output directory
   - Each PDF will have a corresponding markdown file with the same name

## Checkpoint System

The application includes a checkpoint system that saves progress during processing:

- For large documents processed page-by-page, each page is saved as it completes
- If processing is interrupted (by error, cancellation, or application crash), it can be resumed from the last successful page
- Checkpoint files are stored in a directory named `{pdf_name}_checkpoints` alongside the original PDF
- This ensures that long-running jobs (e.g., 2000-page documents) can be safely processed over multiple sessions

## Troubleshooting

- **API Key Issues**: Ensure your API key is correct and has the necessary permissions
- **Processing Errors**: Check that your PDF files are not corrupted and are readable
- **Output Problems**: Make sure the output directory exists and you have write permissions
- **Rate Limiting**: If you encounter "429 Too Many Requests" errors, the application will automatically retry with increased delays
- **Large Files**: For very large PDFs, enable single-page mode in advanced settings

## Advanced Usage

The application handles complex document structures including:
- Mathematical notations and formulas
- Tables and lists
- Footnotes and references
- Special formatting

Advanced processing options allow you to:
- Optimize image quality vs. processing speed
- Adjust DPI settings for better OCR results with different document types
- Process documents page-by-page to handle very large files
- Control chunk size for batch processing

## Technical Details

The application uses:
- Mistral AI's OCR API for text extraction
- Python's markdown library for text processing
- PySide6 for the graphical user interface
- Keyring for secure API key storage
- PyMuPDF and Pillow for PDF and image processing
- Tempfile for managing temporary files during processing

## License

This software is provided as-is under the MIT License + Juan License.
Juan License means you must: 
State that some Juan wrote this code.

