from typing import List, TypedDict, Dict, Annotated, Optional
import operator
from langgraph.graph import StateGraph, END
from langchain_openai import ChatOpenAI
from langchain_core.messages import HumanMessage, SystemMessage
from pydantic import BaseModel, Field
import os
import json
import logging

logger = logging.getLogger(__name__)

# --- 1. State Schema & Pydantic Models ---

class Question(BaseModel):
    text: str = Field(description="The actual question text")
    type: str = Field(description="technical, behavioral, or project_based")
    topic: str = Field(description="The category of the question: Resume Projects, Core Skills, Problem Solving, System Design, Behavioral")
    reasoning: str = Field(description="Detailed logic for why this question was selected based on resume and role")

class QuestionBank(BaseModel):
    questions: List[Question] = Field(description="List of personalized interview questions")

class AgentState(TypedDict):
    resume_data: dict
    job_role: str
    conversation_history: List[dict]
    covered_topics: List[str]
    asked_questions: List[str]
    next_question: Optional[Question]

# --- 2. Agent Logic & Nodes ---

class QuestionGeneratorAgent:
    def __init__(self, api_key: str = None):
        self.api_key = api_key or os.getenv("OPENAI_API_KEY")
        self.llm = ChatOpenAI(
            model="gpt-4o-mini",
            openai_api_key=self.api_key,
            temperature=0.7 # Slight randomness for variety
        )
        self.structured_llm = self.llm.with_structured_output(Question)

    async def generate_next_question(self, state: AgentState) -> Dict:
        """
        Dynamically generates the NEXT core question based on what has been asked 
        and what is in the resume.
        """
        resume = state.get("resume_data", {})
        role = state.get("job_role", "Software Engineer")
        history = state.get("conversation_history", [])
        covered = state.get("covered_topics", [])
        asked = state.get("asked_questions", [])
        
        logger.info(f"QuestionGen: Generating next question for role: {role}")
        
        prompt = f"""
        You are an elite technical recruiter for a top-tier tech company. 
        Your goal is to conduct a highly personalized, deep-dive interview for a {role} position.

        CANDIDATE RESUME:
        {json.dumps(resume, indent=2)}

        INTERVIEW SO FAR:
        {json.dumps(history[-4:], indent=2)} # Last 2 turns for context

        TOPICS ALREADY COVERED: {covered}
        QUESTIONS ALREADY ASKED: {asked}

        STRATEGIC REQUIREMENTS:
        1. GROUNDING: Every question must be directly linked to a specific skill, project, or experience found in the resume.
        2. ROLE ALIGNMENT: Adapt the technical depth to the level of a {role}.
        3. VARIETY: Choose a topic NOT in the 'covered' list. Topics to cover: Resume Projects, Core Skills, Problem Solving, System Design, Behavioral.
        4. NO REPETITION: Do not ask the same question or a semantically similar one to anything in 'asked'.
        5. RECRUITER TONE: Sound professional, curious, and challenging.

        Generate the single best next core question to ask.
        """
        
        try:
            # First, check if we have covered everything
            all_topics = ["Resume Projects", "Core Skills", "Problem Solving", "System Design", "Behavioral"]
            remaining = [t for t in all_topics if t not in covered]
            
            if not remaining and len(asked) >= 5:
                logger.info("QuestionGen: All topics covered. Signaling completion.")
                return {"next_question": None}

            response = await self.structured_llm.ainvoke([
                SystemMessage(content="You are a senior technical interviewer. You ask sharp, resume-grounded questions."),
                HumanMessage(content=prompt)
            ])
            
            logger.info(f"QuestionGen: Selected Topic: {response.topic}")
            logger.info(f"QuestionGen: Reasoning: {response.reasoning}")
            
            return {
                "next_question": response,
                "asked_questions": asked + [response.text],
                "covered_topics": list(set(covered + [response.topic]))
            }
        except Exception as e:
            logger.error(f"Question Generation failed: {e}. Using heuristic fallback.")
            fallback = self._heuristic_fallback(resume, role, asked)
            return {
                "next_question": fallback,
                "asked_questions": asked + [fallback.text],
                "covered_topics": list(set(covered + [fallback.topic]))
            }

    def _heuristic_fallback(self, resume: dict, role: str, asked: List[str]) -> Question:
        skills = resume.get("skills", [])
        if not skills:
            skills = ["Software Engineering", "System Design", "Problem Solving"]
            
        # Create a pool of potential questions
        pool = [
            Question(
                text=f"Looking at your experience with {skills[0]}, what was the most complex technical tradeoff you had to make recently?",
                type="technical", topic="Core Skills", reasoning="Fallback: Skill deep-dive."
            ),
            Question(
                text=f"Can you walk me through the architecture of your most significant project involving {skills[1] if len(skills) > 1 else skills[0]}?",
                type="project_based", topic="Resume Projects", reasoning="Fallback: Project walkthrough."
            ),
            Question(
                text="Tell me about a time you had to deliver a critical feature under a very tight deadline. How did you prioritize?",
                type="behavioral", topic="Behavioral", reasoning="Fallback: Priority assessment."
            ),
            Question(
                text=f"If you were to redesign a system that uses {skills[0]} to handle 10x the current load, what changes would you make?",
                type="technical", topic="System Design", reasoning="Fallback: Scalability check."
            ),
            Question(
                text="Describe a technical disagreement you had with a senior peer. How did you resolve it?",
                type="behavioral", topic="Behavioral", reasoning="Fallback: Conflict resolution."
            )
        ]
        
        # Filter out already asked questions
        available = [q for q in pool if q.text not in asked]
        
        if not available:
            # Absolute fallback if everything is asked
            return Question(
                text=f"How do you ensure code quality and maintainability when working with {skills[0]}?",
                type="technical", topic="Core Skills", reasoning="Final fallback."
            )
            
        return available[0]
