from fastapi import APIRouter, HTTPException
from app.models.schemas import IngestRequest, IngestResponse
from app.models.database import db
from app.embeddings.nomic import embedding_model
from app.utils.chunking import chunk_text
import logging

logger = logging.getLogger(__name__)

router = APIRouter()

@router.post("/ingest", response_model=IngestResponse)
async def ingest(request: IngestRequest):
    """Ingest portfolio content"""
    
    try:
        logger.info(f"Ingesting: {request.title}")
        
        # Step 1: Insert document
        logger.info(f"Step 1: Inserting document '{request.title}'...")
        doc = await db.insert_document(
            title=request.title,
            source=request.source,
            project_type=request.project_type,
            content=request.content
        )
        
        logger.info(f"Doc result type: {type(doc)}, value: {doc}")
        
        # Step 2: Validate doc
        if doc is None:
            logger.error("Document insertion returned None")
            raise HTTPException(status_code=500, detail="Document insertion returned None")
        
        if not isinstance(doc, dict):
            logger.error(f"Document is not dict: {type(doc)} = {doc}")
            raise HTTPException(status_code=500, detail="Document is not a dictionary")
        
        if "id" not in doc:
            logger.error(f"Document has no 'id' key: {doc.keys()}")
            raise HTTPException(status_code=500, detail="Document missing 'id' field")
        
        document_id = doc["id"]
        logger.info(f"Step 1 SUCCESS: Document created with id={document_id}")
        
        # Step 3: Chunk content
        logger.info(f"Step 2: Chunking content...")
        chunks = chunk_text(request.content)
        logger.info(f"Step 2 SUCCESS: Created {len(chunks)} chunks")
        
        # Step 4: Process each chunk
        logger.info(f"Step 3: Processing {len(chunks)} chunks...")
        inserted = 0
        
        for idx, chunk in enumerate(chunks):
            try:
                # Generate embedding
                embedding = embedding_model.embed_query(chunk)
                
                # Verify embedding
                if not isinstance(embedding, list):
                    logger.error(f"Embedding is {type(embedding)}, not list")
                    continue
                
                if len(embedding) != 768:
                    logger.error(f"Embedding has {len(embedding)} dims, expected 768")
                    continue
                
                # Insert chunk
                result = await db.insert_chunk(
                    document_id=document_id,
                    content=chunk,
                    embedding=embedding,
                    metadata={
                        "title": request.title,
                        "source": request.source,
                        "project_type": request.project_type,
                        "chunk_index": idx
                    }
                )
                
                if result is not None:
                    inserted += 1
                
            except Exception as e:
                logger.error(f"Error processing chunk {idx}: {e}")
                continue
        
        logger.info(f"Step 3 SUCCESS: Inserted {inserted}/{len(chunks)} chunks")
        
        return IngestResponse(
            success=True,
            document_id=str(document_id),
            chunks_created=inserted
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Ingest error: {e}")
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))
