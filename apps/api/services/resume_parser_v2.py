from typing import List, Optional
from pydantic import BaseModel, Field
from langchain_openai import ChatOpenAI
from langchain_core.messages import HumanMessage, SystemMessage
import os
import fitz  # PyMuPDF
from docx import Document
import io
import json
import logging
import re

logger = logging.getLogger(__name__)

# --- 1. Structured Data Model ---

class ResumeData(BaseModel):
    skills: List[str] = Field(default_factory=list, description="A comprehensive list of skills and technologies")
    years_of_experience: Optional[str] = Field(default="Not specified", description="Calculated total years of experience")
    education_level: Optional[str] = Field(default="Not specified", description="Highest level of education obtained")
    certifications: List[str] = Field(default_factory=list, description="List of professional certifications")
    past_job_titles: List[str] = Field(default_factory=list, description="List of past job roles or titles held")

# Rebuild models for Pydantic v2 compatibility
ResumeData.model_rebuild()

# --- 2. Parser Service ---

class ResumeParserService:
    def __init__(self, api_key: str = None):
        openai_key = api_key or os.getenv("OPENAI_API_KEY")
        
        openai_is_valid = openai_key and openai_key.startswith("sk-") and len(openai_key) > 20
        
        if openai_is_valid:
            logger.info("Using OpenAI GPT-4o-Mini for ResumeParserService")
            self.llm = ChatOpenAI(
                model="gpt-4o-mini",
                openai_api_key=openai_key,
                temperature=0
            )
        else:
            logger.warning("No valid OpenAI API key found. Defaulting to OpenAI GPT-4o-Mini constructor (may fail).")
            self.llm = ChatOpenAI(
                model="gpt-4o-mini",
                openai_api_key=openai_key or "dummy-key",
                temperature=0
            )
        self.structured_llm = self.llm.with_structured_output(ResumeData)

    @staticmethod
    def extract_text_from_pdf(file_bytes: bytes) -> str:
        text = ""
        try:
            with fitz.open(stream=file_bytes, filetype="pdf") as doc:
                for page in doc:
                    text += page.get_text()
            return text
        except Exception as e:
            logger.error(f"PyMuPDF failed: {e}")
            return ""

    @staticmethod
    def extract_text_from_docx(file_bytes: bytes) -> str:
        try:
            doc = Document(io.BytesIO(file_bytes))
            text = "\n".join([para.text for para in doc.paragraphs])
            return text
        except Exception as e:
            logger.error(f"python-docx failed: {e}")
            return ""

    async def parse_resume(self, file_bytes: bytes, filename: str) -> ResumeData:
        """
        Extracts text and uses LLM to structure it into ResumeData.
        """
        logger.info(f"--- Resume Parsing Started: {filename} ---")
        if filename.lower().endswith('.pdf'):
            raw_text = self.extract_text_from_pdf(file_bytes)
        elif filename.lower().endswith('.docx'):
            raw_text = self.extract_text_from_docx(file_bytes)
        else:
            raise ValueError("Unsupported file format. Use PDF or DOCX.")

        logger.info(f"Extracted Text Length: {len(raw_text)} characters")
        if not raw_text.strip():
            logger.error("No text extracted from document!")
            return self._get_empty_fallback()

        prompt = f"""
        You are an expert resume parser. Extract the candidate's core details from the resume text and map them to the structured schema.
        Do not summarize or truncate descriptions. Be comprehensive and thorough.
        
        Fields to extract:
        - skills: A comprehensive list of technical skills, programming languages, libraries, frameworks, tools, and certifications.
        - years_of_experience: The total years of experience, or a calculated estimation (e.g. '5 years', '2.5 years', or 'Not specified').
        - education_level: Highest degree or education level obtained (e.g. 'Bachelor's', 'Master's', 'PhD', 'High School', or 'None').
        - certifications: A list of professional certifications mentioned.
        - past_job_titles: A list of job titles/roles the candidate held in their work experience.

        Resume Text:
        {raw_text}
        """

        openai_key = os.getenv("OPENAI_API_KEY")
        openai_is_valid = openai_key and openai_key.startswith("sk-") and len(openai_key) > 20

        if openai_is_valid:
            try:
                logger.info("Invoking OpenAI (GPT-4o-Mini) for resume parsing...")
                result = await self.structured_llm.ainvoke([
                    SystemMessage(content="You are a professional resume parser. Extract every detail into the structured format provided."),
                    HumanMessage(content=prompt)
                ])
                if isinstance(result, dict):
                    return ResumeData(**result)
                return result
            except Exception as openai_err:
                logger.error(f"OpenAI parsing failed: {openai_err}. Using regex fallback.")
                return self._regex_fallback(raw_text)
        else:
            logger.info("No valid OpenAI API key found. Using regex fallback.")
            return self._regex_fallback(raw_text)

    def _regex_fallback(self, text: str) -> ResumeData:
        """Basic extraction fallback using keywords."""
        skills_bank = [
            "python", "javascript", "react", "fastapi", "docker", "aws", "sql",
            "machine learning", "java", "c++", "typescript", "excel", "power bi",
            "tableau", "data analysis", "reporting", "dashboard", "analytics",
            "requirements gathering", "stakeholder management", "documentation",
            "customer support", "troubleshooting", "sales", "marketing", "crm",
            "operations", "project management", "communication", "leadership",
            "training", "coaching", "fitness", "nutrition", "personal trainer"
        ]
        found_skills = [s.title() for s in skills_bank if s in text.lower()]
        
        years_match = re.search(r'(\d+)\+?\s*years?', text.lower())
        years = f"{years_match.group(1)} years" if years_match else "Not specified"
        
        edu_level = "Not specified"
        if any(w in text.lower() for w in ["phd", "ph.d"]):
            edu_level = "PhD"
        elif any(w in text.lower() for w in ["master", "m.s.", "ms", "mba"]):
            edu_level = "Master's"
        elif any(w in text.lower() for w in ["bachelor", "b.s.", "bs", "b.tech"]):
            edu_level = "Bachelor's"
            
        return ResumeData(
            skills=found_skills,
            years_of_experience=years,
            education_level=edu_level,
            certifications=[],
            past_job_titles=[]
        )

    def _get_empty_fallback(self) -> ResumeData:
        return ResumeData(
            skills=[],
            years_of_experience="Not specified",
            education_level="Not specified",
            certifications=[],
            past_job_titles=[]
        )
