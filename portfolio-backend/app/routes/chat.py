from fastapi import APIRouter, HTTPException
from app.models.schemas import ChatRequest, ChatResponse, JudgeScore
from app.agents.mode_detector import detect_mode
from app.agents.rag_agent import retrieve_relevant_chunks
from app.agents.response_agent import generate_response
from app.agents.judge_agent import judge_response, should_revise
from app.models.database import db
from uuid import uuid4
import logging

logger = logging.getLogger(__name__)

router = APIRouter()

@router.post("/chat", response_model=ChatResponse)
async def chat(request: ChatRequest):
    """Main chat endpoint"""
    
    try:
        # Step 1: Detect mode
        if request.mode and request.mode in ["recruiter", "engineer", "ama"]:
            mode = request.mode
        else:
            detection = await detect_mode(request.message)
            mode = detection["mode"]
        
        logger.info(f"Mode: {mode}")
        
        # Step 2: RAG - Retrieve context
        chunks = await retrieve_relevant_chunks(request.message, top_k=5)
        
        if not chunks:
            return ChatResponse(
                response="I don't have enough information in my portfolio to answer that question reliably. Could you ask about one of my documented projects?",
                mode=mode,
                judge_score=None,
                sources=[]
            )
        
        # Step 3: Generate response
        response_text = await generate_response(
            request.message,
            mode,
            chunks
        )
        
        # Step 4: Judge validation (skip for recruiter mode)
        judge_score = None
        
        if mode != "recruiter":
            judge_score = await judge_response(response_text, chunks)
            
            # Step 5: Revision loop if needed
            if should_revise(judge_score):
                logger.info("Revising response...")
                
                revised = await generate_response(
                    request.message,
                    mode,
                    chunks,
                    revision_feedback=judge_score.feedback
                )
                
                judge_score = await judge_response(revised, chunks)
                
                if should_revise(judge_score):
                    response_text = f"I don't have sufficient documentation to answer this confidently. Issues: {', '.join(judge_score.feedback)}"
                else:
                    response_text = revised
        
        sources = [chunk.source for chunk in chunks]
        
        return ChatResponse(
            response=response_text,
            mode=mode,
            judge_score=judge_score,
            sources=sources
        )
        
    except Exception as e:
        logger.error(f"Chat error: {e}")
        raise HTTPException(status_code=500, detail=str(e))
