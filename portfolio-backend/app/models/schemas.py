from pydantic import BaseModel, Field
from typing import Optional, List
from datetime import datetime

# Request/Response Models

class ChatRequest(BaseModel):
    message: str
    mode: Optional[str] = None
    session_id: Optional[str] = None

class JudgeScore(BaseModel):
    grounding_score: int
    consistency_score: int
    depth_score: int
    revision_required: bool
    feedback: List[str]
    citations_used: List[str]

class ExtendedJudgeScore(BaseModel):
    grounding_score: int = 0
    consistency_score: int = 0
    depth_score: int = 0
    specificity_score: int = 0
    average_score: float = 0.0
    revision_required: bool = True
    reject: bool = False
    feedback: List[str] = Field(default_factory=list)
    strengths: List[str] = Field(default_factory=list)
    citations_used: List[str] = Field(default_factory=list)

    class Config:
        arbitrary_types_allowed = True  # allows helper methods

    # methods preserved
    def should_revise(self) -> bool:
        return self.revision_required and not self.reject

    def should_reject(self) -> bool:
        return self.reject or self.average_score < 4

class ChatResponse(BaseModel):
    response: str
    mode: str
    judge_score: Optional[ExtendedJudgeScore] = None
    sources: List[str] = []

class IngestRequest(BaseModel):
    title: str
    source: str
    project_type: str = "project"
    content: str

class IngestResponse(BaseModel):
    success: bool
    document_id: str
    chunks_created: int

class HealthResponse(BaseModel):
    status: str
    environment: str
    timestamp: datetime

# Database Models

class ModeDetectionResult(BaseModel):
    mode: str
    confidence: float
    reasoning: str

class RetrievedChunk(BaseModel):
    id: str
    content: str
    source: Optional[str] = "unknown"
    embedding: Optional[List[float]] = Field(default_factory=list)
    similarity: Optional[float] = 0.0
    
    class Config:
        # Allow creating from dict
        from_attributes = True
