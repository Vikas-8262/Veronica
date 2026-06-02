"""Semantic Long-Term Memory for Veronica using ChromaDB."""

import uuid
import importlib
from pathlib import Path

def _optional_module(module_name: str):
    try:
        return importlib.import_module(module_name)
    except ImportError:
        return None

class MemoryManager:
    """Manages long-term conversational memory using a local Vector DB."""
    
    def __init__(self, data_dir: Path):
        self.chromadb = _optional_module("chromadb")
        self.enabled = self.chromadb is not None
        self.collection = None
        
        if self.enabled:
            try:
                # Initialize persistent local storage for embeddings
                db_path = data_dir / "memory"
                db_path.mkdir(parents=True, exist_ok=True)
                
                import logging
                logging.getLogger("chromadb").setLevel(logging.ERROR)
                
                self.client = self.chromadb.PersistentClient(path=str(db_path))
                # Get or create the main conversation memory collection
                self.collection = self.client.get_or_create_collection(name="veronica_conversations")
            except Exception:
                self.enabled = False
            
    def save_memory(self, user_text: str, ai_text: str) -> None:
        """Embeds and saves an interaction to the database."""
        if not self.enabled or not self.collection:
            return
            
        doc_id = str(uuid.uuid4())
        document = f"User asked: {user_text}\nVeronica replied: {ai_text}"
        
        try:
            self.collection.add(
                documents=[document],
                metadatas=[{"role": "conversation", "user_text": user_text}],
                ids=[doc_id]
            )
        except Exception:
            pass # Fail gracefully 

    def recall_memory(self, query: str, k: int = 3) -> str:
        """Searches for semantically similar past conversations."""
        if not self.enabled or not self.collection:
            return ""
            
        try:
            # Only query if we actually have documents to avoid ChromaDB errors
            if self.collection.count() == 0:
                return ""
                
            results = self.collection.query(
                query_texts=[query],
                n_results=min(k, self.collection.count())
            )
            
            if not results["documents"] or not results["documents"][0]:
                return ""
                
            past_context = "\n---\n".join(results["documents"][0])
            return past_context
            
        except Exception:
            return ""
