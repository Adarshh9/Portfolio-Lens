import logging
from groq import Groq
from app.config import JUDGE_RUBRIC, settings
from app.models.schemas import RetrievedChunk, ExtendedJudgeScore
from typing import List
import json

logger = logging.getLogger(__name__)

client = Groq(api_key=settings.GROQ_API_KEY)


async def judge_response(
    response_text: str,
    context_chunks: List[RetrievedChunk],
    mode: str = "ama"
) -> ExtendedJudgeScore:
    """Validate response using enhanced judge agent"""

    context_str = "\n\n".join([
        f"**{chunk.source}**: {chunk.content[:200]}..."
        for chunk in context_chunks
    ])

    prompt = f"""{JUDGE_RUBRIC}

Response to evaluate (mode: {mode}):
\"\"\"{response_text}\"\"\"

Portfolio context:
\"\"\"{context_str}\"\"\"

Evaluate strictly and return JSON only."""

    try:
        completion = client.chat.completions.create(
            model="llama-3.1-8b-instant",
            messages=[{"role": "user", "content": prompt}],
            temperature=0,
            max_tokens=800,
            stream=True,
            top_p=1,
            stop=None
        )

        content = ""
        for chunk in completion:
            delta = chunk.choices[0].delta
            if delta and delta.content:
                content += delta.content

        # Extract JSON safely
        json_start = content.find("{")
        json_end = content.rfind("}") + 1

        if json_start == -1 or json_end == 0:
            logger.warning("No JSON found in judge response")
            return get_default_extended_score()

        json_str = content[json_start:json_end]

        parsed = json.loads(json_str)

        # Ensure average score exists
        if "average_score" not in parsed:
            scores = [
                parsed.get("grounding_score", 0),
                parsed.get("consistency_score", 0),
                parsed.get("depth_score", 0),
                parsed.get("specificity_score", 0)
            ]
            parsed["average_score"] = sum(scores) / len(scores) if scores else 0

        # ✅ IMPORTANT: Use keyword unpacking for Pydantic
        return ExtendedJudgeScore(**parsed)

    except Exception as e:
        logger.error(f"Judge error: {e}")
        return get_default_extended_score()


def get_default_extended_score() -> ExtendedJudgeScore:
    """Default score when judge fails"""

    return ExtendedJudgeScore(
        grounding_score=0,
        consistency_score=0,
        depth_score=0,
        specificity_score=0,
        average_score=0,
        revision_required=True,
        reject=False,
        feedback=["Judge evaluation failed, please retry"],
        strengths=[],
        citations_used=[]
    )


def should_revise(score: ExtendedJudgeScore) -> bool:
    return score.should_revise()


def should_reject(score: ExtendedJudgeScore) -> bool:
    return score.should_reject()
