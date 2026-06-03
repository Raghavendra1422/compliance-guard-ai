import pdfplumber
import os
import uuid
from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain_huggingface import HuggingFaceEmbeddings
from langchain_chroma import Chroma
from dotenv import load_dotenv

load_dotenv()

# ── Embedding model ────────────────────────────────────────────
embeddings = HuggingFaceEmbeddings(
    model_name="all-MiniLM-L6-v2",
    model_kwargs={"device": "cpu"},
    encode_kwargs={"normalize_embeddings": True}
)

# ── ChromaDB setup ─────────────────────────────────────────────
CHROMA_PATH = os.getenv("CHROMA_DB_PATH", "./chroma_db")

vectorstore = Chroma(
    collection_name="rbi_regulations",
    embedding_function=embeddings,
    persist_directory=CHROMA_PATH
)

# ── Text splitter ──────────────────────────────────────────────
text_splitter = RecursiveCharacterTextSplitter(
    chunk_size=512,
    chunk_overlap=50,
    length_function=len,
    separators=["\n\n", "\n", ".", " ", ""]
)


def extract_text_from_pdf(pdf_path: str) -> str:
    """Extract all text from a PDF file."""
    full_text = ""
    try:
        with pdfplumber.open(pdf_path) as pdf:
            for page_num, page in enumerate(pdf.pages):
                text = page.extract_text()
                if text:
                    full_text += f"\n[PAGE {page_num + 1}]\n{text}"
    except Exception as e:
        raise ValueError(f"Could not read PDF {pdf_path}: {str(e)}")
    return full_text.strip()


def delete_existing_chunks(circular_id: str) -> int:
    """
    Delete ALL chunks belonging to a circular_id from ChromaDB.
    This is the core of version control — wipe old before adding new.
    Returns number of chunks deleted.
    """
    try:
        collection = vectorstore._collection

        # Find all chunk IDs that belong to this circular_id
        results = collection.get(
            where={"circular_id": circular_id},
            include=["metadatas"]
        )

        if not results["ids"]:
            print(f"[Ingestor] No existing chunks found for {circular_id}")
            return 0

        count = len(results["ids"])
        # Delete them all
        collection.delete(ids=results["ids"])
        print(f"[Ingestor] Deleted {count} old chunks for {circular_id}")
        return count

    except Exception as e:
        print(f"[Ingestor] Warning during delete: {e}")
        return 0


def check_circular_exists(circular_id: str) -> dict:
    """
    Check if a circular_id already exists in ChromaDB.
    Returns info about existing document if found.
    """
    try:
        collection = vectorstore._collection
        results = collection.get(
            where={"circular_id": circular_id},
            include=["metadatas"]
        )

        if not results["ids"]:
            return {"exists": False, "chunk_count": 0, "category": None}

        # Get metadata from first chunk
        meta = results["metadatas"][0] if results["metadatas"] else {}
        return {
            "exists": True,
            "chunk_count": len(results["ids"]),
            "category": meta.get("category"),
            "source_file": meta.get("source_file"),
        }
    except Exception:
        return {"exists": False, "chunk_count": 0, "category": None}


def ingest_pdf(
    pdf_path: str,
    circular_id: str,
    category: str = "general",
    replace: bool = True          # ← NEW: replace by default
) -> dict:
    """
    Full pipeline: PDF → text → chunks → embeddings → ChromaDB.
    If replace=True (default), deletes old chunks for this circular_id first.
    """

    # Step 0: Check if this circular_id already exists
    existing = check_circular_exists(circular_id)
    deleted_count = 0

    if existing["exists"] and replace:
        print(f"[Ingestor] Found existing version of {circular_id} "
              f"({existing['chunk_count']} chunks) — replacing with new version...")
        deleted_count = delete_existing_chunks(circular_id)

    elif existing["exists"] and not replace:
        print(f"[Ingestor] Appending to existing {circular_id}...")

    # Step 1: Extract text from PDF
    print(f"[Ingestor] Reading PDF: {pdf_path}")
    raw_text = extract_text_from_pdf(pdf_path)

    if not raw_text:
        raise ValueError(
            f"No text extracted from PDF. Is it a scanned/image PDF?"
        )

    # Step 2: Split into chunks
    print(f"[Ingestor] Splitting text into chunks...")
    chunks = text_splitter.split_text(raw_text)
    print(f"[Ingestor] Created {len(chunks)} chunks")

    # Step 3: Build metadata for each chunk
    filename = os.path.basename(pdf_path)
    import datetime
    ingested_at = datetime.datetime.now().isoformat()

    metadatas = []
    for i, chunk in enumerate(chunks):
        page_num = "unknown"
        for line in chunk.split("\n"):
            if line.startswith("[PAGE "):
                page_num = line.replace("[PAGE ", "").replace("]", "").strip()
                break

        metadatas.append({
            "circular_id": circular_id,
            "source_file": filename,
            "category": category,
            "chunk_index": i,
            "page_number": page_num,
            "chunk_id": str(uuid.uuid4()),
            "ingested_at": ingested_at,     # ← track when ingested
            "version": ingested_at[:10],    # ← date as version (2024-01-15)
        })

    # Step 4: Store in ChromaDB
    print(f"[Ingestor] Embedding and storing in ChromaDB...")
    vectorstore.add_texts(texts=chunks, metadatas=metadatas)

    print(f"[Ingestor] Done! Ingested {len(chunks)} chunks from {filename}")

    return {
        "circular_id": circular_id,
        "source_file": filename,
        "total_chunks": len(chunks),
        "category": category,
        "version": ingested_at[:10],
        "replaced_chunks": deleted_count,
        "action": "replaced" if deleted_count > 0 else "added",
        "status": "success"
    }


def list_ingested_documents() -> list:
    """Return all unique documents stored in ChromaDB with version info."""
    try:
        collection = vectorstore._collection
        results = collection.get(include=["metadatas"])

        seen = set()
        documents = []
        for meta in results["metadatas"]:
            cid = meta.get("circular_id", "unknown")
            if cid not in seen:
                seen.add(cid)
                documents.append({
                    "circular_id": cid,
                    "source_file": meta.get("source_file"),
                    "category": meta.get("category"),
                    "version": meta.get("version", "unknown"),
                    "ingested_at": meta.get("ingested_at", "unknown"),
                })

        # Sort by ingested_at descending (latest first)
        documents.sort(key=lambda x: x.get("ingested_at", ""), reverse=True)
        return documents

    except Exception:
        return []


def search_regulations(
    query: str,
    n_results: int = 5,
    category: str = None
) -> list:
    """Search ChromaDB for relevant regulation chunks."""
    search_kwargs = {"k": n_results}

    if category:
        search_kwargs["filter"] = {"category": category}

    results = vectorstore.similarity_search_with_score(query, **search_kwargs)

    formatted = []
    for doc, score in results:
        formatted.append({
            "content": doc.page_content,
            "metadata": doc.metadata,
            "relevance_score": round(1 - score, 4)
        })
    return formatted