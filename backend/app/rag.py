import os
import logging
from langchain_qdrant import QdrantVectorStore
from langchain_ollama import OllamaEmbeddings
from qdrant_client import QdrantClient
from qdrant_client.http.models import VectorParams, Distance # <--- THÊM IMPORT NÀY
from langchain_community.document_loaders import PyPDFLoader, Docx2txtLoader, TextLoader
from langchain_text_splitters import RecursiveCharacterTextSplitter

# Cấu hình Logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# 1. Cấu hình Embedding Local
embeddings = OllamaEmbeddings(
    base_url=os.getenv("OLLAMA_BASE_URL", "http://ollama:11434"),
    model="nomic-embed-text" 
)

# 2. Kết nối Qdrant
client = QdrantClient(url=os.getenv("QDRANT_URL", "http://qdrant:6333"))

def get_vector_store(collection_name="enterprise_knowledge"):
    # --- ĐOẠN CODE MỚI THÊM VÀO ĐỂ FIX LỖI 404 ---
    # Kiểm tra xem Collection đã tồn tại chưa
    if not client.collection_exists(collection_name):
        logger.info(f"Collection '{collection_name}' not found. Creating it now...")
        # Tạo mới Collection với kích thước vector 768 (Chuẩn của nomic-embed-text)
        client.create_collection(
            collection_name=collection_name,
            vectors_config=VectorParams(size=768, distance=Distance.COSINE)
        )
    # ---------------------------------------------

    return QdrantVectorStore(
        client=client,
        collection_name=collection_name,
        embedding=embeddings,
    )

async def process_file(file_path: str, file_type: str, user_id: str, is_global: bool, original_filename: str):
    # ... (Giữ nguyên phần còn lại của hàm này y hệt code cũ) ...
    # Copy lại đoạn code process_file cũ của bạn vào đây
    logger.info(f"Processing file: {original_filename}")
    
    try:
        # 1. Load file
        if "pdf" in file_type:
            loader = PyPDFLoader(file_path)
        elif "word" in file_type or "officedocument" in file_type:
            loader = Docx2txtLoader(file_path)
        else:
            loader = TextLoader(file_path)
            
        docs = loader.load()
        
        # 2. Split text (Cắt nhỏ văn bản)
        text_splitter = RecursiveCharacterTextSplitter(chunk_size=1000, chunk_overlap=200)
        splits = text_splitter.split_documents(docs)
        
        # 3. Gán Metadata
        msg_type = "global" if is_global else "personal"
        real_user_id = "admin" if is_global else user_id
        
        for doc in splits:
            doc.metadata["type"] = msg_type
            doc.metadata["user_id"] = real_user_id
            doc.metadata["source"] = original_filename

        # 4. Lưu vào Qdrant
        # Lúc này hàm get_vector_store đã tự tạo collection rồi nên không sợ lỗi nữa
        vector_store = get_vector_store()
        vector_store.add_documents(splits)
        
        logger.info(f"Successfully processed {len(splits)} chunks from {original_filename}")
        return len(splits)
        
    except Exception as e:
        logger.error(f"Error processing file {original_filename}: {e}")
        raise e

# ... (Giữ nguyên hàm get_all_files nếu có) ...
def get_all_files(collection_name="enterprise_knowledge"):
    # Code get_all_files cũ của bạn
    try:
        if not client.collection_exists(collection_name):
             return []
             
        response = client.scroll(
            collection_name=collection_name,
            scroll_filter=None,
            limit=1000,
            with_payload=True,
            with_vectors=False
        )
        points, _ = response
        unique_files = set()
        for point in points:
            payload = point.payload
            if payload:
                # Cách 1: Kiểm tra nếu source nằm trong metadata (LangChain chuẩn) -> TRƯỜNG HỢP CỦA BẠN
                if "metadata" in payload and "source" in payload["metadata"]:
                    unique_files.add(payload["metadata"]["source"])
                # Cách 2: Kiểm tra nếu source nằm ngay bên ngoài (Dự phòng)
                elif "source" in payload:
                    unique_files.add(payload["source"])
        return list(unique_files)
    except Exception as e:
        logger.error(f"Error listing files: {e}")
        return []