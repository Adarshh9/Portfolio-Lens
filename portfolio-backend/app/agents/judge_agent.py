import logging
from groq import Groq
from app.config import JUDGE_RUBRIC, settings
from app.models.schemas import RetrievedChunk, JudgeScore
from typing import List, Optional
import json

logger = logging.getLogger(__name__)

client = Groq(api_key=settings.GROQ_API_KEY)

async def judge_response(
    response_text: str,
    context_chunks: List[RetrievedChunk]
) -> JudgeScore:
    """Validate response using judge agent"""
    
    context_str = "\n\n".join([
        f"**{chunk.source}**: {chunk.content[:200]}..."
        for chunk in context_chunks
    ])
    
    prompt = f"""{JUDGE_RUBRIC}

Response to evaluate:
\"\"\"{response_text}\"\"\"

Portfolio context:
\"\"\"{context_str}\"\"\"

Evaluate strictly and return JSON only."""
    
    try:
        completion = client.chat.completions.create(
            model="llama-3.1-8b-instant",
            messages=[{"role": "user", "content": prompt}],
            temperature=0,
            max_tokens=500,
            stream=True,
            top_p=1,
            stop=None
        )
        
        content = ""
        for chunk in completion:
            delta = chunk.choices[0].delta
            if delta and delta.content:
                content += delta.content
        
        # Extract JSON
        json_start = content.find("{")
        json_end = content.rfind("}") + 1
        
        if json_start == -1 or json_end == 0:
            return get_default_score()
        
        json_str = content[json_start:json_end]
        parsed = json.loads(json_str)
        
        return JudgeScore(
            grounding_score=parsed.get("grounding_score", 0),
            consistency_score=parsed.get("consistency_score", 0),
            depth_score=parsed.get("depth_score", 0),
            revision_required=parsed.get("revision_required", False),
            feedback=parsed.get("feedback", []),
            citations_used=parsed.get("citations_used", [])
        )
        
    except Exception as e:
        logger.error(f"Judge error: {e}")
        return get_default_score()

def get_default_score() -> JudgeScore:
    """Default score when judge fails"""
    return JudgeScore(
        grounding_score=0,
        consistency_score=0,
        depth_score=0,
        revision_required=True,
        feedback=["Judge evaluation failed"],
        citations_used=[]
    )

def should_revise(score: JudgeScore) -> bool:
    """Check if response needs revision"""
    return (
        score.grounding_score < 3 or
        score.consistency_score < 3 or
        score.revision_required
    )
