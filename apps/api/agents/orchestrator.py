from typing import List, TypedDict, Dict, Annotated, Optional, Literal
import operator
import asyncio
import time
import logging
from langgraph.graph import StateGraph, END

logger = logging.getLogger(__name__)
from pydantic import BaseModel, Field
import os

from agents.question_generator import QuestionGeneratorAgent, Question
from agents.technical_evaluator import TechnicalEvalAgent
from agents.star_analyzer import STARAnalyzerAgent
from agents.follow_up_agent import FollowUpAgent
from services.communication_eval import CommunicationEvalEngine

# --- 1. State Definition ---

class InterviewState(TypedDict):
    # Context
    resume_data: dict
    job_role: str
    
    # Progress Tracking
    covered_topics: List[str]
    asked_questions: List[str]
    current_question_index: int
    current_question: str
    current_answer: str
    current_follow_up_depth: int
    max_follow_up_depth: int
    
    # Logs
    full_transcript: Annotated[List[dict], operator.add]
    
    # Evaluations
    technical_evals: Annotated[List[dict], operator.add]
    behavioral_evals: Annotated[List[dict], operator.add]
    communication_metrics: Annotated[List[dict], operator.add]
    
    # Control
    next_step: Literal["ask", "follow_up", "finalize"]
    is_completed: bool
    final_report: Optional[dict]

# --- 2. Agent Node Implementations ---

class InterviewOrchestrator:
    def __init__(self):
        self.question_gen = QuestionGeneratorAgent()
        self.tech_eval = TechnicalEvalAgent()
        self.star_eval = STARAnalyzerAgent()
        self.comm_eval = CommunicationEvalEngine()
        self.follow_up_agent = FollowUpAgent()

    async def prepare_interview(self, state: InterviewState):
        """Node 1: Initialize the interview session."""
        logger.info(f"Orchestrator: Initializing session for {state['job_role']}")
        return {
            "covered_topics": [],
            "asked_questions": [],
            "current_question_index": 0,
            "max_follow_up_depth": 2,
            "is_completed": False,
            "next_step": "ask"
        }

    async def ask_question(self, state: InterviewState):
        """Node: Generate or serve the next question."""
        # Check if we need to generate a new core question
        # If we have asked 5+ questions and covered all topics, we might finish
        
        gen_res = await self.question_gen.generate_next_question({
            "resume_data": state["resume_data"],
            "job_role": state["job_role"],
            "conversation_history": state["full_transcript"],
            "covered_topics": state["covered_topics"],
            "asked_questions": state["asked_questions"]
        })

        if gen_res.get("next_question") is None:
            return {"is_completed": True, "next_step": "finalize"}
        
        q = gen_res["next_question"]
        return {
            "current_question": q.text,
            "current_follow_up_depth": 0,
            "asked_questions": gen_res["asked_questions"],
            "covered_topics": gen_res["covered_topics"],
            "full_transcript": [{"role": "interviewer", "content": q.text}]
        }

    async def evaluate_response(self, state: InterviewState):
        """Node: Parallel Evaluation and Follow-up determination."""
        if not state.get("current_answer"):
            return {"full_transcript": []}
            
        answer_text = state["current_answer"]
        question_text = state["current_question"]
        
        # 1. Parallel Evaluations
        logger.info("Orchestrator: Starting technical/communication audit...")
        tasks = [
            self.tech_eval.evaluate_answer(question_text, answer_text),
            self.comm_eval.evaluate(answer_text, duration_seconds=30.0)
        ]
        
        # Check if it was a behavioral question to add STAR analysis
        # We don't have the question type directly here but we can infer or pass it
        # For now, let's assume all can have behavioral traits
        tasks.append(self.star_eval.analyze_behavioral_answer(question_text, answer_text))
        
        eval_results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # 2. Dynamic Follow-up Probing
        logger.info("Orchestrator: Checking if follow-up is needed...")
        follow_up_res = await self.follow_up_agent.evaluate_and_generate({
            "resume_data": state["resume_data"],
            "job_role": state["job_role"],
            "current_question": question_text,
            "candidate_answer": answer_text,
            "conversation_history": state["full_transcript"],
            "depth": state["current_follow_up_depth"],
            "max_depth": state["max_follow_up_depth"]
        })
        
        evaluation = follow_up_res["evaluation"]
        next_step = "ask"
        new_question = state["current_question"]
        
        # Safe attribute access for Pydantic/Dict
        is_sufficient = True
        follow_up_q = ""
        if hasattr(evaluation, 'is_sufficient'):
            is_sufficient = evaluation.is_sufficient
            follow_up_q = getattr(evaluation, 'follow_up_needed', "")
        elif isinstance(evaluation, dict):
            is_sufficient = evaluation.get('is_sufficient', True)
            follow_up_q = evaluation.get('follow_up_needed', "")

        if not is_sufficient and state["current_follow_up_depth"] < state["max_follow_up_depth"]:
            next_step = "follow_up"
            new_question = follow_up_q
        
        update = {
            "full_transcript": [{"role": "candidate", "content": answer_text}],
            "technical_evals": [],
            "behavioral_evals": [],
            "communication_metrics": [],
            "next_step": next_step,
            "current_question": new_question,
            "current_follow_up_depth": state["current_follow_up_depth"] + 1
        }
        
        if next_step == "ask":
            update["current_question_index"] = state["current_question_index"] + 1

        # Process eval results
        for i, res in enumerate(eval_results):
            if isinstance(res, Exception) or res is None: continue
            dump = res.model_dump() if hasattr(res, 'model_dump') else res
            if i == 0: update["technical_evals"].append(dump)
            elif i == 1: update["communication_metrics"].append(dump)
            elif i == 2: update["behavioral_evals"].append(dump)
                
        return update

    async def handle_follow_up(self, state: InterviewState):
        """Node: Serve the follow-up question."""
        return {
            "full_transcript": [{"role": "interviewer", "content": state["current_question"]}]
        }

    async def generate_final_report(self, state: InterviewState):
        """Node: Report Aggregator."""
        tech_scores = [e["score"] for e in state["technical_evals"] if "score" in e]
        star_scores = [e["star_score"] for e in state["behavioral_evals"] if "star_score" in e]
        
        all_scores = tech_scores + star_scores
        avg_score = sum(all_scores) / len(all_scores) if all_scores else 0
        
        return {
            "final_report": {
                "overall_score": avg_score,
                "summary": "Interview completed with deep technical probing.",
                "total_questions": len(state["asked_questions"])
            },
            "is_completed": True,
            "next_step": "finalize"
        }

