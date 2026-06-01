from typing import List, Dict, Optional
from pydantic import BaseModel, Field
from langchain_openai import ChatOpenAI
from langchain_core.messages import HumanMessage, SystemMessage
import os
import logging

logger = logging.getLogger(__name__)

# --- 1. Output Schema ---

class TechnicalAssessment(BaseModel):
    score: float = Field(description="Overall technical score from 0-100")
    correctness_score: float = Field(description="Accuracy of the technical facts provided (0-100)")
    depth_score: float = Field(description="Depth of understanding and architectural awareness (0-100)")
    examples_score: float = Field(description="Quality and relevance of examples provided (0-100)")
    tradeoffs_score: float = Field(description="Identification of technical tradeoffs and alternatives (0-100)")
    strengths: List[str] = Field(description="Specific technical strengths demonstrated in the answer")
    weaknesses: List[str] = Field(description="Technical gaps, inaccuracies, or areas lacking detail")
    tradeoffs_mentioned: List[str] = Field(description="List of technical tradeoffs or alternatives identified by the candidate")
    ai_rationale: str = Field(description="Detailed explanation of why this score was given")

# --- 2. Evaluation Service ---

class TechnicalEvalAgent:
    def __init__(self, api_key: str = None):
        self.api_key = api_key or os.getenv("OPENAI_API_KEY")
        self.llm = ChatOpenAI(
            model="gpt-4o-mini",
            openai_api_key=self.api_key,
            temperature=0
        )
        self.structured_llm = self.llm.with_structured_output(TechnicalAssessment)

    async def evaluate_answer(self, question: str, answer: str, context: Optional[str] = None) -> TechnicalAssessment:
        """
        Performs a deep technical audit of a candidate's answer.
        """
        prompt = f"""
        Evaluate the candidate's answer for technical correctness, depth, tradeoffs, and examples.
        Question: {question}
        Answer: {answer}
        """
        
        try:
            result = await self.structured_llm.ainvoke([
                SystemMessage(content="You are an expert technical evaluator."),
                HumanMessage(content=prompt)
            ])
            return result
        except Exception as e:
            logger.error(f"Technical Eval failed: {e}. Using heuristic fallback.")
            return self._heuristic_evaluation(answer)

    def _heuristic_evaluation(self, answer: str) -> TechnicalAssessment:
        # Simple heuristics based on length and keywords
        length = len(answer.split())
        score = min(40 + (length / 2), 95)
        
        return TechnicalAssessment(
            score=score,
            correctness_score=score,
            depth_score=score - 5,
            examples_score=score - 10 if length < 50 else score,
            tradeoffs_score=score - 15 if length < 70 else score,
            strengths=["Answer provided", "Detailed response" if length > 50 else "Concise response"],
            weaknesses=["Lacks deep architectural analysis" if length < 100 else "Could be more structured"],
            tradeoffs_mentioned=[],
            ai_rationale="Heuristic fallback applied due to API unavailability."
        )

# ... router remains the same ...
from fastapi import APIRouter, HTTPException

router = APIRouter(prefix="/api/v1/eval/technical", tags=["evaluation"])
agent = TechnicalEvalAgent()

@router.post("/evaluate", response_model=TechnicalAssessment)
async def evaluate_technical_answer(question: str, answer: str, context: Optional[str] = None):
    try:
        return await agent.evaluate_answer(question, answer, context)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
