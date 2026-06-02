"""Desktop Memory & RAG Viewer Agent for Veronica.

Spawns a desktop Tkinter window to visually search, inspect, and delete
entries from Veronica's Semantic Memory and RAG database collections.
"""

import os
import threading
from pathlib import Path
from .skills import AssistantContext, SkillResult

# ──────────────────────────────────────────────
# Matcher
# ──────────────────────────────────────────────
def is_gui_viewer_request(message: str) -> bool:
    lowered = message.lower().strip()
    return lowered in ("show memory panel", "open rag viewer", "open database panel", "open database inspector")

# ──────────────────────────────────────────────
# Tkinter Window Engine
# ──────────────────────────────────────────────
def _build_gui():
    import os
    if not os.getenv("VERONICA_GUI_SUBPROCESS"):
        import subprocess
        import sys
        from pathlib import Path
        
        env = os.environ.copy()
        env["VERONICA_GUI_SUBPROCESS"] = "1"
        code = (
            "import sys\n"
            "from pathlib import Path\n"
            f"sys.path.insert(0, r'{Path.cwd()}')\n"
            "from veronica.gui_viewer_agent import _build_gui\n"
            "_build_gui()\n"
        )
        try:
            subprocess.Popen([sys.executable, "-c", code], env=env, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            return
        except Exception:
            pass

    try:
        import tkinter as tk
        from tkinter import ttk, messagebox
    except ImportError:
        print("   [GUI Viewer] tkinter library not available.")
        return

    try:
        root = tk.Tk()
    except Exception as e:
        print(f"   [GUI Viewer] Failed to initialize Tkinter window (likely headless run): {e}")
        return

    root.title("Veronica Database Inspector")
    root.geometry("650x450")
    root.configure(bg="#1e1e1e")

    style = ttk.Style()
    style.theme_use("clam")
    style.configure(".", background="#1e1e1e", foreground="#ffffff")
    style.configure("Treeview", background="#2d2d2d", fieldbackground="#2d2d2d", foreground="#ffffff")

    # Header
    header = tk.Label(root, text="VERONICA DATABASE INSPECTOR", bg="#1e1e1e", fg="#00d2ff", font=("Consolas", 14, "bold"))
    header.pack(pady=10)

    # Search Bar
    search_frame = tk.Frame(root, bg="#1e1e1e")
    search_frame.pack(fill="x", padx=15, pady=5)
    
    search_lbl = tk.Label(search_frame, text="Search: ", bg="#1e1e1e", fg="#ffffff")
    search_lbl.pack(side="left")
    
    search_entry = tk.Entry(search_frame, bg="#2d2d2d", fg="#ffffff", insertbackground="white")
    search_entry.pack(side="left", fill="x", expand=True, padx=5)

    # Database Treeview (List)
    tree_frame = tk.Frame(root, bg="#1e1e1e")
    tree_frame.pack(fill="both", expand=True, padx=15, pady=5)
    
    columns = ("id", "type", "content", "timestamp")
    tree = ttk.Treeview(tree_frame, columns=columns, show="headings")
    tree.heading("id", text="ID")
    tree.heading("type", text="Type")
    tree.heading("content", text="Content Snippet")
    tree.heading("timestamp", text="Timestamp")
    
    tree.column("id", width=60)
    tree.column("type", width=80)
    tree.column("content", width=350)
    tree.column("timestamp", width=120)
    tree.pack(fill="both", expand=True, side="left")

    scrollbar = ttk.Scrollbar(tree_frame, orient="vertical", command=tree.yview)
    tree.configure(yscrollcommand=scrollbar.set)
    scrollbar.pack(side="right", fill="y")

    # Fetch data helper
    from .memory_agent import _get_collection as get_mem_col
    from .rag_agent import _get_rag_collection as get_rag_col

    def refresh_data():
        for item in tree.get_children():
            tree.delete(item)
            
        search_query = search_entry.get().lower().strip()
        
        # Load memories
        mem_col, _ = get_mem_col()
        if mem_col:
            try:
                data = mem_col.get()
                ids = data.get("ids", [])
                docs = data.get("documents", [])
                metadatas = data.get("metadatas", [])
                for i, doc, meta in zip(ids, docs, metadatas):
                    if search_query and search_query not in doc.lower():
                        continue
                    ts = meta.get("timestamp", "unknown")
                    tree.insert("", "end", values=(i[:8], "Memory", doc[:50] + "...", ts))
            except Exception:
                pass
                
        # Load RAG
        rag_col, _ = get_rag_col()
        if rag_col:
            try:
                data = rag_col.get()
                ids = data.get("ids", [])
                docs = data.get("documents", [])
                metadatas = data.get("metadatas", [])
                for i, doc, meta in zip(ids, docs, metadatas):
                    if search_query and search_query not in doc.lower():
                        continue
                    ts = meta.get("timestamp", "unknown")
                    tree.insert("", "end", values=(i[:8], "RAG Document", doc[:50] + "...", ts))
            except Exception:
                pass

    # Bind search key
    search_entry.bind("<KeyRelease>", lambda e: refresh_data())

    # Actions Frame (Delete / Refresh)
    btn_frame = tk.Frame(root, bg="#1e1e1e")
    btn_frame.pack(fill="x", padx=15, pady=10)

    def delete_selected():
        selected = tree.selection()
        if not selected:
            messagebox.showinfo("Selection Required", "Please select an item to delete.")
            return
            
        vals = tree.item(selected[0])["values"]
        short_id = vals[0]
        dtype = vals[1]
        
        confirm = messagebox.askyesno("Confirm Delete", f"Are you sure you want to delete this {dtype} record?")
        if not confirm:
            return
            
        if dtype == "Memory":
            col, _ = get_mem_col()
        else:
            col, _ = get_rag_col()
            
        if col:
            try:
                # Find full ID by listing
                data = col.get()
                for full_id in data.get("ids", []):
                    if full_id.startswith(short_id):
                        col.delete(ids=[full_id])
                        break
                messagebox.showinfo("Success", "Record deleted successfully.")
                refresh_data()
            except Exception as e:
                messagebox.showerror("Error", f"Failed to delete: {e}")

    del_btn = tk.Button(btn_frame, text="Delete Selected", command=delete_selected, bg="#d9534f", fg="white", activebackground="#c9302c")
    del_btn.pack(side="left", padx=5)
    
    refresh_btn = tk.Button(btn_frame, text="Refresh", command=refresh_data, bg="#5cb85c", fg="white", activebackground="#4cae4c")
    refresh_btn.pack(side="left", padx=5)
    
    refresh_data()
    root.mainloop()

# ──────────────────────────────────────────────
# Handler
# ──────────────────────────────────────────────
def handle_gui_viewer_request(message: str, context: AssistantContext) -> SkillResult:
    lowered = message.lower().strip()
    
    # Spawn the Tkinter GUI window in a dedicated background thread to avoid hanging the assistant
    t = threading.Thread(target=_build_gui, daemon=True)
    t.start()
    
    return SkillResult(True, "🖥️ Spawning **Desktop Database Inspector** panel in background...")
