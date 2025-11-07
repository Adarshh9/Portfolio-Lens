import logging
from fastapi import APIRouter, HTTPException
from fastapi.responses import StreamingResponse
from typing import Optional, List
import json
import asyncio
from datetime import datetime

from app.models.schemas import ChatRequest, ChatResponse
from app.agents.mode_detector import detect_mode
from app.agents.advanced_rag import advanced_rag
from app.agents.response_agent import generate_response_with_history
from app.agents.judge_agent import judge_response, should_revise, should_reject
from app.models.database import db
from app.agents.context_filter import smart_context_decision
import uuid as uuid_lib

logger = logging.getLogger(__name__)
router = APIRouter()

@router.post("/chat", response_model=ChatResponse)
async def chat(request: ChatRequest):
    """Main chat endpoint with PROPER follow-up handling"""
    
    try:
        # Step 1: Session management
        session_id = request.session_id
        
        if not session_id:
            session_id = await db.create_session()
            logger.info(f"🆕 Created new session: {session_id}")
        else:
            # Verify session exists
            try:
                import uuid
                uuid.UUID(session_id)
                
                sessions = db.client.table("chat_sessions").select("id").eq("id", session_id).limit(1).execute()
                
                if not sessions.data or len(sessions.data) == 0:
                    logger.warning(f"Session {session_id} not found, creating...")
                    # Create session without user_id
                    db.client.table("chat_sessions").insert({
                        "id": session_id,
                        "created_at": datetime.now().isoformat()
                    }).execute()
                    logger.info(f"✓ Created session in DB: {session_id}")
                    
            except Exception as e:
                logger.error(f"Session validation error: {e}")
                session_id = await db.create_session()
        
        # Step 2: Detect mode
        if request.mode and request.mode in ["recruiter", "engineer", "ama"]:
            mode = request.mode
        else:
            detection = await detect_mode(request.message)
            mode = detection.get("mode", "ama")
        
        logger.info(f"💬 Chat Request - Mode: {mode}, Query: {request.message[:50]}...")
        
        # Step 3: Get conversation history FIRST
        conversation_history = []
        if session_id:
            try:
                conversation_history = await db.get_conversation_history(session_id, limit=6)
                logger.info(f"📖 Loaded {len(conversation_history)} previous messages for session {session_id}")
            except Exception as e:
                logger.warning(f"Could not load conversation history: {e}")
        
        # # Step 4: CRITICAL - Determine if this is a follow-up
        # is_followup = len(conversation_history) >= 2
        # followup_project = None
        
        # if is_followup:
        #     # Extract project from last assistant message
        #     for msg in reversed(conversation_history):
        #         if msg.get("role") == "assistant":
        #             content = msg.get("content", "")
                    
        #             # Extract [source: project_name] from response
        #             import re
        #             sources = re.findall(r'\[source:\s*([^\]]+)\]', content)

        #             if sources and len(sources) > 0:
        #                 followup_project = sources[0].strip()
        #                 logger.info(f"🔄 Follow-up detected! Previous project: {followup_project}")
        #                 break
        
        # # Step 5: RAG retrieval
        # logger.info("📚 Starting advanced RAG retrieval...")
        # try:
        #     chunks = await advanced_rag.retrieve_advanced(request.message, top_k=5)
        # except Exception as e:
        #     logger.error(f"RAG retrieval failed: {e}")
        #     chunks = []
        
        # if not chunks:
        #     logger.warning("⚠️ No relevant chunks found")
        #     return ChatResponse(
        #         response="I don't have enough information in my portfolio to answer that question. Try asking about:\n- TaxoCapsNet\n- Finsaathi\n- Nutri-AI\n- ProdML\n- Doc-QA",
        #         mode=mode,
        #         judge_score=None,
        #         sources=[]
            # )
        
        # # Step 6: FILTER chunks if this is a follow-up
        # if followup_project:
        #     logger.info(f"🔍 Filtering {len(chunks)} chunks to project: {followup_project}")
            
        #     filtered_chunks = [
        #         chunk for chunk in chunks
        #         if chunk.source and chunk.source.lower() == followup_project.lower()
        #     ]
            
        #     if filtered_chunks:
        #         logger.info(f"✓ Filtered to {len(filtered_chunks)} chunks from {followup_project}")
        #         chunks = filtered_chunks
        #     else:
        #         logger.warning(f"No chunks found for {followup_project}, using all")
        
        # logger.info(f"✅ Retrieved {len(chunks)} chunks")

        # Step 4: SEMANTIC - Smart context decision
        followup_project = None

        # Extract previous project from conversation
        if len(conversation_history) >= 2:
            for msg in reversed(conversation_history):
                if msg.get("role") == "assistant":
                    content = msg.get("content", "")
                    
                    import re
                    sources = re.findall(r'\[source:\s*([^\]]+)\]', content)
                    
                    if sources:
                        followup_project = sources[0].strip()
                        logger.info(f"📚 Previous project detected: {followup_project}")
                        break

        # Use semantic approach to decide if we should filter
        context_decision = await smart_context_decision(
            current_query=request.message,
            conversation_history=conversation_history,
            previous_project=followup_project,
            use_llm=True,
            use_embeddings=True
        )

        logger.info(f"🧠 Context Decision: {context_decision['reasoning']}")

        # Step 5: RAG retrieval
        logger.info("📚 Starting advanced RAG retrieval...")
        try:
            chunks = await advanced_rag.retrieve_advanced(request.message, top_k=5)
        except Exception as e:
            logger.error(f"RAG retrieval failed: {e}")
            chunks = []

        if not chunks:
            logger.warning("⚠️ No relevant chunks found")
            return ChatResponse(
                response="I don't have enough information in my portfolio to answer that question. Try asking about:\n- TaxoCapsNet\n- Finsaathi\n- Nutri-AI\n- ProdML\n- Doc-QA",
                mode=mode,
                judge_score=None,
                sources=[]
            )

        # Step 6: CONDITIONALLY filter chunks based on semantic decision
        if context_decision['should_filter'] and context_decision['target_project']:
            target = context_decision['target_project'].lower()
            filtered_chunks = [
                c for c in chunks 
                if c.source and c.source.lower() == target
            ]
            
            if filtered_chunks:
                chunks = filtered_chunks
                logger.info(f"✂️ Filtered to {len(chunks)} chunks for {target}")
            else:
                logger.info(f"⚠️ No chunks for {target}, using all {len(chunks)} chunks")
        else:
            logger.info(f"🌐 Using all {len(chunks)} chunks (context: {context_decision['reasoning'][:40]}...)")

        logger.info(f"✅ Retrieved {len(chunks)} chunks")

        
        # Step 7: Generate response
        logger.info("🤖 Generating response...")
        try:
            response_text = await generate_response_with_history(
                request.message,
                mode,
                chunks,
                conversation_history=conversation_history,
                stream=False  # Use stream=True for streaming endpoint
            )
        except Exception as e:
            logger.error(f"Response generation failed: {e}")
            return ChatResponse(
                response="I encountered an error generating a response. Please try again.",
                mode=mode,
                judge_score=None,
                sources=[c.source for c in chunks]
            )
        
        logger.info(f"✅ Response generated ({len(response_text)} chars)")
        
        # Step 8: Judge validation (skip for recruiter)
        judge_score = None
        if mode != "recruiter":
            try:
                judge_score = await judge_response(response_text, chunks, mode)
                logger.info(f"📊 Initial Judge Score: {judge_score.average_score:.1f}/10")
                
                # Revision loop
                revision_count = 0
                max_revisions = 2
                
                while should_revise(judge_score) and revision_count < max_revisions:
                    revision_count += 1
                    logger.info(f"🔄 Revision {revision_count}: {judge_score.feedback}")
                    
                    response_text = await generate_response_with_history(
                        request.message,
                        mode,
                        chunks,
                        revision_feedback=judge_score.feedback,
                        conversation_history=conversation_history,
                        stream=False
                    )
                    
                    judge_score = await judge_response(response_text, chunks, mode)
                    logger.info(f"📊 Judge Score After Revision {revision_count}: {judge_score.average_score:.1f}/10")
                
                if should_reject(judge_score):
                    logger.warning("❌ Response rejected after revisions")
                    response_text = f"I apologize, but I cannot provide a confident answer. Issues: {', '.join(judge_score.feedback)}"
            
            except Exception as e:
                logger.warning(f"Judge evaluation failed: {e}")
                judge_score = None
        
        # Step 9: Save conversation
        if session_id:
            try:
                await db.save_message(session_id, "user", request.message)
                await db.save_message(session_id, "assistant", response_text)
            except Exception as e:
                logger.warning(f"Could not save conversation: {e}")
        
        # Step 10: Log analytics
        sources = list(set([chunk.source for chunk in chunks]))
        try:
            await db.log_query(
                request.message,
                mode,
                judge_score.average_score if judge_score else 0,
                sources
            )
        except Exception as e:
            logger.warning(f"Could not log analytics: {e}")
        
        logger.info(f"✅ Chat complete. Sources used: {sources}")
        
        return ChatResponse(
            response=response_text,
            mode=mode,
            judge_score=judge_score,
            sources=sources
        )
        
    except Exception as e:
        logger.error(f"❌ CRITICAL Chat error: {e}")
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/chat/stream")
async def chat_stream(request: ChatRequest):
    """Streaming chat endpoint - FIXED VERSION"""
    
    async def generate():
        """Generator for streaming responses"""
        
        try:
            # Setup (same as regular chat)
            session_id = request.session_id or await db.create_session()
            
            # Ensure session exists
            try:
                sessions = db.client.table("chat_sessions").select("id").eq("id", session_id).limit(1).execute()
                if not sessions.data:
                    db.client.table("chat_sessions").insert({
                        "id": session_id,
                        "created_at": datetime.now().isoformat()
                    }).execute()
            except:
                pass
            
            mode = request.mode if request.mode in ["recruiter", "engineer", "ama"] else (await detect_mode(request.message)).get("mode", "ama")
            
            # Get conversation history
            conversation_history = []
            try:
                conversation_history = await db.get_conversation_history(session_id, limit=6)
            except:
                pass
            
            # Detect follow-up
            is_followup = len(conversation_history) >= 2
            followup_project = None

            if is_followup:
                for msg in reversed(conversation_history):
                    if msg.get("role") == "assistant":
                        import re
                        sources = re.findall(r'\[source:\s*([^\]]+)\]', msg.get("content", ""))
                        if sources and len(sources) > 0:
                            followup_project = sources[0].strip()   
                            break

            # RAG retrieval
            chunks = await advanced_rag.retrieve_advanced(request.message, top_k=5)
            
            if not chunks:
                yield json.dumps({"type": "error", "message": "No relevant information found"}) + "\n"
                return
            
            # Filter for follow-up
            if followup_project:
                filtered = [c for c in chunks if c.source and c.source.lower() == followup_project.lower()]
                if filtered:
                    chunks = filtered
            
            sources = list(set([c.source for c in chunks]))
            
            # Send start event
            yield json.dumps({
                "type": "start",
                "mode": mode,
                "session_id": session_id,
                "sources": sources
            }) + "\n"
            
            # Generate with streaming
            full_response = ""
            
            async for token in generate_response_with_history(
                request.message,
                mode,
                chunks,
                conversation_history=conversation_history,
                stream=True  # ← ENABLE STREAMING
            ):
                full_response += token
                yield json.dumps({"type": "token", "content": token}) + "\n"
                await asyncio.sleep(0)  # Allow other tasks to run
            
            # Judge score
            judge_score = None
            try:
                if mode != "recruiter":
                    judge_score = await judge_response(full_response, chunks, mode)
            except:
                pass
            
            # Save messages
            try:
                await db.save_message(session_id, "user", request.message)
                await db.save_message(session_id, "assistant", full_response)
            except:
                pass
            
            # Log analytics
            try:
                await db.log_query(request.message, mode, judge_score.average_score if judge_score else 0, sources)
            except:
                pass
            
            # Send end event
            yield json.dumps({
                "type": "end",
                "session_id": session_id,
                "judge_score": judge_score.average_score if judge_score else 0,
                "sources": sources
            }) + "\n"
            
        except Exception as e:
            logger.error(f"Streaming error: {e}")
            yield json.dumps({"type": "error", "message": str(e)}) + "\n"
    
    return StreamingResponse(generate(), media_type="application/x-ndjson")
