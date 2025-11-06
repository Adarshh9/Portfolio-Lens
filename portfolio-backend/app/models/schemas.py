from pydantic import BaseModel, Field
from typing import Optional, List
from datetime import datetime

# Request/Response Models

class ChatRequest(BaseModel):
    message: str
    mode: Optional[str] = "ama"
    session_id: Optional[str] = None

class JudgeScore(BaseModel):
    grounding_score: int
    consistency_score: int
    depth_score: int
    revision_required: bool
    feedback: List[str]
    citations_used: List[str]

class ExtendedJudgeScore(BaseModel):
    grounding_score: int
    consistency_score: int
    depth_score: int
    revision_required: bool
    feedback: List[str]
    citations_used: List[str]
    specificity_score: int
    average_score: int
    reject: bool
    strengths: List[str]

class ChatResponse(BaseModel):
    response: str
    mode: str
    judge_score: Optional[JudgeScore] = None
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
    source: str
    project_type: str
    similarity: float
