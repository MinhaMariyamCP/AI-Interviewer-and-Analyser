from typing import List, TypedDict, Dict, Annotated, Optional
import operator
from pydantic import BaseModel, Field

class TurnEval(BaseModel):
    technical_score: float = Field(description="0-100 score for technical accuracy and depth")
    communication_score: float = Field(description="0-100 score for clarity and conciseness")
    confidence_score: float = Field(description="0-100 score for candidate confidence")
    knowledge_depth: float = Field(description="0-100 score for depth of understanding, tradeoffs, and system design thinking")
    weak_areas: List[str] = Field(description="Specific technical or soft skill areas where the candidate struggled")
    strong_areas: List[str] = Field(description="Specific areas where the candidate demonstrated expertise")
    reasoning: str = Field(description="Detailed explanation of the evaluation considering technical accuracy and examples used")

class GeneratedQuestion(BaseModel):
    text: str = Field(description="The question text")
    topic: str = Field(description="The topic covered")
    reasoning: str = Field(description="Why this question was generated based on specific resume points or previous answers")

class CandidateProfile(BaseModel):
    core_skills: List[str]
    technologies: List[str]
    projects: List[Dict[str, str]]
    experience: List[Dict[str, str]]
    achievements: List[str]
    education: List[Dict[str, str]]
    summary: str

class InterviewState(TypedDict):
    # Initial Context
    resume_data: dict
    job_role: str
    
    # Processed Context
    candidate_profile: Optional[dict]
    
    # Progress State
    current_topic: Optional[str]
    covered_topics: List[str]
    remaining_topics: List[str] # ["Resume Projects", "Technical Skills", "System Design", "Problem Solving", "Behavioral Questions", "Leadership", "Communication"]
    asked_questions: List[str]
    attempted_questions: List[str] # Questions that were rejected as duplicates
    answer_history: Annotated[List[dict], operator.add]
    
    # Current Turn
    current_question: str
    current_answer: str
    current_turn_eval: Optional[dict]
    turn_count: int
    
    # Duplicate Detection
    duplicate_detected: bool
    
    # Aggregated
    scores: dict
    
    # Flow Control
    next_step: str
    is_completed: bool
    final_report: Optional[dict]
