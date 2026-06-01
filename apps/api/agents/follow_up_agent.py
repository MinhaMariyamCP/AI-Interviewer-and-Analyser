from typing import List, TypedDict, Dict, Optional, Literal
from langgraph.graph import StateGraph, END
from langchain_openai import ChatOpenAI
from langchain_core.messages import HumanMessage, SystemMessage, BaseMessage
from pydantic import BaseModel, Field
import os
import json
import logging

logger = logging.getLogger(__name__)

# --- 1. State & Schema Definitions ---

class EvaluationResult(BaseModel):
    is_sufficient: bool = Field(description="True if the answer is comprehensive and doesn't need follow-up")
    follow_up_needed: str = Field(description="The actual follow-up question, or empty if is_sufficient is True")
    reasoning: str = Field(description="Why this follow-up is relevant to the candidate's specific answer and resume")

class FollowUpState(TypedDict):
    resume_data: dict
    job_role: str
    current_question: str
    candidate_answer: str
    conversation_history: List[dict]
    depth: int 
    max_depth: int
    evaluation: Optional[EvaluationResult]

# Rebuild for Pydantic v2
EvaluationResult.model_rebuild()

# --- 2. Node Implementations ---

class FollowUpAgent:
    def __init__(self, api_key: str = None):
        self.api_key = api_key or os.getenv("OPENAI_API_KEY")
        self.llm = ChatOpenAI(
            model="gpt-4o-mini",
            openai_api_key=self.api_key,
            temperature=0.3
        )
        self.structured_llm = self.llm.with_structured_output(EvaluationResult)

    async def evaluate_and_generate(self, state: FollowUpState) -> Dict:
        """Analyze the candidate's answer and generate a targeted follow-up if needed."""
        resume = state.get("resume_data", {})
        role = state.get("job_role", "Software Engineer")
        history = state.get("conversation_history", [])
        
        prompt = f"""
        You are a senior hiring manager conducting a technical interview for a {role}.
        Analyze the candidate's answer to the current question and decide if a follow-up is necessary 
        to test depth, verify claims, or clarify vague statements.

        RESUME CONTEXT:
        {json.dumps(resume, indent=2)}

        PREVIOUS CONVERSATION:
        {json.dumps(history[-2:], indent=2)}

        CURRENT QUESTION: {state['current_question']}
        CANDIDATE ANSWER: {state['candidate_answer']}

        REQUIREMENTS:
        1. SPECIFICITY: If you ask a follow-up, it MUST be directly derived from their answer. 
           Example: If they mentioned using Redis for caching, ask about their eviction policy or cluster setup.
        2. DEPTH: Focus on "Why" and "How" rather than "What".
        3. RESUME GROUNDING: Link their answer back to their reported experience in the resume.
        4. SUFFICIENCY: If the answer is 100% complete, architecturally sound, and demonstrates clear seniority, mark as sufficient.
        """
        
        try:
            result = await self.structured_llm.ainvoke([
                SystemMessage(content="You are a probing technical interviewer who values depth and specific examples."),
                HumanMessage(content=prompt)
            ])
            
            if result.follow_up_needed:
                logger.info(f"FollowUp: Probing deeper. Reasoning: {result.reasoning}")
            
            return {
                "evaluation": result,
                "depth": state["depth"] + 1
            }
        except Exception as e:
            logger.error(f"Follow-up Generation failed: {e}. Marking as sufficient.")
            return {
                "evaluation": EvaluationResult(is_sufficient=True, follow_up_needed="", reasoning="Error in LLM call."),
                "depth": state["depth"] + 1
            }
