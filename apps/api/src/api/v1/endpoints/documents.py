"""Documents endpoints"""
from fastapi import APIRouter, UploadFile, File, Form
from typing import List

router = APIRouter()


@router.post("/upload")
async def upload_document(
    file: UploadFile = File(...),
    user_id: str = Form(...),
    is_global: bool = Form(False),
):
    """Upload and process a document"""
    return {
        "message": "Document uploaded successfully",
        "file_id": file.filename,
    }


@router.get("")
async def list_documents(user_id: str):
    """List user's documents"""
    return {
        "documents": [],
        "total": 0,
    }


@router.delete("/{doc_id}")
async def delete_document(doc_id: str):
    """Delete a document"""
    return {"message": "Document deleted", "doc_id": doc_id}
