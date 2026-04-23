"""
MULTIMODAL RETRIEVAL SERVICE — PDF, Image, Text, Markdown Support

Purpose: Extract and embed multimodal documents (PDF, JPEG, PNG, TXT, Markdown)
for enhanced RAG context in verification and reasoning stages
"""

from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass
from datetime import datetime
import logging
import os
from pathlib import Path

logger = logging.getLogger(__name__)


@dataclass
class DocumentChunk:
    """A chunk of extracted document text."""
    chunk_id: str  # unique identifier
    source_document: str  # original file name/path
    source_type: str  # "pdf", "image", "txt", "markdown"
    content: str  # extracted text
    chunk_index: int  # position in document
    token_count: int  # approximate tokens
    metadata: Dict  # any additional metadata
    created_at: datetime


@dataclass
class EmbeddedChunk:
    """Chunk with vector embedding."""
    chunk_id: str
    content: str
    embedding: List[float]  # 1024-dim vector from BAAI/bge-large-en-v1.5
    token_count: int
    source_document: str
    source_type: str


class DocumentExtractor:
    """Extract text from multimodal documents."""
    
    SUPPORTED_TYPES = ["pdf", "jpg", "jpeg", "png", "txt", "md"]
    TARGET_CHUNK_SIZE = 256  # tokens per chunk
    
    def __init__(self):
        self.pdfplumber_available = False
        self.tesseract_available = False
        self.PIL_available = False
        
        self._check_dependencies()
    
    def _check_dependencies(self):
        """Check for optional dependencies."""
        try:
            import pdfplumber
            self.pdfplumber_available = True
            logger.info("[Multimodal] pdfplumber available for PDF extraction")
        except ImportError:
            logger.warning("[Multimodal] pdfplumber not installed. Install: pip install pdfplumber")
        
        try:
            import pytesseract
            self.tesseract_available = True
            logger.info("[Multimodal] pytesseract available for OCR")
        except ImportError:
            logger.warning("[Multimodal] pytesseract not installed. Install: pip install pytesseract")
        
        try:
            from PIL import Image
            self.PIL_available = True
            logger.info("[Multimodal] PIL available for image handling")
        except ImportError:
            logger.warning("[Multimodal] Pillow not installed. Install: pip install Pillow")
    
    def extract_text(self, file_path: str) -> Tuple[str, str]:
        """
        Extract text from document.
        
        Args:
            file_path: Path to document file
        
        Returns:
            Tuple of (extracted_text, source_type)
        """
        try:
            file_ext = Path(file_path).suffix.lower().lstrip(".")
            
            if file_ext == "pdf":
                return self._extract_pdf(file_path), "pdf"
            elif file_ext in ["jpg", "jpeg", "png"]:
                return self._extract_image(file_path), "image"
            elif file_ext == "txt":
                return self._extract_text_file(file_path), "txt"
            elif file_ext == "md":
                return self._extract_markdown(file_path), "markdown"
            else:
                logger.warning(f"[Multimodal] Unsupported file type: {file_ext}")
                return "", "unknown"
        
        except Exception as e:
            logger.error(f"[Multimodal] Error extracting text from {file_path}: {e}")
            raise
    
    def _extract_pdf(self, file_path: str) -> str:
        """Extract text from PDF."""
        try:
            if not self.pdfplumber_available:
                raise ImportError("pdfplumber not installed")
            
            import pdfplumber
            
            text_parts = []
            with pdfplumber.open(file_path) as pdf:
                for page_num, page in enumerate(pdf.pages, 1):
                    text = page.extract_text()
                    if text:
                        text_parts.append(f"--- Page {page_num} ---\n{text}")
            
            full_text = "\n".join(text_parts)
            logger.info(f"[Multimodal] Extracted {len(full_text)} chars from PDF: {file_path}")
            return full_text
        
        except ImportError as e:
            logger.error(f"[Multimodal] pdfplumber required for PDF extraction: {e}")
            return ""
        except Exception as e:
            logger.error(f"[Multimodal] Error extracting PDF: {e}")
            return ""
    
    def _extract_image(self, file_path: str) -> str:
        """Extract text from image via OCR."""
        try:
            if not self.tesseract_available or not self.PIL_available:
                raise ImportError("pytesseract and/or Pillow not installed")
            
            import pytesseract
            from PIL import Image
            
            img = Image.open(file_path)
            text = pytesseract.image_to_string(img)
            
            logger.info(f"[Multimodal] Extracted {len(text)} chars from image: {file_path}")
            return text
        
        except ImportError as e:
            logger.error(f"[Multimodal] pytesseract/Pillow required for OCR: {e}")
            return ""
        except Exception as e:
            logger.error(f"[Multimodal] Error extracting image: {e}")
            return ""
    
    def _extract_text_file(self, file_path: str) -> str:
        """Extract text from plain text file."""
        try:
            with open(file_path, "r", encoding="utf-8") as f:
                text = f.read()
            logger.info(f"[Multimodal] Extracted {len(text)} chars from text file: {file_path}")
            return text
        except Exception as e:
            logger.error(f"[Multimodal] Error reading text file: {e}")
            return ""
    
    def _extract_markdown(self, file_path: str) -> str:
        """Extract text from markdown file."""
        try:
            with open(file_path, "r", encoding="utf-8") as f:
                text = f.read()
            logger.info(f"[Multimodal] Extracted {len(text)} chars from markdown: {file_path}")
            return text
        except Exception as e:
            logger.error(f"[Multimodal] Error reading markdown: {e}")
            return ""
    
    def chunk_text(self, text: str, chunk_size: int = 256) -> List[str]:
        """
        Split text into chunks by approximate token count.
        
        Uses simple whitespace-based approximation:
        ~1 token per 4 characters (rough estimate)
        
        Args:
            text: Full text to chunk
            chunk_size: Target tokens per chunk (approximately)
        
        Returns:
            List of text chunks
        """
        try:
            char_per_token = 4
            target_chars = chunk_size * char_per_token
            
            sentences = text.split(". ")
            chunks = []
            current_chunk = []
            current_length = 0
            
            for sentence in sentences:
                sentence_length = len(sentence)
                
                # If adding this sentence would exceed target, start new chunk
                if current_length + sentence_length > target_chars and current_chunk:
                    chunks.append(". ".join(current_chunk) + ".")
                    current_chunk = [sentence]
                    current_length = sentence_length
                else:
                    current_chunk.append(sentence)
                    current_length += sentence_length
            
            # Add remaining chunk
            if current_chunk:
                chunks.append(". ".join(current_chunk))
            
            logger.info(f"[Multimodal] Split text into {len(chunks)} chunks")
            return chunks
        
        except Exception as e:
            logger.error(f"[Multimodal] Error chunking text: {e}")
            return [text]  # Return original if chunking fails


