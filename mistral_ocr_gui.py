import sys
import os
from pathlib import Path
import json
from functools import partial
import keyring
import threading
import markdown
from markdown.extensions import Extension
import re

from PySide6.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout, 
                              QHBoxLayout, QPushButton, QLabel, QLineEdit, 
                              QFileDialog, QProgressBar, QMessageBox, QListWidget)
from PySide6.QtCore import Qt, Signal, QObject, Slot
from PySide6.QtGui import QDragEnterEvent, QDropEvent

from mistralai import Mistral

# Import the process_pdf function from oo.py
from oo import process_pdf

# Constants
APP_NAME = "MistralOCR"
SERVICE_NAME = "MistralOCR"
API_KEY_NAME = "mistral_api_key"

def process_markdown(markdown_text):
    """
    Process and clean markdown text from Mistral API response using the markdown library.
    
    Args:
        markdown_text (str): Raw markdown text from API response
        
    Returns:
        str: Cleaned and formatted markdown text
    """
    # Fix common issues in the markdown before processing
    
    # Fix section headers (ensure space after #)
    markdown_text = re.sub(r'(^|\n)#([^#\s])', r'\1# \2', markdown_text)
    
    # Fix list formatting (ensure space after * or -)
    markdown_text = re.sub(r'(^|\n)[*-]([^\s])', r'\1* \2', markdown_text)
    
    # Ensure proper line breaks before and after section headers
    markdown_text = re.sub(r'([^\n])\n(#+\s)', r'\1\n\n\2', markdown_text)
    markdown_text = re.sub(r'(#+\s.*?)\n([^\n#])', r'\1\n\n\2', markdown_text)
    
    # Create markdown processor with extensions
    md = markdown.Markdown(extensions=[
        'markdown.extensions.extra',       # Tables, footnotes, etc.
        'markdown.extensions.codehilite',  # Code highlighting
        'markdown.extensions.smarty',      # Smart quotes, dashes, etc.
        'markdown.extensions.toc',         # Table of contents
        'markdown.extensions.nl2br',       # Line breaks
    ])
    
    # Convert to HTML and back to markdown to normalize formatting
    # This step is optional and can be removed if not needed
    html = md.convert(markdown_text)
    
    # Return the processed markdown
    return markdown_text

class WorkerSignals(QObject):
    """Defines the signals available from the worker thread."""
    progress = Signal(int, str)
    finished = Signal()
    error = Signal(str)

class OCRWorker(threading.Thread):
    """Worker thread for OCR processing."""
    def __init__(self, api_key, files, output_dir):
        super().__init__()
        self.api_key = api_key
        self.files = files
        self.output_dir = output_dir
        self.signals = WorkerSignals()
        self.stop_event = threading.Event()
        self.daemon = True
        
    def run(self):
        try:
            total_files = len(self.files)
            
            for i, pdf_path in enumerate(self.files):
                if self.stop_event.is_set():
                    break
                
                pdf_name = Path(pdf_path).stem
                output_path = Path(self.output_dir) / f"{pdf_name}.md"
                
                self.signals.progress.emit(int((i / total_files) * 100), f"Processing {pdf_name}...")
                
                # Use the process_pdf function from oo.py
                result_path = process_pdf(self.api_key, pdf_path, str(output_path))
                
                # Process the markdown file to clean and format it
                with open(result_path, 'r', encoding='utf-8') as f:
                    markdown_content = f.read()
                
                processed_markdown = process_markdown(markdown_content)
                
                # Save the processed markdown
                with open(result_path, 'w', encoding='utf-8') as f:
                    f.write(processed_markdown)
                
                if self.stop_event.is_set():
                    break
                
                self.signals.progress.emit(int(((i + 1) / total_files) * 100), f"Saved {output_path}")
            
            if not self.stop_event.is_set():
                self.signals.progress.emit(100, "All files processed successfully!")
            self.signals.finished.emit()
            
        except Exception as e:
            self.signals.error.emit(str(e))
            self.signals.finished.emit()
    
    def stop(self):
        self.stop_event.set()

