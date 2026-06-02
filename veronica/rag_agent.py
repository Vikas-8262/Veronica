"""Local RAG (Retrieval-Augmented Generation) Agent for Veronica.

Supports:
- Indexing folders (scanning .txt, .md, .pdf files)
- Text chunking (with overlap)
- Storing vectors in ChromaDB (using Gemini text-embedding-004)
- Answering questions by retrieving relevant context and generating a cited response via Gemini.
"""

import os
import re
import uuid
import datetime
import importlib
from pathlib import Path
from .skills import AssistantContext, SkillResult

def _optional_module(module_name: str):
    try:
        return importlib.import_module(module_name)
    except ImportError:
        return None

# ──────────────────────────────────────────────
# Matcher
# ──────────────────────────────────────────────
def is_rag_request(message: str) -> bool:
    lowered = message.lower().strip()
    return (
        lowered.startswith("index folder")
        or lowered.startswith("index directory")
        or lowered.startswith("index documents")
        or lowered.startswith("ask my documents")
        or lowered.startswith("ask documents")
        or lowered.startswith("ask my rag")
        or lowered.startswith("ask rag")
        or lowered.startswith("list indexed")
    )

# ──────────────────────────────────────────────
# File Readers
# ──────────────────────────────────────────────
def _read_text_file(path: Path) -> str:
    try:
        return path.read_text(encoding="utf-8", errors="ignore")
    except Exception:
        return ""

def _read_pdf_file(path: Path) -> str:
    pypdf = _optional_module("PyPDF2")
    if not pypdf:
        return ""
    try:
        text = []
        with open(path, "rb") as f:
            reader = pypdf.PdfReader(f)
            for page in reader.pages:
                t = page.extract_text()
                if t:
                    text.append(t)
        return "\n".join(text)
    except Exception:
        return ""

# ──────────────────────────────────────────────
# Chunking Helper
# ──────────────────────────────────────────────
def _chunk_text(text: str, chunk_size: int = 1000, overlap: int = 150) -> list[str]:
    chunks = []
    start = 0
    text_len = len(text)
    while start < text_len:
        end = start + chunk_size
        chunk = text[start:end]
        chunks.append(chunk)
        start += (chunk_size - overlap)
    return [c.strip() for c in chunks if len(c.strip()) > 30]

# ──────────────────────────────────────────────
# Embedding & Chroma Setup
# ──────────────────────────────────────────────
def _get_gemini_embedding(text: str, api_key: str) -> list[float]:
    requests = _optional_module("requests")
    if not requests or not api_key:
        return []

    model = "text-embedding-004"
    url = f"https://generativelanguage.googleapis.com/v1beta/models/{model}:embedContent?key={api_key}"
    payload = {
        "model": f"models/{model}",
        "content": {
            "parts": [{"text": text}]
        }
    }

    try:
        resp = requests.post(url, json=payload, timeout=15)
        if resp.status_code == 200:
            data = resp.json()
            embedding = data.get("embedding", {}).get("values", [])
            return embedding
    except Exception:
        pass
    return []

def _get_rag_collection():
    chromadb = _optional_module("chromadb")
    if not chromadb:
        return None, "chromadb is not installed."
    try:
        import logging
        logging.getLogger("chromadb").setLevel(logging.ERROR)
        
        memory_dir = Path(os.path.expanduser("~")) / "veronica_memory"
        memory_dir.mkdir(parents=True, exist_ok=True)
        
        client = chromadb.PersistentClient(path=str(memory_dir))
        collection = client.get_or_create_collection(name="veronica_rag_documents")
        return collection, None
    except Exception as e:
        return None, f"ChromaDB initialization failed: {e}"

# ──────────────────────────────────────────────
# Indexing Logic
# ──────────────────────────────────────────────
def _index_directory(dir_path_str: str, api_key: str) -> str:
    path = Path(dir_path_str.strip('\'"'))
    if not path.is_dir():
        return f"Directory not found: {dir_path_str}"

    collection, err = _get_rag_collection()
    if err:
        return f"Database error: {err}"

    allowed_exts = {".txt", ".md", ".pdf"}
    files_processed = 0
    total_chunks = 0

    print(f"\n[RAG INDEXING] Scanning: {path}")

    # Walk through directory recursively
    for root, _, files in os.walk(path):
        for file in files:
            file_path = Path(root) / file
            if file_path.suffix.lower() in allowed_exts:
                # Read content
                if file_path.suffix.lower() == ".pdf":
                    content = _read_pdf_file(file_path)
                else:
                    content = _read_text_file(file_path)

                if not content or len(content.strip()) < 50:
                    continue

                chunks = _chunk_text(content)
                if not chunks:
                    continue

                print(f"Indexing: {file_path.name} ({len(chunks)} chunks)")

                for i, chunk in enumerate(chunks):
                    chunk_id = f"{file_path.name}_{i}_{uuid.uuid4().hex[:8]}"
                    metadata = {
                        "source_file": str(file_path),
                        "file_name": file_path.name,
                        "timestamp": datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                    }
                    
                    embedding = _get_gemini_embedding(chunk, api_key)
                    try:
                        if embedding:
                            collection.add(
                                documents=[chunk],
                                embeddings=[embedding],
                                metadatas=[metadata],
                                ids=[chunk_id]
                            )
                        else:
                            collection.add(
                                documents=[chunk],
                                metadatas=[metadata],
                                ids=[chunk_id]
                            )
                        total_chunks += 1
                    except Exception as e:
                        print(f"Error adding chunk: {e}")

                files_processed += 1

    return f"Indexed {files_processed} files ({total_chunks} text chunks total) from: {path}"

