from typing import List, Dict, Optional
from pydantic import BaseModel, Field
from langchain_openai import ChatOpenAI
from langchain_core.messages import HumanMessage, SystemMessage
import os
import logging

logger = logging.getLogger(__name__)

# --- 1. Output Schema ---

class STARComponent(BaseModel):
    present: bool = Field(description="Is this component present in the answer?")
    content: Optional[str] = Field(description="The specific text segment corresponding to this component")
    score: float = Field(description="Score for this specific component (0-100)")
    feedback: str = Field(description="Brief feedback on how this component was handled")

class STARAnalysis(BaseModel):
    star_score: float = Field(description="Overall STAR method adherence score (0-100)")
    situation: STARComponent
    task: STARComponent
    action: STARComponent
    result: STARComponent
    missing_sections: List[str] = Field(description="List of STAR components that were absent or very weak")
    general_feedback: List[str] = Field(description="Overall advice to improve behavioral storytelling")

# --- 2. Analyzer Service ---

class STARAnalyzerAgent:
    def __init__(self, api_key: str = None):
        self.api_key = api_key or os.getenv("OPENAI_API_KEY")
        self.llm = ChatOpenAI(
            model="gpt-4o-mini",
            openai_api_key=self.api_key,
            temperature=0
        )
        self.structured_llm = self.llm.with_structured_output(STARAnalysis)

    async def analyze_behavioral_answer(self, question: str, answer: str) -> STARAnalysis:
        prompt = f"""
        Analyze the following behavioral interview answer using the STAR method.
        Question: {question}
        Answer: {answer}
        """
        
        try:
            result = await self.structured_llm.ainvoke([
                SystemMessage(content="You are a behavioral interview assessor."),
                HumanMessage(content=prompt)
            ])
            return result
        except Exception as e:
            logger.error(f"STAR analysis failed: {e}. Using heuristic fallback.")
            return self._heuristic_analysis(answer)

    def _heuristic_analysis(self, answer: str) -> STARAnalysis:
        # Simple length-based heuristics
        length = len(answer.split())
        base_score = min(30 + (length / 3), 90)
        
        comp = lambda name: STARComponent(
            present=length > 30,
            content=None,
            score=base_score,
            feedback=f"Found indicators of {name}." if length > 30 else f"{name} section seems brief."
        )

        return STARAnalysis(
            star_score=base_score,
            situation=comp("Situation"),
            task=comp("Task"),
            action=comp("Action"),
            result=comp("Result"),
            missing_sections=[] if length > 50 else ["Result", "Task"],
            general_feedback=["Try to provide more measurable outcomes.", "Ensure you clearly define your specific actions."]
        )

# ... router remains the same ...
from fastapi import APIRouter, HTTPException

router = APIRouter(prefix="/api/v1/eval/behavioral", tags=["evaluation"])
agent = STARAnalyzerAgent()

@router.post("/star-analysis", response_model=STARAnalysis)
async def evaluate_star_answer(question: str, answer: str):
    try:
        return await agent.analyze_behavioral_answer(question, answer)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