class DropArea(QWidget):
    """Widget that accepts file drops."""
    filesDropped = Signal(list)
    
    def __init__(self):
        super().__init__()
        self.setAcceptDrops(True)
        layout = QVBoxLayout()
        self.label = QLabel("Drop PDF files here or use the buttons below")
        self.label.setAlignment(Qt.AlignCenter)
        layout.addWidget(self.label)
        self.setLayout(layout)
        self.setMinimumHeight(100)
        self.setStyleSheet("border: 2px dashed #aaa; border-radius: 5px;")
    
    def dragEnterEvent(self, event: QDragEnterEvent):
        if event.mimeData().hasUrls():
            event.acceptProposedAction()
    
    def dropEvent(self, event: QDropEvent):
        file_paths = []
        for url in event.mimeData().urls():
            path = url.toLocalFile()
            if path.lower().endswith('.pdf'):
                file_paths.append(path)
        
        if file_paths:
            self.filesDropped.emit(file_paths)

class MistralOCRApp(QMainWindow):
    """Main application window."""
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Mistral OCR")
        self.resize(800, 600)
        
        self.worker = None
        self.setup_ui()
        self.load_api_key()
    
    def setup_ui(self):
        central_widget = QWidget()
        main_layout = QVBoxLayout(central_widget)
        
        # API Key section
        api_key_layout = QHBoxLayout()
        api_key_layout.addWidget(QLabel("API Key:"))
        self.api_key_input = QLineEdit()
        self.api_key_input.setEchoMode(QLineEdit.Password)
        api_key_layout.addWidget(self.api_key_input)
        save_key_btn = QPushButton("Save Key")
        save_key_btn.clicked.connect(self.save_api_key)
        api_key_layout.addWidget(save_key_btn)
        main_layout.addLayout(api_key_layout)
        
        # Drop area
        self.drop_area = DropArea()
        self.drop_area.filesDropped.connect(self.add_files)
        main_layout.addWidget(self.drop_area)
        
        # File list
        main_layout.addWidget(QLabel("Selected Files:"))
        self.file_list = QListWidget()
        main_layout.addWidget(self.file_list)
        
        # Buttons for file selection
        file_buttons_layout = QHBoxLayout()
        select_file_btn = QPushButton("Select PDF File")
        select_file_btn.clicked.connect(self.select_pdf_file)
        file_buttons_layout.addWidget(select_file_btn)
        
        select_folder_btn = QPushButton("Select PDF Folder")
        select_folder_btn.clicked.connect(self.select_pdf_folder)
        file_buttons_layout.addWidget(select_folder_btn)
        
        clear_files_btn = QPushButton("Clear Files")
        clear_files_btn.clicked.connect(self.clear_files)
        file_buttons_layout.addWidget(clear_files_btn)
        main_layout.addLayout(file_buttons_layout)
        
        # Output directory
        output_layout = QHBoxLayout()
        output_layout.addWidget(QLabel("Output Directory:"))
        self.output_dir_input = QLineEdit()
        output_layout.addWidget(self.output_dir_input)
        select_output_btn = QPushButton("Browse...")
        select_output_btn.clicked.connect(self.select_output_dir)
        output_layout.addWidget(select_output_btn)
        main_layout.addLayout(output_layout)
        
        # Progress bar
        main_layout.addWidget(QLabel("Progress:"))
        self.progress_bar = QProgressBar()
        main_layout.addWidget(self.progress_bar)
        self.status_label = QLabel("Ready")
        main_layout.addWidget(self.status_label)
        
        # Process buttons
        process_layout = QHBoxLayout()
        self.process_btn = QPushButton("Process Files")
        self.process_btn.clicked.connect(self.process_files)
        process_layout.addWidget(self.process_btn)
        
        self.cancel_btn = QPushButton("Cancel")
        self.cancel_btn.clicked.connect(self.cancel_processing)
        self.cancel_btn.setEnabled(False)
        process_layout.addWidget(self.cancel_btn)
        main_layout.addLayout(process_layout)
        
        self.setCentralWidget(central_widget)
    
    def load_api_key(self):
        """Load API key from keyring."""
        try:
            api_key = keyring.get_password(SERVICE_NAME, API_KEY_NAME)
            if api_key:
                self.api_key_input.setText(api_key)
        except Exception as e:
            QMessageBox.warning(self, "Warning", f"Could not load API key: {str(e)}")
    
    def save_api_key(self):
        """Save API key to keyring."""
        api_key = self.api_key_input.text().strip()
        if not api_key:
            QMessageBox.warning(self, "Warning", "Please enter an API key")
            return
        
        try:
            keyring.set_password(SERVICE_NAME, API_KEY_NAME, api_key)
            QMessageBox.information(self, "Success", "API key saved securely")
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Could not save API key: {str(e)}")
    
    def select_pdf_file(self):
        """Open file dialog to select a PDF file."""
        file_paths, _ = QFileDialog.getOpenFileNames(
            self, "Select PDF Files", "", "PDF Files (*.pdf)"
        )
        if file_paths:
            self.add_files(file_paths)
    
    def select_pdf_folder(self):
        """Open folder dialog to select a folder with PDF files."""
        folder_path = QFileDialog.getExistingDirectory(
            self, "Select Folder with PDF Files"
        )
        if folder_path:
            pdf_files = []
            for file in Path(folder_path).glob("*.pdf"):
                pdf_files.append(str(file))
            
            if pdf_files:
                self.add_files(pdf_files)
            else:
                QMessageBox.information(self, "Information", "No PDF files found in the selected folder")
    
    def select_output_dir(self):
        """Open folder dialog to select output directory."""
        folder_path = QFileDialog.getExistingDirectory(
            self, "Select Output Directory"
        )
        if folder_path:
            self.output_dir_input.setText(folder_path)
    
    def add_files(self, file_paths):
        """Add files to the list."""
        for file_path in file_paths:
            # Check if file is already in the list
            items = [self.file_list.item(i).text() for i in range(self.file_list.count())]
            if file_path not in items:
                self.file_list.addItem(file_path)
    
    def clear_files(self):
        """Clear the file list."""
        self.file_list.clear()
    
    def process_files(self):
        """Start processing the selected files."""
        api_key = self.api_key_input.text().strip()
        if not api_key:
            QMessageBox.warning(self, "Warning", "Please enter an API key")
            return
        
        if self.file_list.count() == 0:
            QMessageBox.warning(self, "Warning", "Please select at least one PDF file")
            return
        
        output_dir = self.output_dir_input.text().strip()
        if not output_dir:
            QMessageBox.warning(self, "Warning", "Please select an output directory")
            return
        
        if not os.path.isdir(output_dir):
            QMessageBox.warning(self, "Warning", "The selected output directory does not exist")
            return
        
        # Get all files from the list
        files = [self.file_list.item(i).text() for i in range(self.file_list.count())]
        
        # Disable UI elements during processing
        self.process_btn.setEnabled(False)
        self.cancel_btn.setEnabled(True)
        self.progress_bar.setValue(0)
        self.status_label.setText("Starting processing...")
        
        # Start worker thread
        self.worker = OCRWorker(api_key, files, output_dir)
        self.worker.signals.progress.connect(self.update_progress)
        self.worker.signals.finished.connect(self.processing_finished)
        self.worker.signals.error.connect(self.processing_error)
        self.worker.start()
    
    def cancel_processing(self):
        """Cancel the current processing."""
        if self.worker and self.worker.is_alive():
            self.status_label.setText("Cancelling...")
            self.worker.stop()
    
    @Slot(int, str)
    def update_progress(self, value, message):
        """Update progress bar and status message."""
        self.progress_bar.setValue(value)
        self.status_label.setText(message)
    
    @Slot()
    def processing_finished(self):
        """Handle processing completion."""
        self.process_btn.setEnabled(True)
        self.cancel_btn.setEnabled(False)
        self.worker = None
    
    @Slot(str)
    def processing_error(self, error_message):
        """Handle processing error."""
        QMessageBox.critical(self, "Error", f"An error occurred: {error_message}")
        self.status_label.setText(f"Error: {error_message}")
        self.process_btn.setEnabled(True)
        self.cancel_btn.setEnabled(False)

def main():
    app = QApplication(sys.argv)
    window = MistralOCRApp()
    window.show()
    sys.exit(app.exec())

if __name__ == "__main__":
    main()