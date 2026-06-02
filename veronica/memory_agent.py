"""Semantic Long-Term Memory Agent for Veronica.

Stores, queries, lists, deletes, and wipes semantic memories using ChromaDB
and Gemini's text-embedding-004 model.
"""

import os
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
def is_memory_request(message: str) -> bool:
    lowered = message.lower().strip()
    # Check for commands matching the implementation plan
    return (
        lowered.startswith("remember that")
        or (lowered.startswith("remember ") and "=" in lowered)
        or lowered.startswith("what do you know about")
        or lowered.startswith("what is my")
        or lowered.startswith("what's my")
        or lowered.startswith("search memory for")
        or lowered.startswith("search memories for")
        or lowered.startswith("recall memory")
        or lowered.startswith("what have you remembered")
        or lowered.startswith("list all memories")
        or lowered.startswith("list memories")
        or lowered.startswith("show memory")
        or lowered.startswith("list memory")
        or lowered.startswith("forget ")
        or lowered.startswith("delete memory ")
        or lowered in ("clear all memories", "clear memories", "reset memory", "wipe memory", "wipe memories")
    )

# ──────────────────────────────────────────────
# Embedding Function using Gemini API
# ──────────────────────────────────────────────
def _get_gemini_embedding(text: str, api_key: str) -> list[float]:
    """Retrieve embedding vector using Gemini API."""
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
    except Exception as e:
        print(f"   [Gemini embedding error: {e}]")
    return []

# ──────────────────────────────────────────────
# ChromaDB Helper
# ──────────────────────────────────────────────
def _get_collection(context: AssistantContext | None = None):
    """Retrieve or initialize the ChromaDB memory collection."""
    chromadb = _optional_module("chromadb")
    if not chromadb:
        return None, "chromadb is not installed."

    try:
        import logging
        logging.getLogger("chromadb").setLevel(logging.ERROR)
        
        # Memory path as per implementation plan: ~/veronica_memory/
        profile_name = os.getenv("VERONICA_PROFILE", "default").strip()
        memory_dir = Path(os.path.expanduser("~")) / "veronica_memory" / profile_name
        memory_dir.mkdir(parents=True, exist_ok=True)
        
        client = chromadb.PersistentClient(path=str(memory_dir))
        collection = client.get_or_create_collection(name="veronica_semantic_memory")
        return collection, None
    except Exception as e:
        return None, f"ChromaDB initialization failed: {e}"