# --- 3. Graph Architecture ---

def create_interview_system():
    orchestrator = InterviewOrchestrator()
    workflow = StateGraph(InterviewState)

    workflow.add_node("prepare", orchestrator.prepare_interview)
    workflow.add_node("ask", orchestrator.ask_question)
    workflow.add_node("evaluate", orchestrator.evaluate_response)
    workflow.add_node("follow_up", orchestrator.handle_follow_up)
    workflow.add_node("finalize", orchestrator.generate_final_report)

    def entry_router(state: InterviewState) -> Literal["prepare", "evaluate", "finalize"]:
        if state.get("is_completed"): return "finalize"
        if not state.get("asked_questions"): return "prepare"
        if state.get("current_answer"): return "evaluate"
        return "finalize"

    workflow.set_conditional_entry_point(
        entry_router,
        {
            "prepare": "prepare",
            "evaluate": "evaluate",
            "finalize": "finalize"
        }
    )

    workflow.add_edge("prepare", "ask")
    workflow.add_edge("ask", END)

    def post_eval_router(state: InterviewState) -> Literal["ask", "follow_up", "finalize"]:
        if state.get("is_completed") or state.get("next_step") == "finalize":
            return "finalize"
        return state.get("next_step", "ask")

    workflow.add_conditional_edges(
        "evaluate",
        post_eval_router,
        {
            "ask": "ask",
            "follow_up": "follow_up",
            "finalize": "finalize"
        }
    )
    
    workflow.add_edge("follow_up", END)
    workflow.add_edge("finalize", END)

    return workflow.compile()

interview_graph = create_interview_system()
