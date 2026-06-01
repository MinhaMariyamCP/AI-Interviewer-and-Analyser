import re
from typing import List, Dict
from pydantic import BaseModel, Field
from langchain_openai import ChatOpenAI
from langchain_core.messages import HumanMessage, SystemMessage
import os
import logging

logger = logging.getLogger(__name__)

# --- 1. Data Models ---

class CommunicationMetrics(BaseModel):
    communication_score: float = Field(description="Overall score from 0-100")
    filler_word_count: int = Field(description="Number of filler words detected")
    wpm: float = Field(description="Words per minute")
    clarity_score: float = Field(description="Score for structural clarity 0-100")
    confidence_indicators: List[str] = Field(description="Specific indicators of confidence or lack thereof")
    strengths: List[str] = Field(description="Key communication strengths")
    improvements: List[str] = Field(description="Specific areas for improvement")

# --- 2. Evaluation Engine ---

class CommunicationEvalEngine:
    FILLER_WORDS = [
        r'\buh\b', r'\bum\b', r'\blike\b', r'\byou know\b', 
        r'\bactually\b', r'\bbasically\b', r'\bi mean\b'
    ]

    def __init__(self, api_key: str = None):
        self.api_key = api_key or os.getenv("OPENAI_API_KEY")
        self.llm = ChatOpenAI(
            model="gpt-4o-mini",
            openai_api_key=self.api_key,
            temperature=0
        )
        self.structured_llm = self.llm.with_structured_output(CommunicationMetrics)

    def _calculate_base_metrics(self, transcript: str, duration_seconds: float) -> Dict:
        words = transcript.split()
        word_count = len(words)
        wpm = (word_count / duration_seconds) * 60 if duration_seconds > 0 else 0
        filler_count = 0
        for pattern in self.FILLER_WORDS:
            filler_count += len(re.findall(pattern, transcript, re.IGNORECASE))
        return {"wpm": round(wpm, 2), "filler_count": filler_count, "word_count": word_count}

    async def evaluate(self, transcript: str, duration_seconds: float) -> CommunicationMetrics:
        base_metrics = self._calculate_base_metrics(transcript, duration_seconds)
        prompt = f"""
        Analyze communication style:
        Transcript: "{transcript}"
        Quantitative: {base_metrics}
        """
        try:
            result = await self.structured_llm.ainvoke([
                SystemMessage(content="You are a communication coach."),
                HumanMessage(content=prompt)
            ])
            result.wpm = base_metrics['wpm']
            result.filler_word_count = base_metrics['filler_count']
            return result
        except Exception as e:
            logger.error(f"Comm eval failed: {e}. Using fallback.")
            return self._heuristic_comm_eval(base_metrics)

    def _heuristic_comm_eval(self, metrics: dict) -> CommunicationMetrics:
        score = 80 - (metrics['filler_count'] * 2)
        if metrics['wpm'] > 180 or metrics['wpm'] < 80:
            score -= 10
            
        return CommunicationMetrics(
            communication_score=max(0, score),
            filler_word_count=metrics['filler_count'],
            wpm=metrics['wpm'],
            clarity_score=score,
            confidence_indicators=["Stable pace" if 100 < metrics['wpm'] < 160 else "Pace could be steadier"],
            strengths=["Answer provided clearly"],
            improvements=["Try to reduce filler words" if metrics['filler_count'] > 3 else "Keep it up"]
        )

# ... router remains the same ...
from fastapi import APIRouter, HTTPException

router = APIRouter(prefix="/api/v1/eval", tags=["evaluation"])
engine = CommunicationEvalEngine()

@router.post("/communication", response_model=CommunicationMetrics)
async def evaluate_communication(transcript: str, duration_seconds: float):
    try:
        return await engine.evaluate(transcript, duration_seconds)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
