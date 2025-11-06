import logging
from groq import Groq
from app.config import MODE_KEYWORDS, settings
import json

logger = logging.getLogger(__name__)

client = Groq(api_key=settings.GROQ_API_KEY)

async def detect_mode_by_keywords(query: str) -> dict:
    """Keyword-based mode detection (fast path)"""
    query_lower = query.lower()
    scores = {
        "recruiter": 0,
        "engineer": 0,
        "ama": 0
    }
    
    for mode, keywords in MODE_KEYWORDS.items():
        for keyword in keywords:
            if keyword in query_lower:
                scores[mode] += 1
    
    max_score = max(scores.values())
    total_score = sum(scores.values())
    
    if max_score == 0:
        return {
            "mode": "ama",
            "confidence": 0.3,
            "reasoning": "No strong keywords detected, defaulting to AMA"
        }
    
    mode = [m for m, s in scores.items() if s == max_score]
    
    return {
        "mode": mode,
        "confidence": max_score / max(total_score, 1),
        "reasoning": f"Keyword-based: {max_score} matches for {mode}"
    }

async def detect_mode_by_llm(query: str) -> dict:
    """LLM-based mode detection (fallback)"""
    prompt = f"""Classify this query into one of three modes:
- recruiter: hiring-focused, role/experience questions
- engineer: technical deep-dive, architecture questions
- ama: exploratory, opinion, advice questions

Query: "{query}"

Respond with ONLY valid JSON:
{{
  "mode": "recruiter" | "engineer" | "ama",
  "confidence": number between 0 and 1,
  "reasoning": "brief explanation"
}}"""

    try:
        response = client.chat.completions.create(
            model="llama-3.1-8b-instant",
            messages=[{"role": "user", "content": prompt}],
            temperature=0,
            max_tokens=150
        )
        
        content = response.choices.message.content
        parsed = json.loads(content)
        
        return {
            "mode": parsed.get("mode", "ama"),
            "confidence": parsed.get("confidence", 0.5),
            "reasoning": parsed.get("reasoning", "LLM classification")
        }
    except Exception as e:
        logger.error(f"Mode detection error: {e}")
        return {
            "mode": "ama",
            "confidence": 0.3,
            "reasoning": "Error in LLM detection, defaulting to AMA"
        }

async def detect_mode(query: str, use_llm: bool = False) -> dict:
    """Detect interaction mode"""
    if use_llm:
        return await detect_mode_by_llm(query)
    
    result = await detect_mode_by_keywords(query)
    
    # If confidence is too low, use LLM fallback
    if result["confidence"] < 0.4:
        return await detect_mode_by_llm(query)
    
    return result
