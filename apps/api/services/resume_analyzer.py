from typing import List
from pydantic import BaseModel, Field
from langchain_openai import ChatOpenAI
from langchain_core.messages import HumanMessage, SystemMessage
import os
import json
import logging
import re

logger = logging.getLogger(__name__)

# --- Output Schema ---

class JobPreference(BaseModel):
    role: str = Field(description="Recommended job title (e.g., Senior AI Engineer)")
    confidence: float = Field(description="Confidence score from 0-100")
    reasoning: str = Field(description="Brief explanation of why this role matches the resume")

class ResumeAnalysis(BaseModel):
    skills: List[str] = Field(description="Core hard skills and soft skills extracted from the resume")
    technologies: List[str] = Field(description="Specific tools, frameworks, and programming languages")
    experience_level: str = Field(description="Calculated seniority: Junior, Mid-level, Senior, or Lead")
    strengths: List[str] = Field(description="Top 3-5 unique value propositions")
    suggested_roles: List[JobPreference] = Field(description="At least 10 personalized job role recommendations")

# Rebuild models for Pydantic v2 compatibility
ResumeAnalysis.model_rebuild()

# --- Service Implementation ---

class ResumeAnalyzerService:
    def __init__(self, api_key: str = None):
        self.api_key = api_key or os.getenv("OPENAI_API_KEY")
        self.llm = ChatOpenAI(
            model="gpt-4o-mini",
            openai_api_key=self.api_key,
            temperature=0
        )
        self.structured_llm = self.llm.with_structured_output(ResumeAnalysis)

    async def analyze(self, resume_json: dict) -> ResumeAnalysis:
        """
        Perform deep semantic analysis on resume data to generate job preferences.
        """
        prompt = f"""
        You are an expert technical recruiter. Analyze the following structured resume data.
        Your goal is to:
        1. Recommend AT LEAST 10 specific job roles that this candidate is qualified for.
        
        Resume Data:
        {json.dumps(resume_json, indent=2)}
        """

        try:
            logger.info("Calling LLM for Resume Analysis")
            result = await self.structured_llm.ainvoke([
                SystemMessage(content="You are a highly accurate AI career recruiter. Generate personalized job matches."),
                HumanMessage(content=prompt)
            ])
            return result
            
        except Exception as e:
            logger.error(f"LLM Analysis failed: {str(e)}. Using rule-based fallback.")
            return self._rule_based_analysis(resume_json)

    def _rule_based_analysis(self, resume_json: dict) -> ResumeAnalysis:
        """
        Fallback logic to ensure the UI is populated even if AI APIs are down/unauthorized.
        """
        skills = resume_json.get("skills") or []
        skills_str = " ".join(skills).lower()
        
        # Simple heuristic matches
        potential_roles = []
        
        if any(kw in skills_str for kw in ["python", "java", "backend", "fastapi", "django", "node"]):
            potential_roles.append(JobPreference(
                role="Backend Software Engineer", 
                confidence=85.0, 
                reasoning="Strong match based on backend development skills found in resume."
            ))
        
        if any(kw in skills_str for kw in ["react", "frontend", "typescript", "css", "vue"]):
            potential_roles.append(JobPreference(
                role="Frontend Developer", 
                confidence=80.0, 
                reasoning="Demonstrated proficiency in modern frontend frameworks."
            ))

        if any(kw in skills_str for kw in ["machine learning", "ml", "ai", "pytorch", "tensorflow"]):
            potential_roles.append(JobPreference(
                role="AI/ML Engineer", 
                confidence=90.0, 
                reasoning="Expertise in artificial intelligence and machine learning frameworks."
            ))

        if any(kw in skills_str for kw in ["docker", "kubernetes", "aws", "cloud", "devops"]):
            potential_roles.append(JobPreference(
                role="DevOps Engineer", 
                confidence=75.0, 
                reasoning="Experience with cloud infrastructure and containerization."
            ))

        if any(kw in skills_str for kw in ["data", "sql", "pandas", "analysis"]):
            potential_roles.append(JobPreference(
                role="Data Scientist", 
                confidence=70.0, 
                reasoning="Strong analytical background and data manipulation skills."
            ))
            
        # Ensure we always have a broad interview catalogue for the UI requirement.
        generic_roles = [
            ("Fullstack Developer", "Versatile skill set across the entire web stack."),
            ("Junior Software Engineer", "Strong foundational knowledge and willingness to learn."),
            ("Technical Product Manager", "Combination of technical understanding and project experience."),
            ("System Architect", "High-level understanding of software components and design patterns."),
            ("QA Automation Engineer", "Good fit for candidates who can reason through reliability, testing, and edge cases."),
            ("Cloud Engineer", "Relevant for candidates preparing for infrastructure, deployment, and cloud service interviews."),
            ("Data Analyst", "Useful for analytical interviews involving SQL, reporting, and business metrics."),
            ("Business Analyst", "Matches candidates who translate requirements into structured solutions."),
            ("Cybersecurity Analyst", "Covers security fundamentals, risk awareness, and secure system design."),
            ("Mobile App Developer", "Suitable for app-focused interviews across Android, iOS, and cross-platform stacks."),
            ("UI/UX Engineer", "Targets frontend implementation, usability thinking, and design-system collaboration."),
            ("AI Product Engineer", "Blends product judgement with AI-assisted application development."),
            ("Support Engineer", "Strong option for troubleshooting, communication, and customer-facing technical roles."),
            ("Operations Manager", "Useful for non-technical resumes with leadership, process, and execution experience."),
            ("Sales Engineer", "Fits candidates combining technical understanding with client-facing communication.")
        ]
        
        while len(potential_roles) < 12 and generic_roles:
            role, reason = generic_roles.pop(0)
            potential_roles.append(JobPreference(role=role, confidence=60.0, reasoning=reason))

        return ResumeAnalysis(
            skills=skills,
            technologies=skills,
            experience_level="Mid-level",
            strengths=["Technically proficient", "Well-rounded candidate"],
            suggested_roles=potential_roles
        )