# ──────────────────────────────────────────────
# QA & Generation Logic
# ──────────────────────────────────────────────
def _query_rag(query: str, api_key: str) -> str:
    collection, err = _get_rag_collection()
    if err:
        return f"Database error: {err}"

    count = collection.count()
    if count == 0:
        return "No documents have been indexed yet. Try: 'Index folder C:\\path\\to\\docs'."

    # Query embedding
    embedding = _get_gemini_embedding(query, api_key)
    
    try:
        if embedding:
            results = collection.query(
                query_embeddings=[embedding],
                n_results=min(5, count)
            )
        else:
            results = collection.query(
                query_texts=[query],
                n_results=min(5, count)
            )
            
        docs = results.get("documents", [[]])[0]
        metadatas = results.get("metadatas", [[]])[0]
    except Exception as e:
        return f"Search retrieval failed: {e}"

    if not docs:
        return "No relevant information found in the indexed documents."

    # Construct context context
    context_blocks = []
    sources = set()
    for doc, meta in zip(docs, metadatas):
        src = meta.get("file_name", "Unknown File")
        sources.add(src)
        context_blocks.append(f"--- [Source: {src}] ---\n{doc}")

    context_str = "\n\n".join(context_blocks)
    
    # Prompt synthesis
    prompt = f"""You are Veronica, an advanced AI Assistant. Answer the user's question based strictly on the provided context retrieved from local documents.
If the information is not in the context, state that you cannot find it in the indexed files.
Cite your sources in the text using [Source Name] notation where appropriate.

Context:
{context_str}

User Question: {query}

Professional Answer:"""

    requests = _optional_module("requests")
    if not requests or not api_key:
        return f"Retrieved Context:\n{context_str}\n\n[Warning: Gemini API not available to synthesize response]"

    model = os.getenv("GEMINI_MODEL", "gemini-1.5-flash")
    url = f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent?key={api_key}"
    payload = {
        "contents": [{"parts": [{"text": prompt}]}],
        "generationConfig": {
            "temperature": 0.3,
            "maxOutputTokens": 1024,
        }
    }

    try:
        resp = requests.post(url, json=payload, timeout=30)
        if resp.status_code == 200:
            data = resp.json()
            if "candidates" in data and data["candidates"]:
                parts = data["candidates"][0].get("content", {}).get("parts", [])
                for part in parts:
                    if "text" in part:
                        ans = part["text"].strip()
                        sources_list = ", ".join(sorted(list(sources)))
                        return f"{ans}\n\n📚 Sources: {sources_list}"
    except Exception as e:
        return f"Gemini QA generation failed: {e}\n\nRaw Context:\n{context_str}"

    return "Failed to synthesize a response."

# ──────────────────────────────────────────────
# Handler
# ──────────────────────────────────────────────
def handle_rag_request(message: str, context: AssistantContext) -> SkillResult:
    api_key = os.getenv("GEMINI_API_KEY", "").strip()
    lowered = message.lower().strip()

    # Index folders
    if lowered.startswith("index folder ") or lowered.startswith("index directory ") or lowered.startswith("index documents "):
        dir_path = ""
        if lowered.startswith("index folder "):
            dir_path = message[len("index folder "):].strip()
        elif lowered.startswith("index directory "):
            dir_path = message[len("index directory "):].strip()
        elif lowered.startswith("index documents "):
            dir_path = message[len("index documents "):].strip()
        
        result = _index_directory(dir_path, api_key)
        return SkillResult(True, result)

    # List folders (show document count)
    if lowered == "list indexed":
        collection, err = _get_rag_collection()
        if err:
            return SkillResult(True, f"Database error: {err}")
        try:
            count = collection.count()
            if count == 0:
                return SkillResult(True, "No indexed documents found.")
            
            data = collection.get()
            metadatas = data.get("metadatas", [])
            sources = {m.get("source_file") for m in metadatas if m.get("source_file")}
            
            lines = [f"• {src}" for src in sorted(list(sources))]
            return SkillResult(True, f"Indexed documents ({count} chunks across these files):\n" + "\n".join(lines))
        except Exception as e:
            return SkillResult(True, f"Error listing indexes: {e}")

    # Ask RAG
    query = message.strip()
    starters = ["ask my documents ", "ask documents ", "ask my rag ", "ask rag "]
    for starter in starters:
        if lowered.startswith(starter):
            query = message[len(starter):].strip().strip("?.!")
            break

    result = _query_rag(query, api_key)
    return SkillResult(True, result)
