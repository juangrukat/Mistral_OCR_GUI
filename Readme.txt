# Mistral OCR Application

## Overview

Mistral OCR is a desktop application that allows you to extract text from PDF documents using Mistral AI's OCR (Optical Character Recognition) capabilities. The application converts PDF files into markdown format, preserving the document's structure, formatting, and mathematical notations.

## Features

- Process single or multiple PDF files at once
- Drag and drop interface for easy file selection
- Secure API key storage
- Progress tracking for batch processing
- Converts PDFs to well-formatted markdown files

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

4. **Process Files**
   - Click "Process Files" to start the OCR conversion
   - The progress bar will show the current status
   - You can cancel the process at any time by clicking "Cancel"

5. **View Results**
   - Once processing is complete, the markdown files will be available in your selected output directory
   - Each PDF will have a corresponding markdown file with the same name

## Troubleshooting

- **API Key Issues**: Ensure your API key is correct and has the necessary permissions
- **Processing Errors**: Check that your PDF files are not corrupted and are readable
- **Output Problems**: Make sure the output directory exists and you have write permissions

## Advanced Usage

The application handles complex document structures including:
- Mathematical notations and formulas
- Tables and lists
- Footnotes and references
- Special formatting

## Technical Details

The application uses:
- Mistral AI's OCR API for text extraction
- Python's markdown library for text processing
- PySide6 for the graphical user interface
- Keyring for secure API key storage

## License

This software is provided as-is under the MIT License.