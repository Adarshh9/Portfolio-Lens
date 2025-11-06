from pydantic_settings import BaseSettings
from typing import List
import os

class Settings(BaseSettings):
    # Environment
    ENVIRONMENT: str = os.getenv("ENVIRONMENT", "development")
    DEBUG: bool = os.getenv("DEBUG", "true").lower() == "true"
    
    # Supabase
    SUPABASE_URL: str = os.getenv("SUPABASE_URL", "")
    SUPABASE_KEY: str = os.getenv("SUPABASE_KEY", "")
    SUPABASE_SERVICE_ROLE_KEY: str = os.getenv("SUPABASE_SERVICE_ROLE_KEY", "")
    
    # Groq
    GROQ_API_KEY: str = os.getenv("GROQ_API_KEY", "")
    
    # Embeddings
    EMBEDDING_MODEL: str = os.getenv("EMBEDDING_MODEL", "nomic-embed-text-v1.5")
    EMBEDDING_DIMENSION: int = int(os.getenv("EMBEDDING_DIMENSION", "768"))
    
    # CORS
    CORS_ORIGINS: List[str] = ["http://localhost:3000", "http://localhost:3001"]
    
    class Config:
        env_file = ".env"
        case_sensitive = True

settings = Settings()

# Constants
MODE_KEYWORDS = {
    "recruiter": [
        "hire", "hiring", "role", "position", "job", "team", "company",
        "experience", "skills", "resume", "background", "qualifications",
        "tell me about", "what do you", "summarize", "overview"
    ],
    "engineer": [
        "architecture", "design", "implementation", "why did you", "tradeoff",
        "alternative", "performance", "scalability", "optimization",
        "technical", "how does", "explain", "deep dive", "challenge"
    ],
    "ama": [
        "what if", "would you", "opinion", "think", "advice",
        "improve", "change", "next version", "future", "learn"
    ]
}

SYSTEM_PROMPTS = {
    "recruiter": """You are a professional portfolio assistant in Recruiter Mode.
Your role:
- Provide clear, business-focused summaries
- Highlight impact and outcomes
- Emphasize skills and technologies
- Keep responses concise and polished
- Avoid deep technical jargon
- Focus on value delivered

Always cite sources from the portfolio using [source: project_name].""",

    "engineer": """You are a technical portfolio assistant in Engineer Mode.
Your role:
- Provide detailed architectural explanations
- Discuss tradeoffs and design decisions
- Compare alternatives that were considered
- Explain technical reasoning deeply
- Reference specific implementations
- Acknowledge limitations and future improvements

Always cite specific portfolio documentation using [source: project_name].""",

    "ama": """You are a conversational portfolio assistant in AMA Mode.
Your role:
- Be friendly and exploratory
- Encourage curiosity
- Share insights and lessons learned
- Discuss hypotheticals and improvements
- Be authentic and thoughtful
- Keep tone warm but professional

Always reference relevant portfolio content using [source: project_name]."""
}

JUDGE_RUBRIC = """You are a strict Judge Agent evaluating portfolio responses.

Score each dimension 0-5:

**Grounding (0-5):**
- 5: Every claim has explicit portfolio citations
- 3: Most claims cited, minor gaps
- 0: Fabricated or unsupported claims

**Consistency (0-5):**
- 5: Aligns perfectly with documented decisions across projects
- 3: Mostly consistent, minor contradictions
- 0: Major contradictions with portfolio

**Depth (0-5):**
- 5: Architectural reasoning with tradeoffs
- 3: Solid explanation, missing some nuance
- 0: Surface-level or generic

Return ONLY valid JSON:
{
  "grounding_score": number,
  "consistency_score": number,
  "depth_score": number,
  "revision_required": boolean,
  "feedback": ["specific issue 1", "specific issue 2"],
  "citations_used": ["source1", "source2"]
}"""

CHUNK_SIZE = 600
CHUNK_OVERLAP = 100
