import logging
import json
from typing import Optional, Dict, List
from groq import Groq
from app.config import settings

logger = logging.getLogger(__name__)
client = Groq(api_key=settings.GROQ_API_KEY)


async def analyze_query_intent(
    current_query: str,
    conversation_history: List[Dict],
    previous_project: Optional[str] = None
) -> Dict[str, any]:
    """
    Use LLM to understand query intent and decide context filtering
    
    Returns:
        {
            "intent": "expand" | "clarify" | "compare" | "new_topic",
            "should_filter": bool,
            "target_project": str | None,
            "reasoning": str
        }
    """
    
    # Format conversation context
    history_str = ""
    if conversation_history:
        for msg in conversation_history[-4:]:  # Last 2 turns
            role = msg.get("role", "").upper()
            content = msg.get("content", "")[:200]
            history_str += f"{role}: {content}\n"
    
    prompt = f"""You are a conversation intent analyzer for a technical portfolio Q&A system. Analyze the user's query to determine its intent:

1. **CLARIFY** - More details about the SAME project/topic just discussed
   Examples: "How does it work?", "Tell me more", "Why that approach?", "Explain the architecture"
   Decision: FILTER to same project

2. **EXPAND** - Information about OTHER/DIFFERENT projects or topics
   Examples: "What other projects?", "Tell me about something else", "What else did you work on?"
   Decision: DO NOT FILTER

3. **COMPARE** - Comparing multiple projects/technologies/approaches
   Examples: "Compare your projects", "What's different between X and Y?", "Comparison"
   Decision: DO NOT FILTER

4. **NEW_TOPIC** - Completely new, unrelated question
   Examples: "What are your hobbies?", "Tell me about your education", "Unrelated question"
   Decision: DO NOT FILTER

Recent Conversation Context:
{history_str}

Previous Topic Discussed: {previous_project or "None"}

Current User Query: "{current_query}"

Analyze the query and respond ONLY with valid JSON (no other text):
{{
    "intent": "clarify|expand|compare|new_topic",
    "should_filter": true/false,
    "reasoning": "Brief explanation of why"
}}

Guidelines:
- If intent is "clarify" AND previous_project exists → should_filter: true
- If intent is "expand" OR "compare" OR "new_topic" → should_filter: false
- Be conservative: prefer "expand" over "clarify" if unclear"""

    try:
        completion = client.chat.completions.create(
            model="llama-3.1-8b-instant",  # Fast + cheaper for intent detection
            messages=[
                {
                    "role": "system",
                    "content": "You are a precise intent classifier. Always respond with valid JSON only."
                },
                {"role": "user", "content": prompt}
            ],
            temperature=0.1,  # Low temp for consistent classification
            max_tokens=150,
        )
        
        response_text = completion.choices[0].message.content.strip()
        
        # Extract JSON from response (in case of extra text)
        import re
        json_match = re.search(r'\{.*\}', response_text, re.DOTALL)
        if json_match:
            result = json.loads(json_match.group())
        else:
            result = json.loads(response_text)
        
        logger.info(
            f"🎯 Intent Analysis: {result.get('intent')} | "
            f"Filter: {result.get('should_filter')} | "
            f"Reason: {result.get('reasoning', '')[:60]}..."
        )
        
        return {
            "intent": result.get("intent", "new_topic"),
            "should_filter": bool(result.get("should_filter", False)),
            "target_project": previous_project if result.get("should_filter") else None,
            "reasoning": result.get("reasoning", "")
        }
        
    except Exception as e:
        logger.error(f"❌ Intent analysis failed: {e}")
        # Fallback: don't filter on error (safer default)
        return {
            "intent": "unknown",
            "should_filter": False,
            "target_project": None,
            "reasoning": f"Error in analysis: {str(e)[:50]}"
        }


