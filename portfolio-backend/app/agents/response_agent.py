import logging
from typing import List, Optional, Dict
from groq import Groq

from app.config import SYSTEM_PROMPTS, settings
from app.models.schemas import RetrievedChunk

logger = logging.getLogger(__name__)

client = Groq(api_key=settings.GROQ_API_KEY)

def _format_conversation_history(conversation_history: List[Dict]) -> str:
    """Format conversation history for context"""
    if not conversation_history:
        return ""
    
    formatted = "\n\n## Previous Conversation Context:\n"
    for msg in conversation_history[-6:]:  # Last 3 turns (6 messages)
        role = msg.get("role", "unknown").upper()
        content = msg.get("content", "")
        if len(content) > 250:
            content = content[:250] + "..."
        formatted += f"**{role}**: {content}\n"
    
    return formatted

def _extract_follow_up_project(conversation_history: List[Dict]) -> Optional[str]:
    """Extract which project the user was just discussing"""
    if not conversation_history or len(conversation_history) < 2:
        return None
    
    # Get last assistant response (should have sources)
    for msg in reversed(conversation_history):
        if msg.get("role") == "assistant":
            content = msg.get("content", "")
            
            # Extract source from [source: project_name]
            import re
            sources = re.findall(r'\[source:\s*([^\]]+)\]', content)
            
            if sources:
                project = sources[0].strip()
                logger.info(f"📌 Detected project context: {project}")
                return project
    
    return None

async def generate_response_with_history(
    query: str,
    mode: str,
    context_chunks: List[RetrievedChunk],
    conversation_history: Optional[List[Dict]] = None,
    revision_feedback: Optional[List[str]] = None,
    stream: bool = True,
) -> str:
    """Generate response WITH FOCUSED CONTEXT"""
    
    system_prompt = SYSTEM_PROMPTS.get(mode, SYSTEM_PROMPTS.get("ama", ""))
    
    # CRITICAL: If this is follow-up, filter chunks to ONLY relevant project
    detected_project = _extract_follow_up_project(conversation_history or [])
    
    if detected_project and conversation_history and len(conversation_history) >= 2:
        # This is likely a follow-up question
        logger.info(f"🔄 Follow-up detected - Filtering to {detected_project} only")
        
        # Filter chunks to only the detected project
        filtered_chunks = [
            chunk for chunk in context_chunks 
            if chunk.source and chunk.source.lower() == detected_project.lower()
        ]
        
        if filtered_chunks:
            logger.info(f"Filtered {len(context_chunks)} → {len(filtered_chunks)} chunks")
            context_chunks = filtered_chunks
        else:
            logger.warning(f"No chunks found for {detected_project}, using all")
    
    # Format context
    context_str = ""
    for idx, chunk in enumerate(context_chunks):
        source = chunk.source or "Unknown"
        context_str += f"[Source {idx + 1}: {source}]\n{chunk.content}\n\n"
    
    # Format conversation history
    conversation_context = ""
    if conversation_history and len(conversation_history) >= 2:
        conversation_context = "\n\n## Previous Conversation Context:\n"
        
        # Show last 4 messages (2 turns)
        for msg in conversation_history[-4:]:
            role = msg.get("role", "unknown").upper()
            content = msg.get("content", "")[:200]
            conversation_context += f"**{role}**: {content}\n"
    
    user_prompt = f"""Portfolio Context:
{context_str}

{conversation_context}

Current Question: {query}

---
If this is a follow-up question, focus ONLY on the project previously discussed and answer in that context."""
    
    if revision_feedback:
        user_prompt += f"\n\n**Improvement Notes:**\n"
        for feedback in revision_feedback:
            user_prompt += f"- {feedback}\n"
        user_prompt += "\nPlease revise your response addressing these concerns."
    
    try:
        logger.info(f"Generating response (stream={stream})")
        
        completion = client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt}
            ],
            temperature=0.3 if mode != "ama" else 0.7,
            max_tokens=800,
            stream=stream 
        )
        
        if stream:
            # STREAMING MODE - Handle Groq's response format
            full_response = ""
            
            try:
                # Groq returns an iterator, NOT a list
                for chunk in completion:
                    # Check if chunk has choices
                    if hasattr(chunk, 'choices') and len(chunk.choices) > 0:
                        delta = chunk.choices.delta
                        
                        # Check if delta has content
                        if hasattr(delta, 'content') and delta.content:
                            token = delta.content
                            full_response += token
                            await token 
                
                logger.info(f"✓ Streamed response ({len(full_response)} chars)")
                return full_response
                
            except Exception as e:
                logger.error(f"Streaming error: {e}")
                # Fallback to non-streaming
                return "I encountered an error during streaming. Please try again."
        
        else:
            # NON-STREAMING MODE
            response = completion.choices[0].message.content
            logger.info(f"✓ Generated response ({len(response)} chars)")
            return response
        
    except Exception as e:
        logger.error(f"Response generation error: {e}")
        return "I encountered an error generating a response. Please try again."

# Backward compatibility
async def generate_response(
    query: str,
    mode: str,
    context_chunks: List[RetrievedChunk],
    revision_feedback: Optional[List[str]] = None
) -> str:
    """Backward compatible function"""
    return await generate_response_with_history(
        query,
        mode,
        context_chunks,
        conversation_history=None,
        revision_feedback=revision_feedback
    )