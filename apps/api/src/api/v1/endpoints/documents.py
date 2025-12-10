"""
Documents Endpoints

Upload, search, and manage documents in vector store
"""
import logging
import io
from typing import List, Optional, Dict
from fastapi import APIRouter, UploadFile, File, Form, HTTPException, Query
from pydantic import BaseModel

from src.services.rag_service import RAGService

logger = logging.getLogger(__name__)

router = APIRouter()


# Request/Response Models
class SearchRequest(BaseModel):
    query: str
    top_k: int = 5
    collection: Optional[str] = None
    score_threshold: Optional[float] = 0.5


class SearchResult(BaseModel):
    id: str
    score: float
    content: str
    title: str
    source: str
    metadata: Dict
    created_at: Optional[str] = None


class DocumentResponse(BaseModel):
    id: str
    content: str
    title: str
    source: str
    metadata: Dict
    user_id: Optional[str] = None
    created_at: Optional[str] = None


class CollectionInfo(BaseModel):
    name: str
    count: int
    vectors_count: Optional[int] = None


@router.post("/search", response_model=List[SearchResult])
async def search_documents(request: SearchRequest):
    """
    Search documents using semantic similarity
    
    - **query**: Search query text
    - **top_k**: Number of results to return (default: 5, max: 20)
    - **collection**: Optional collection name filter
    - **score_threshold**: Minimum similarity score (0.0 - 1.0)
    """
    try:
        if request.top_k > 20:
            raise HTTPException(
                status_code=400,
                detail="top_k cannot exceed 20"
            )
        
        rag_service = RAGService()
        results = await rag_service.search(
            query=request.query,
            limit=request.top_k,
            score_threshold=request.score_threshold,
        )
        
        return results
        
    except Exception as e:
        logger.error(f"Error searching documents: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/upload")
async def upload_document(
    file: UploadFile = File(...),
    title: Optional[str] = Form(None),
    source: Optional[str] = Form(None),
    user_id: Optional[str] = Form("anonymous"),
    metadata: Optional[str] = Form("{}"),  # JSON string
):
    """
    Upload and process a document
    
    Supported formats: PDF, TXT, MD, DOCX
    """
    import json
    
    try:
        # Validate file type
        allowed_types = [
            "application/pdf",
            "text/plain", 
            "text/markdown",
            "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
        ]
        
        if file.content_type not in allowed_types:
            raise HTTPException(
                status_code=400,
                detail=f"File type {file.content_type} not supported"
            )
        
        # Read file content
        content = await file.read()
        
        # Extract text based on file type
        if file.content_type == "application/pdf":
            text = await extract_text_from_pdf(content)
        elif file.content_type == "application/vnd.openxmlformats-officedocument.wordprocessingml.document":
            text = await extract_text_from_docx(content)
        else:
            # Plain text or markdown
            text = content.decode('utf-8')
        
        if not text or len(text.strip()) == 0:
            raise HTTPException(
                status_code=400,
                detail="No text content found in document"
            )
        
        # Parse metadata
        try:
            meta_dict = json.loads(metadata) if metadata != "{}" else {}
        except json.JSONDecodeError:
            meta_dict = {}
        
        # Add document to vector store
        rag_service = RAGService()
        doc_id = await rag_service.add_document(
            content=text,
            metadata=meta_dict,
            title=title or file.filename,
            source=source or file.filename,
            user_id=user_id,
        )
        
        return {
            "message": "Document uploaded successfully",
            "document_id": doc_id,
            "filename": file.filename,
            "size": len(content),
            "text_length": len(text),
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error uploading document: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/{doc_id}", response_model=DocumentResponse)
async def get_document(doc_id: str):
    """
    Get document by ID
    
    - **doc_id**: Document unique identifier
    """
    try:
        rag_service = RAGService()
        doc = await rag_service.get_document(doc_id)
        
        if not doc:
            raise HTTPException(
                status_code=404,
                detail=f"Document {doc_id} not found"
            )
        
        return doc
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting document: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/{doc_id}")
async def delete_document(doc_id: str):
    """
    Delete a document
    
    - **doc_id**: Document unique identifier
    """
    try:
        rag_service = RAGService()
        success = await rag_service.delete_document(doc_id)
        
        if not success:
            raise HTTPException(
                status_code=404,
                detail=f"Document {doc_id} not found"
            )
        
        return {
            "message": "Document deleted successfully",
            "document_id": doc_id
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error deleting document: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/collections/list", response_model=List[CollectionInfo])
async def list_collections():
    """
    List all available document collections
    
    Returns collection names and document counts
    """
    try:
        rag_service = RAGService()
        collections = await rag_service.list_collections()
        return collections
        
    except Exception as e:
        logger.error(f"Error listing collections: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("")
async def list_documents(
    user_id: Optional[str] = Query(None),
    limit: int = Query(10, le=100),
    offset: int = Query(0, ge=0),
):
    """
    List documents (filtered by user if provided)
    
    - **user_id**: Optional user ID filter
    - **limit**: Maximum number of results
    - **offset**: Pagination offset
    """
    # TODO: Implement pagination and filtering in Qdrant
    # For now, return empty list
    return {
        "documents": [],
        "total": 0,
        "limit": limit,
        "offset": offset,
    }


# Helper functions for text extraction
async def extract_text_from_pdf(content: bytes) -> str:
    """Extract text from PDF"""
    try:
        from pypdf import PdfReader
        pdf = PdfReader(io.BytesIO(content))
        text = ""
        for page in pdf.pages:
            text += page.extract_text() + "\n"
        return text
    except Exception as e:
        logger.error(f"Error extracting PDF text: {e}")
        raise HTTPException(
            status_code=400,
            detail="Could not extract text from PDF"
        )


async def extract_text_from_docx(content: bytes) -> str:
    """Extract text from DOCX"""
    try:
        from docx import Document
        doc = Document(io.BytesIO(content))
        text = ""
        for para in doc.paragraphs:
            text += para.text + "\n"
        return text
    except Exception as e:
        logger.error(f"Error extracting DOCX text: {e}")
        raise HTTPException(
            status_code=400,
            detail="Could not extract text from DOCX"
        )
