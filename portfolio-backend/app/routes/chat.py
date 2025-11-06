import logging
from fastapi import APIRouter, HTTPException
from typing import Optional

from app.models.schemas import ChatRequest, ChatResponse
from app.agents.mode_detector import detect_mode
from app.agents.advanced_rag import advanced_rag
from app.agents.response_agent import generate_response_with_history
from app.agents.judge_agent import judge_response, should_revise, should_reject
from app.models.database import db

logger = logging.getLogger(__name__)

router = APIRouter()

@router.post("/chat", response_model=ChatResponse)
async def chat(request: ChatRequest):
    """Main chat endpoint with advanced RAG + conversation memory"""
    
    try:
        # Step 1: Detect mode
        if request.mode and request.mode in ["recruiter", "engineer", "ama"]:
            mode = request.mode
        else:
            detection = await detect_mode(request.message)
            mode = detection.get("mode", "ama")
        
        logger.info(f"💬 Chat Request - Mode: {mode}, Query: {request.message[:50]}...")
        
        # Step 2: Retrieve with advanced RAG
        logger.info("📚 Starting advanced RAG retrieval...")
        chunks = await advanced_rag.retrieve_advanced(request.message, top_k=5)
        
        if not chunks:
            logger.warning("⚠️ No relevant chunks found")
            return ChatResponse(
                response="I don't have enough information in my portfolio to answer that question. Try asking about my projects, skills, or experience.",
                mode=mode,
                judge_score=None,
                sources=[]
            )
        
        # Step 3: Get conversation history (last 3 turns)
        conversation_history = []
        if request.session_id:
            try:
                conversation_history = await db.get_conversation_history(
                    session_id=request.session_id,
                    limit=6  # 3 turns (user + assistant)
                )
                logger.info(f"📖 Loaded {len(conversation_history)} previous messages")
            except Exception as e:
                logger.warning(f"Could not load conversation history: {e}")
        
        # Step 4: Generate response with conversation context
        logger.info("🤖 Generating response...")
        response_text = await generate_response_with_history(
            request.message,
            mode,
            chunks,
            conversation_history=conversation_history
        )
        
        logger.info(f"✓ Response generated: {len(response_text)} chars")
        
        # Step 5: Judge validation
        judge_score = None
        revision_count = 0
        max_revisions = 2
        
        if mode != "recruiter":
            judge_score = await judge_response(response_text, chunks, mode)
            logger.info(f"📊 Judge Score: {judge_score.average_score:.1f}/10")
            
            # Revision loop
            while should_revise(judge_score) and revision_count < max_revisions:
                revision_count += 1
                logger.info(f"🔄 Revision {revision_count}: {judge_score.feedback}")
                
                response_text = await generate_response_with_history(
                    request.message,
                    mode,
                    chunks,
                    revision_feedback=judge_score.feedback,
                    conversation_history=conversation_history
                )
                
                judge_score = await judge_response(response_text, chunks, mode)
            
            if should_reject(judge_score):
                logger.warning("❌ Response rejected after revisions")
                response_text = f"I apologize, but I cannot provide a confident answer. Issues: {', '.join(judge_score.feedback)}"
        
        # Step 6: Save conversation message
        if request.session_id:
            try:
                await db.save_message(
                    session_id=request.session_id,
                    role="user",
                    content=request.message
                )
                await db.save_message(
                    session_id=request.session_id,
                    role="assistant",
                    content=response_text
                )
            except Exception as e:
                logger.warning(f"Could not save conversation: {e}")
        
        # Step 7: Log to analytics
        sources = list(set([chunk.source for chunk in chunks]))
        try:
            await db.log_query(
                query=request.message,
                mode=mode,
                response_quality=judge_score.average_score if judge_score else 0,
                sources=sources
            )
        except Exception as e:
            logger.warning(f"Could not log to analytics: {e}")
        
        logger.info(f"✓ Response complete. Sources: {sources}")
        
        return ChatResponse(
            response=response_text,
            mode=mode,
            judge_score=judge_score,
            sources=sources
        )
        
    except Exception as e:
        logger.error(f"❌ Chat error: {e}")
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))