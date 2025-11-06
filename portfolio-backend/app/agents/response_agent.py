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
        content = msg.get("content", "")[:200]  # Truncate long messages
        formatted += f"**{role}**: {content}\n"
    
    return formatted

async def generate_response_with_history(
    query: str,
    mode: str,
    context_chunks: List[RetrievedChunk],
    conversation_history: Optional[List[Dict]] = None,
    revision_feedback: Optional[List[str]] = None
) -> str:
    """Generate response with conversation memory"""
    
    system_prompt = SYSTEM_PROMPTS.get(mode, SYSTEM_PROMPTS.get("ama", ""))
    
    # Format context
    context_str = ""
    for idx, chunk in enumerate(context_chunks):
        source = chunk.source or "Unknown"
        context_str += f"[Source {idx + 1}: {source}]\n{chunk.content}\n\n"
    
    # Add conversation history
    conversation_context = _format_conversation_history(conversation_history or [])
    
    user_prompt = f"""Portfolio Context:
{context_str}

{conversation_context}

Current Question: {query}"""
    
    if revision_feedback:
        user_prompt += f"\n\n**Improvement Notes:**\n"
        for feedback in revision_feedback:
            user_prompt += f"- {feedback}\n"
        user_prompt += "\nPlease revise your response addressing these concerns."
    
    try:
        completion = client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt}
            ],
            temperature=0.3 if mode != "ama" else 0.7,
            max_tokens=400 if mode == "recruiter" else 800,
            stream=False
        )
        
        response = completion.choices[0].message.content
        logger.info(f"✓ Generated response with conversation context ({len(response)} chars)")
        return response
        
    except Exception as e:
        logger.error(f"Response generation error: {e}")
        return "I encountered an error. Please try again."

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