class MultimodalRetrieval:
    """Multimodal document retrieval service."""
    
    _instance = None
    
    def __new__(cls):
        """Singleton pattern."""
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialized = False
        return cls._instance
    
    def __init__(self):
        if self._initialized:
            return
        
        from services.mongodb_service import get_db
        
        self.db = get_db()
        self.extractor = DocumentExtractor()
        self._setup_collections()
        
        # Try to load sentence transformer for embeddings
        self.embeddings_model = None
        self._load_embeddings_model()
        
        self._initialized = True
        logger.info("[Multimodal] Retrieval service initialized")
    
    def _setup_collections(self):
        """Setup MongoDB collections."""
        chunks = self.db["document_chunks"]
        chunks.create_index([("source_document", 1)])
        chunks.create_index([("source_type", 1)])
        chunks.create_index([("created_at", -1)])
        
        embeddings = self.db["chunk_embeddings"]
        embeddings.create_index([("chunk_id", 1)])
        embeddings.create_index([("source_document", 1)])
    
    def _load_embeddings_model(self):
        """Load SentenceTransformers model."""
        try:
            from sentence_transformers import SentenceTransformer
            
            self.embeddings_model = SentenceTransformer("BAAI/bge-large-en-v1.5")
            logger.info("[Multimodal] Loaded embeddings model: BAAI/bge-large-en-v1.5 (1024-dim)")
        except ImportError:
            logger.warning("[Multimodal] sentence-transformers not installed. "
                          "Install: pip install sentence-transformers")
            self.embeddings_model = None
        except Exception as e:
            logger.error(f"[Multimodal] Error loading embeddings model: {e}")
            self.embeddings_model = None
    
    def ingest_document(self, file_path: str, metadata: Optional[Dict] = None) -> Dict:
        """
        Ingest a document (PDF, image, text, markdown).
        
        Steps:
        1. Extract text from document
        2. Chunk into 256-token windows
        3. Generate embeddings
        4. Store in MongoDB
        5. Optionally upsert to Pinecone
        
        Args:
            file_path: Path to document file
            metadata: Optional metadata to attach
        
        Returns:
            Dict with ingestion status and chunk count
        """
        try:
            logger.info(f"[Multimodal] Ingesting document: {file_path}")
            
            # 1. Extract text
            text, source_type = self.extractor.extract_text(file_path)
            if not text:
                return {"success": False, "error": f"Failed to extract text from {file_path}"}
            
            # 2. Chunk text
            chunks = self.extractor.chunk_text(text)
            
            # 3. Store chunks
            doc_name = Path(file_path).name
            stored_chunks = []
            
            for idx, chunk_text in enumerate(chunks):
                chunk_id = f"{doc_name}_{idx}"
                token_count = len(chunk_text) // 4  # rough estimate
                
                chunk = {
                    "chunk_id": chunk_id,
                    "source_document": doc_name,
                    "source_type": source_type,
                    "content": chunk_text,
                    "chunk_index": idx,
                    "token_count": token_count,
                    "metadata": metadata or {},
                    "created_at": datetime.utcnow(),
                }
                
                self.db["document_chunks"].insert_one(chunk)
                stored_chunks.append(chunk_id)
                
                # 4. Generate and store embedding
                if self.embeddings_model:
                    try:
                        embedding = self.embeddings_model.encode(chunk_text).tolist()
                        
                        embedding_record = {
                            "chunk_id": chunk_id,
                            "content": chunk_text,
                            "embedding": embedding,
                            "token_count": token_count,
                            "source_document": doc_name,
                            "source_type": source_type,
                            "created_at": datetime.utcnow(),
                        }
                        
                        self.db["chunk_embeddings"].insert_one(embedding_record)
                        
                        # TODO: Optionally upsert to Pinecone here
                        # from services.pinecone_service import get_pinecone_client
                        # pc = get_pinecone_client()
                        # pc.upsert(vectors=[(chunk_id, embedding, {"source": doc_name})])
                    
                    except Exception as e:
                        logger.warning(f"[Multimodal] Error embedding chunk {chunk_id}: {e}")
            
            logger.info(f"[Multimodal] Ingested {len(stored_chunks)} chunks from {doc_name}")
            
            return {
                "success": True,
                "document": doc_name,
                "source_type": source_type,
                "chunks_count": len(stored_chunks),
                "total_tokens": sum(len(c) // 4 for c in chunks),
            }
        
        except Exception as e:
            logger.error(f"[Multimodal] Error ingesting document: {e}")
            raise
    
    def retrieve_similar_chunks(self, query: str, top_k: int = 5,
                               source_type: Optional[str] = None) -> List[Dict]:
        """
        Retrieve similar chunks for a query using vector similarity.
        
        Args:
            query: Search query text
            top_k: Number of results to return
            source_type: Filter by source type (optional)
        
        Returns:
            List of similar chunks with similarity scores
        """
        try:
            if not self.embeddings_model:
                logger.warning("[Multimodal] Embeddings model not available")
                return []
            
            # Encode query
            query_embedding = self.embeddings_model.encode(query)
            
            # Retrieve all embeddings
            filter_query = {}
            if source_type:
                filter_query["source_type"] = source_type
            
            stored_embeddings = list(self.db["chunk_embeddings"].find(filter_query))
            
            if not stored_embeddings:
                logger.warning("[Multimodal] No embeddings found in database")
                return []
            
            # Compute similarity scores (cosine)
            import numpy as np
            
            similarities = []
            for doc in stored_embeddings:
                stored_vec = np.array(doc["embedding"])
                query_vec = np.array(query_embedding)
                
                # Cosine similarity
                similarity = np.dot(stored_vec, query_vec) / (
                    np.linalg.norm(stored_vec) * np.linalg.norm(query_vec)
                )
                
                similarities.append({
                    "chunk_id": doc["chunk_id"],
                    "content": doc["content"],
                    "similarity": float(similarity),
                    "source_document": doc["source_document"],
                    "source_type": doc["source_type"],
                    "token_count": doc["token_count"],
                })
            
            # Sort and return top-k
            similarities.sort(key=lambda x: x["similarity"], reverse=True)
            
            logger.info(f"[Multimodal] Retrieved {len(similarities[:top_k])} similar chunks")
            return similarities[:top_k]
        
        except Exception as e:
            logger.error(f"[Multimodal] Error retrieving similar chunks: {e}")
            return []
    
    def search_documents(self, query: str, top_k: int = 5) -> List[Dict]:
        """
        Search documents by keyword (fallback to keyword search).
        
        Args:
            query: Search query
            top_k: Number of results
        
        Returns:
            List of matching chunks
        """
        try:
            # MongoDB text search (requires text index)
            # Fallback: simple keyword matching
            
            results = list(self.db["document_chunks"].find(
                {"content": {"$regex": query, "$options": "i"}}
            ).limit(top_k))
            
            logger.info(f"[Multimodal] Keyword search found {len(results)} results")
            
            return [
                {
                    "chunk_id": r["chunk_id"],
                    "content": r["content"],
                    "source_document": r["source_document"],
                    "source_type": r["source_type"],
                }
                for r in results
            ]
        
        except Exception as e:
            logger.error(f"[Multimodal] Error in keyword search: {e}")
            return []
    
    def get_document_stats(self, source_document: str) -> Dict:
        """Get statistics about an ingested document."""
        try:
            chunks = list(self.db["document_chunks"].find(
                {"source_document": source_document}
            ))
            
            if not chunks:
                return {"found": False}
            
            total_tokens = sum(c["token_count"] for c in chunks)
            avg_chunk_size = total_tokens / len(chunks) if chunks else 0
            
            return {
                "found": True,
                "source_document": source_document,
                "source_type": chunks[0]["source_type"],
                "chunk_count": len(chunks),
                "total_tokens": total_tokens,
                "avg_chunk_tokens": avg_chunk_size,
                "ingested_at": chunks[0]["created_at"].isoformat() if chunks else None,
            }
        
        except Exception as e:
            logger.error(f"[Multimodal] Error getting document stats: {e}")
            raise


# Singleton accessor
def get_multimodal_retrieval() -> MultimodalRetrieval:
    """Get or create the MultimodalRetrieval singleton."""
    return MultimodalRetrieval()
