from fastapi import APIRouter, HTTPException
from app.models.schemas import ChatRequest, ChatResponse
from app.agents.mode_detector import detect_mode
from app.agents.rag_agent import retrieve_relevant_chunks
from app.agents.response_agent import generate_response
from app.agents.judge_agent import judge_response, should_revise, should_reject
from app.models.database import db
import logging

logger = logging.getLogger(__name__)

router = APIRouter()

@router.post("/chat", response_model=ChatResponse)
async def chat(request: ChatRequest):
    """Main chat endpoint with validation loop"""
    
    try:
        # Step 1: Detect mode
        if request.mode and request.mode in ["recruiter", "engineer", "ama"]:
            mode = request.mode
            logger.info(f"Mode: {mode} (explicit)")
        else:
            detection = await detect_mode(request.message)
            mode = detection["mode"]
            confidence = detection.get("confidence", 0)
            logger.info(f"Mode: {mode} (detected, confidence: {confidence:.2f})")
        
        # Step 2: RAG - Retrieve context
        chunks = await retrieve_relevant_chunks(request.message, top_k=5)
        
        if not chunks:
            logger.warning("No relevant chunks found")
            return ChatResponse(
                response="I don't have enough information in my portfolio to answer that question reliably. Could you ask about one of my documented projects?",
                mode=mode,
                judge_score=None,
                sources=[]
            )
        
        logger.info(f"Retrieved {len(chunks)} chunks")
        
        # Step 3: Generate initial response
        logger.info("Generating response...")
        response_text = await generate_response(
            request.message,
            mode,
            chunks
        )
        
        logger.info(f"Response generated: {len(response_text)} chars")
        
        # Step 4: Judge validation (skip for recruiter mode)
        judge_score = None
        revision_count = 0
        max_revisions = 2
        
        if mode != "recruiter":
            logger.info("Evaluating response quality...")
            judge_score = await judge_response(response_text, chunks, mode)
            
            logger.info(f"Judge scores - Grounding: {judge_score.grounding_score}, Consistency: {judge_score.consistency_score}, Depth: {judge_score.depth_score}, Specificity: {judge_score.specificity_score}")
            logger.info(f"Average: {judge_score.average_score:.1f}/10")
            
            # Step 5: Revision loop
            while should_revise(judge_score) and revision_count < max_revisions:
                revision_count += 1
                logger.info(f"🔄 Revision {revision_count}/{max_revisions} - Issues: {judge_score.feedback}")
                
                # Generate improved response
                response_text = await generate_response(
                    request.message,
                    mode,
                    chunks,
                    revision_feedback=judge_score.feedback
                )
                
                # Re-judge
                judge_score = await judge_response(response_text, chunks, mode)
                logger.info(f"After revision - Average: {judge_score.average_score:.1f}/10")
            
            # If still bad after revisions, be honest
            if should_reject(judge_score):
                logger.warning("Response rejected after revisions")
                response_text = f"I apologize, but I cannot provide a sufficiently grounded response to your question. The issues are: {', '.join(judge_score.feedback)}. Please try asking about a more documented aspect of my portfolio."
        
        sources = list(set([chunk.source for chunk in chunks]))
        
        return ChatResponse(
            response=response_text,
            mode=mode,
            judge_score=judge_score,
            sources=sources
        )
        
    except Exception as e:
        logger.error(f"Chat error: {e}")
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))