# ──────────────────────────────────────────────
# Handler
# ──────────────────────────────────────────────
def handle_memory_request(message: str, context: AssistantContext) -> SkillResult:
    api_key = os.getenv("GEMINI_API_KEY", "").strip()
    lowered = message.lower().strip()
    
    # ──────────────────────────────────────────────
    # Compatibility support for old key-value memory JSON
    # ──────────────────────────────────────────────
    def _load_old_memory(ctx: AssistantContext) -> dict[str, str]:
        if not ctx.memory_file.exists():
            return {}
        try:
            import json
            data = json.loads(ctx.memory_file.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            return {}
        if not isinstance(data, dict):
            return {}
        return {str(k): str(v) for k, v in data.items()}

    def _save_old_memory(ctx: AssistantContext, mem: dict[str, str]) -> None:
        import json
        ctx.memory_file.write_text(json.dumps(mem, indent=2, ensure_ascii=False), encoding="utf-8")

    # 1. Old Show / List memory
    if lowered.startswith(("show memory", "list memory")) and not lowered.startswith(("list memories", "list all memories")):
        memory = _load_old_memory(context)
        if not memory:
            return SkillResult(True, "Memory store empty hai.")
        lines = [f"- {k}: {v}" for k, v in sorted(memory.items())]
        return SkillResult(True, "Saved memory:\n" + "\n".join(lines))

    # 2. Old Forget / Delete memory
    if lowered.startswith(("forget memory ", "delete memory ")) and not lowered.startswith("delete memory list"):
        key = message.split(maxsplit=2)[-1].strip() if len(message.split()) >= 3 else ""
        if not key:
            return SkillResult(True, "Kaunsa memory key delete karna hai?")
        memory = _load_old_memory(context)
        if key not in memory:
            return SkillResult(True, f"Memory key '{key}' mila nahi.")
        del memory[key]
        _save_old_memory(context, memory)
        
        # Also clean up ChromaDB if possible
        try:
            collection, err = _get_collection(context)
            if not err and collection:
                count = collection.count()
                if count > 0:
                    results = collection.query(query_texts=[key], n_results=min(3, count))
                    ids = results.get("ids", [[]])[0]
                    docs = results.get("documents", [[]])[0]
                    for i, d in zip(ids, docs):
                        if key.lower() in d.lower():
                            collection.delete(ids=[i])
        except Exception:
            pass
        return SkillResult(True, f"Memory '{key}' delete kar diya.")

    # 3. Format validator: check if it's a malformed key-value or a natural semantic fact
    if lowered.startswith("remember that") and "=" not in message:
        body = message[len("remember that"):].strip()
        words = body.lower().split()
        if len(words) <= 3 and "is" not in words:
            return SkillResult(True, "Use format: remember that key = value")

    # 4. Old Save memory: remember that key = value or remember key = value
    if (lowered.startswith("remember that ") or lowered.startswith("remember ")) and "=" in message:
        body = ""
        if lowered.startswith("remember that "):
            body = message[len("remember that "):].strip()
        elif lowered.startswith("remember "):
            body = message[len("remember "):].strip()
            
        key, value = [part.strip() for part in body.split("=", 1)]
        if not key or not value:
            return SkillResult(True, "Key aur value dono dene honge: key = value")
            
        # Save to old memory structure
        memory = _load_old_memory(context)
        memory[key] = value
        _save_old_memory(context, memory)
        
        # Also save to ChromaDB for semantic retrieval
        try:
            collection, err = _get_collection(context)
            if not err and collection:
                doc_id = str(uuid.uuid4())
                timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                metadata = {"timestamp": timestamp}
                fact = f"{key} = {value}"
                embedding = _get_gemini_embedding(fact, api_key)
                if embedding:
                    collection.add(documents=[fact], embeddings=[embedding], metadatas=[metadata], ids=[doc_id])
                else:
                    collection.add(documents=[fact], metadatas=[metadata], ids=[doc_id])
        except Exception:
            pass
            
        return SkillResult(True, f"Memory saved: {key} = {value}")

    collection, err = _get_collection()
    if err:
        return SkillResult(True, f"❌ Memory Engine Error: {err}")

    # Case 1: Wiping memory
    if lowered in ("clear all memories", "clear memories", "reset memory", "wipe memory", "wipe memories"):
        try:
            count = collection.count()
            if count > 0:
                # Get all IDs and delete them
                all_ids = collection.get()["ids"]
                if all_ids:
                    collection.delete(ids=all_ids)
            return SkillResult(True, f"🧹 All {count} memories have been permanently cleared.")
        except Exception as e:
            return SkillResult(True, f"❌ Failed to clear memories: {e}")

    # Case 2: Listing memories
    if lowered in ("what have you remembered", "list all memories", "list memories"):
        try:
            count = collection.count()
            if count == 0:
                return SkillResult(True, "💭 I don't have any memories saved yet.")
            
            data = collection.get()
            docs = data.get("documents", [])
            metadatas = data.get("metadatas", [])
            
            lines = []
            for doc, meta in zip(docs, metadatas):
                timestamp = meta.get("timestamp", "unknown time")
                lines.append(f"• [{timestamp}] {doc}")
            
            return SkillResult(True, f"🧠 Here is what I remember ({count} entries):\n\n" + "\n".join(lines))
        except Exception as e:
            return SkillResult(True, f"❌ Failed to retrieve memories: {e}")

    # Case 3: Forget a memory
    if lowered.startswith("forget ") or lowered.startswith("delete memory "):
        topic = ""
        if lowered.startswith("forget "):
            topic = message[len("forget "):].strip()
        elif lowered.startswith("delete memory "):
            topic = message[len("delete memory "):].strip()
            
        if not topic:
            return SkillResult(True, "Please specify what you want me to forget (e.g. 'forget my github token').")

        try:
            count = collection.count()
            if count == 0:
                return SkillResult(True, "I don't have any memories to delete.")

            # Search semantically or do matching to find the correct ID
            embedding = _get_gemini_embedding(topic, api_key)
            
            # Fetch candidates using query
            if embedding:
                results = collection.query(
                    query_embeddings=[embedding],
                    n_results=min(5, count)
                )
            else:
                results = collection.query(
                    query_texts=[topic],
                    n_results=min(5, count)
                )
                
            ids = results.get("ids", [[]])[0]
            docs = results.get("documents", [[]])[0]
            distances = results.get("distances", [[]])[0] if "distances" in results else [0.0]*len(ids)

            if not ids:
                return SkillResult(True, f"I couldn't find any memories matching '{topic}'.")

            # Let's delete the closest match if it's reasonably close, or match text
            # If the user says exactly 'forget <doc>', let's check for exact matches
            exact_match_idx = -1
            for idx, doc in enumerate(docs):
                if topic.lower() in doc.lower() or doc.lower() in topic.lower():
                    exact_match_idx = idx
                    break
            
            target_idx = exact_match_idx if exact_match_idx != -1 else 0
            target_id = ids[target_idx]
            target_doc = docs[target_idx]
            
            collection.delete(ids=[target_id])
            return SkillResult(True, f"🗑️ Forgotten: \"{target_doc}\"")
            
        except Exception as e:
            return SkillResult(True, f"❌ Failed to forget memory: {e}")

    # Case 4: Remember something
    if lowered.startswith("remember that") or lowered.startswith("remember "):
        fact = ""
        if lowered.startswith("remember that"):
            fact = message[len("remember that"):].strip()
        elif lowered.startswith("remember "):
            fact = message[len("remember "):].strip()
            
        if not fact:
            return SkillResult(True, "What would you like me to remember?")

        try:
            doc_id = str(uuid.uuid4())
            timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            metadata = {"timestamp": timestamp}
            
            embedding = _get_gemini_embedding(fact, api_key)
            if embedding:
                collection.add(
                    documents=[fact],
                    embeddings=[embedding],
                    metadatas=[metadata],
                    ids=[doc_id]
                )
            else:
                collection.add(
                    documents=[fact],
                    metadatas=[metadata],
                    ids=[doc_id]
                )
            return SkillResult(True, f"💾 Stored in memory: \"{fact}\"")
        except Exception as e:
            return SkillResult(True, f"❌ Failed to save memory: {e}")

    # Case 5: Recall / Query memory
    query = message.strip()
    # Strip question starters to focus on the semantic content
    starters = ["what do you know about ", "what is my ", "what's my ", "search memory for ", "search memories for ", "recall memory "]
    for starter in starters:
        if lowered.startswith(starter):
            query = message[len(starter):].strip().strip("?.!")
            break

    try:
        count = collection.count()
        if count == 0:
            return SkillResult(True, "💭 I don't have any memories saved yet. Try saying: \"Remember that I prefer VS Code\".")

        embedding = _get_gemini_embedding(query, api_key)
        if embedding:
            results = collection.query(
                query_embeddings=[embedding],
                n_results=min(3, count)
            )
        else:
            results = collection.query(
                query_texts=[query],
                n_results=min(3, count)
            )

        docs = results.get("documents", [[]])[0]
        if not docs:
            return SkillResult(True, f"💭 I couldn't find any relevant memories matching \"{query}\".")

        lines = [f"• {doc}" for doc in docs]
        return SkillResult(True, f"🧠 Here is what I retrieved from my memories regarding \"{query}\":\n\n" + "\n".join(lines))
    except Exception as e:
        return SkillResult(True, f"❌ Failed to recall memory: {e}")
