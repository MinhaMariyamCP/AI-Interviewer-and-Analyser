from typing import Literal
from langgraph.graph import StateGraph, END
from .state import InterviewState
from .adaptive_agents import AdaptiveAgents
import logging

logger = logging.getLogger(__name__)

def create_adaptive_interview_system():
    agents = AdaptiveAgents()
    workflow = StateGraph(InterviewState)
    
    workflow.add_node("analyze_resume", agents.analyze_resume)
    workflow.add_node("plan_question", agents.plan_question)
    workflow.add_node("manage_state", agents.manage_state)
    workflow.add_node("evaluate_answer", agents.evaluate_answer)
    workflow.add_node("generate_follow_up", agents.generate_follow_up)
    workflow.add_node("generate_report", agents.generate_report)
    
    def entry_router(state: InterviewState) -> Literal["analyze_resume", "evaluate_answer", "generate_report"]:
        if state.get("is_completed"):
            return "generate_report"
        if not state.get("candidate_profile"):
            return "analyze_resume"
        if state.get("current_answer"):
            return "evaluate_answer"
        return "analyze_resume"

    workflow.set_conditional_entry_point(
        entry_router,
        {
            "analyze_resume": "analyze_resume",
            "evaluate_answer": "evaluate_answer",
            "generate_report": "generate_report"
        }
    )

    workflow.add_edge("analyze_resume", "plan_question")
    workflow.add_edge("plan_question", "manage_state")
    
    def manage_state_router(state: InterviewState) -> Literal["plan_question", "__end__"]:
        if state.get("duplicate_detected"):
            return "plan_question"
        return "__end__"

    workflow.add_conditional_edges(
        "manage_state",
        manage_state_router,
        {"plan_question": "plan_question", "__end__": END}
    )
    
    def post_plan_router(state: InterviewState) -> Literal["generate_report", "__end__"]:
        if state.get("next_step") == "report":
            return "generate_report"
        return "__end__"
        
    def post_eval_router(state: InterviewState) -> Literal["generate_follow_up", "generate_report"]:
        if state.get("next_step") == "report":
            return "generate_report"
        return "generate_follow_up"

    workflow.add_conditional_edges(
        "evaluate_answer",
        post_eval_router,
        {
            "generate_follow_up": "generate_follow_up",
            "generate_report": "generate_report"
        }
    )
    
    def post_follow_up_router(state: InterviewState) -> Literal["manage_state", "plan_question", "__end__"]:
        if state.get("next_step") == "manage_state":
            return "manage_state"
        if state.get("next_step") == "plan":
            return "plan_question"
        return "__end__"
        
    workflow.add_conditional_edges(
        "generate_follow_up", 
        post_follow_up_router, 
        {
            "manage_state": "manage_state", 
            "plan_question": "plan_question", 
            "__end__": END
        }
    )
    
    workflow.add_edge("generate_report", END)

    return workflow.compile()

adaptive_interview_graph = create_adaptive_interview_system()
