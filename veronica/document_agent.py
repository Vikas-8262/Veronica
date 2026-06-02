"""Local Document Chat (RAG) agent for Veronica."""

import importlib
import os
from pathlib import Path
from .skills import AssistantContext, SkillResult
from .memory_manager import MemoryManager

def _optional_module(module_name: str):
    try:
        return importlib.import_module(module_name)
    except ImportError:
        return None

def is_doc_request(message: str) -> bool:
    """Matcher for Document RAG requests."""
    lowered = message.lower().strip()
    return lowered.startswith(("read file", "ingest document", "summarize pdf", "read document"))

def handle_doc_request(message: str, context: AssistantContext) -> SkillResult:
    """Handler to read a local file and ingest it into ChromaDB."""
    PyPDF2 = _optional_module("PyPDF2")
    if PyPDF2 is None:
        return SkillResult(True, "Document reading requires 'PyPDF2'. Run: pip install PyPDF2")

    lowered = message.lower().strip()
    
    # Extract file path
    file_path_str = ""
    for prefix in ["read file", "ingest document", "summarize pdf", "read document"]:
        if lowered.startswith(prefix):
            # We take from the original message to preserve case
            file_path_str = message[len(prefix):].strip()
            break
            
    # Remove quotes
    file_path_str = file_path_str.strip('"').strip("'")
    
    if not file_path_str:
        return SkillResult(True, "Please provide the full path to the document. Example: 'read file C:\\documents\\report.pdf'")
        
    path = Path(file_path_str)
    if not path.exists() or not path.is_file():
        return SkillResult(True, f"File not found at path: {path.absolute()}")
        
    try:
        text = ""
        ext = path.suffix.lower()
        
        if ext == ".pdf":
            with open(path, "rb") as f:
                reader = PyPDF2.PdfReader(f)
                for page in reader.pages:
                    page_text = page.extract_text()
                    if page_text:
                        text += page_text + "\n"
        elif ext in [".txt", ".md", ".csv", ".json", ".py", ".html"]:
            with open(path, "r", encoding="utf-8", errors="ignore") as f:
                text = f.read()
        else:
            return SkillResult(True, f"Unsupported file type: {ext}. I can currently read .pdf, .txt, .md, .csv, and code files.")
            
        if not text.strip():
            return SkillResult(True, "Could not extract any text from the document. It might be empty or a scanned image.")
            
        # Initialize Memory Manager to ingest chunks
        memory = MemoryManager(context.data_dir)
        
        # Simple chunking logic (roughly 1500 chars per chunk)
        chunk_size = 1500
        chunks = [text[i:i+chunk_size] for i in range(0, len(text), chunk_size)]
        
        for i, chunk in enumerate(chunks):
            # Save into the vector DB
            doc_context = f"Excerpt from document {path.name}: " + chunk
            memory.save_memory(f"Document {path.name} Context Part {i+1}", doc_context)
            
        return SkillResult(True, f"Successfully read and memorized '{path.name}' ({len(chunks)} chunks). You can now ask me questions about it!")
        
    except Exception as e:
        return SkillResult(True, f"An error occurred while reading the document: {e}")
