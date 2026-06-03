from fastapi import APIRouter, UploadFile, File, Form, HTTPException
from fastapi.responses import JSONResponse
from services.ingestor import (
    ingest_pdf,
    list_ingested_documents,
    search_regulations,
    check_circular_exists,
    delete_existing_chunks
)
import tempfile
import os
import shutil

router = APIRouter(prefix="/api/v1/documents", tags=["Documents"])


@router.post("/ingest")
async def ingest_document(
    file: UploadFile = File(...),
    circular_id: str = Form(...),
    category: str = Form("general"),
    replace: bool = Form(True)    # ← NEW param
):
    """
    Upload an RBI PDF and ingest it into ChromaDB.
    replace=True (default) → deletes old version first (recommended)
    replace=False → appends alongside old version
    """
    if not file.filename.endswith(".pdf"):
        raise HTTPException(status_code=400, detail="Only PDF files are accepted.")

    # Check if this circular already exists — return info to frontend
    existing = check_circular_exists(circular_id)

    with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as tmp:
        shutil.copyfileobj(file.file, tmp)
        tmp_path = tmp.name

    try:
        result = ingest_pdf(
            pdf_path=tmp_path,
            circular_id=circular_id,
            category=category,
            replace=replace
        )
        # Add existing info to response
        result["was_existing"] = existing["exists"]
        result["previous_chunks"] = existing.get("chunk_count", 0)
        return JSONResponse(content=result)
    except ValueError as e:
        raise HTTPException(status_code=422, detail=str(e))
    finally:
        os.unlink(tmp_path)


@router.get("/check/{circular_id}")
async def check_document_exists(circular_id: str):
    """
    Check if a circular_id already exists in the knowledge base.
    Frontend uses this to warn user before they upload a duplicate.
    """
    result = check_circular_exists(circular_id)
    return result


@router.delete("/delete/{circular_id}")
async def delete_document(circular_id: str):
    """Delete all chunks for a circular_id from ChromaDB."""
    existing = check_circular_exists(circular_id)
    if not existing["exists"]:
        raise HTTPException(
            status_code=404,
            detail=f"Circular '{circular_id}' not found in knowledge base."
        )
    deleted = delete_existing_chunks(circular_id)
    return {
        "circular_id": circular_id,
        "deleted_chunks": deleted,
        "status": "deleted"
    }


@router.get("/list")
async def list_documents():
    """List all RBI documents currently stored in ChromaDB."""
    docs = list_ingested_documents()
    return {"total": len(docs), "documents": docs}


@router.post("/search")
async def test_search(
    query: str,
    n_results: int = 5,
    category: str = None
):
    """Test raw vector search."""
    if not query.strip():
        raise HTTPException(status_code=400, detail="Query cannot be empty.")
    results = search_regulations(
        query=query,
        n_results=n_results,
        category=category
    )
    return {
        "query": query,
        "total_results": len(results),
        "results": results
    }