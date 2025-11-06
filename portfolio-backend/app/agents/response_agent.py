import logging
from groq import Groq
from app.config import SYSTEM_PROMPTS, settings
from app.models.schemas import RetrievedChunk
from typing import List

logger = logging.getLogger(__name__)

client = Groq(api_key=settings.GROQ_API_KEY)

async def generate_response(
    query: str,
    mode: str,
    context_chunks: List[RetrievedChunk],
    revision_feedback: List[str] = None
) -> str:
    """Generate mode-appropriate response using Groq"""
    
    system_prompt = SYSTEM_PROMPTS.get(mode, SYSTEM_PROMPTS["ama"])
    
    # Format context
    context_str = ""
    for idx, chunk in enumerate(context_chunks):
        source = chunk.source or "Unknown"
        context_str += f"[Source {idx + 1}: {source}]\n{chunk.content}\n\n"
    
    user_prompt = f"""Context from portfolio:
{context_str}

User question: {query}"""
    
    if revision_feedback:
        user_prompt += f"\n\nIMPORTANT - Previous response had issues:\n"
        for feedback in revision_feedback:
            user_prompt += f"- {feedback}\n"
        user_prompt += "\nRevise to address these specific concerns."
    
    try:
        completion = client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt}
            ],
            temperature=0.3 if mode != "ama" else 0.7,
            max_tokens=400 if mode == "recruiter" else 800,
            top_p=1,
            stream=True,
            stop=None
        )
        
        response_text = ""
        for chunk in completion:
            delta = chunk.choices[0].delta
            if delta and delta.content:
                response_text += delta.content

        logger.info(f"Generated response ({mode} mode, {len(response_text)} chars)")
        return response_text
        
    except Exception as e:
        logger.error(f"Response generation error: {e}")
        return "I encountered an error generating a response. Please try again."