async def detect_topic_shift_via_embeddings(
    current_query: str,
    previous_query: Optional[str],
    threshold: float = 0.65
) -> bool:
    """
    Use embedding similarity to detect topic shift
    
    Args:
        current_query: Current user question
        previous_query: Previous user question
        threshold: Similarity threshold (0.65 = tuned for topic detection)
    
    Returns:
        True if topic shifted (should NOT filter)
        False if same topic (should filter)
    """
    if not previous_query:
        return True  # New conversation, no filter
    
    try:
        from app.embeddings.nomic import embedding_model
        import numpy as np
        
        # Get embeddings
        current_emb = np.array(embedding_model.embed_query(current_query))
        previous_emb = np.array(embedding_model.embed_query(previous_query))
        
        # Ensure same dimension
        if len(current_emb) != len(previous_emb):
            logger.warning(f"Embedding dimension mismatch: {len(current_emb)} vs {len(previous_emb)}")
            return True  # Default: don't filter on error
        
        # Cosine similarity
        dot_product = np.dot(current_emb, previous_emb)
        norm_curr = np.linalg.norm(current_emb)
        norm_prev = np.linalg.norm(previous_emb)
        
        similarity = dot_product / (norm_curr * norm_prev + 1e-10)
        
        # High similarity = same topic = should filter
        # Low similarity = topic shift = should NOT filter
        should_filter = similarity >= threshold
        
        logger.info(
            f"📊 Query Similarity: {similarity:.3f} (threshold: {threshold}) | "
            f"{'Same topic ✓' if should_filter else 'Topic shift ↗️'}"
        )
        
        return not should_filter  # Return True if topic shifted
        
    except Exception as e:
        logger.error(f"❌ Embedding similarity failed: {e}")
        return True  # Fallback: don't filter


async def smart_context_decision(
    current_query: str,
    conversation_history: List[Dict],
    previous_project: Optional[str] = None,
    use_llm: bool = True,
    use_embeddings: bool = True
) -> Dict[str, any]:
    """
    HYBRID APPROACH: Combine LLM intent + embedding similarity
    
    Most reliable for production use.
    
    Returns:
        {
            "should_filter": bool,
            "target_project": str | None,
            "reasoning": str,
            "llm_intent": str,
            "embedding_shift": bool
        }
    """
    
    # Method 1: LLM-based intent analysis
    llm_result = None
    if use_llm:
        llm_result = await analyze_query_intent(
            current_query, conversation_history, previous_project
        )
    
    # Method 2: Embedding similarity between consecutive user queries
    embedding_shift = False
    if use_embeddings and conversation_history:
        # Find previous user query
        previous_query = None
        for msg in reversed(conversation_history):
            if msg.get("role") == "user":
                previous_query = msg.get("content")
                break
        
        if previous_query:
            embedding_shift = await detect_topic_shift_via_embeddings(
                current_query, previous_query, threshold=0.65
            )
    
    # Combine signals (LLM has priority, embeddings as confirmation)
    if llm_result:
        # "expand" and "compare" intents → always don't filter
        if llm_result["intent"] in ["expand", "compare"]:
            should_filter = False
            reasoning = f"🔀 LLM: {llm_result['intent']} intent detected"
        
        # "clarify" → check embeddings for confirmation
        elif llm_result["intent"] == "clarify":
            if embedding_shift:
                # LLM thinks clarify but embeddings show topic shift = don't filter
                should_filter = False
                reasoning = "🔀 LLM: clarify BUT embeddings: topic shift → NO FILTER"
            else:
                # Both agree: same topic = filter
                should_filter = True
                reasoning = "✓ LLM + Embeddings: Same topic → FILTER"
        
        # "new_topic" → never filter
        else:
            should_filter = False
            reasoning = f"🆕 New topic detected"
    
    else:
        # Fallback to embeddings only (no LLM result)
        should_filter = not embedding_shift
        reasoning = "📊 Embeddings-only: " + ("Same topic → FILTER" if should_filter else "Topic shift → NO FILTER")
    
    logger.info(
        f"🧠 FINAL DECISION: {'🔒 FILTER' if should_filter else '🌐 NO FILTER'} | {reasoning}"
    )
    
    return {
        "should_filter": should_filter,
        "target_project": previous_project if should_filter else None,
        "reasoning": reasoning,
        "llm_intent": llm_result.get("intent") if llm_result else None,
        "embedding_shift": embedding_shift
    }
