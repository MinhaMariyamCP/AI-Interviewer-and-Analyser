from typing import List, Dict, Optional
from pydantic import BaseModel, Field
from langchain_openai import ChatOpenAI
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_core.messages import HumanMessage, SystemMessage
import os
import fitz  # PyMuPDF
from docx import Document
import io
import json
import logging
import re

logger = logging.getLogger(__name__)

# --- 1. Structured Data Models ---

class Experience(BaseModel):
    company: str
    role: str
    duration: str
    description: List[str]

class Education(BaseModel):
    institution: str
    degree: str
    year: str

class Project(BaseModel):
    name: str
    description: str
    technologies: List[str]

class ResumeData(BaseModel):
    full_name: Optional[str]
    email: Optional[str]
    phone: Optional[str]
    skills: List[str]
    experience: List[Experience]
    education: List[Education]
    projects: List[Project]

# Rebuild models for Pydantic v2 compatibility with nested types
ResumeData.model_rebuild()

# --- 2. Parser Service ---

class ResumeParserService:
    def __init__(self, api_key: str = None):
        google_key = os.getenv("GOOGLE_API_KEY")
        openai_key = api_key or os.getenv("OPENAI_API_KEY")
        
        if google_key and not google_key.startswith("AQ."):
            logger.info("Using Google Gemini for ResumeParserService")
            self.llm = ChatGoogleGenerativeAI(
                model="gemini-1.5-flash",
                google_api_key=google_key,
                temperature=0
            )
        else:
            logger.info("Using OpenAI GPT for ResumeParserService")
            self.llm = ChatOpenAI(
                model="gpt-4o-mini",
                openai_api_key=openai_key,
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
        Extract structured information from the following resume text.
        Resume Text:
        {raw_text}
        """

        try:
            google_key = os.getenv("GOOGLE_API_KEY")
            if google_key and not google_key.startswith("AQ."):
                logger.info("Invoking native Google Gemini for resume parsing...")
                import google.generativeai as genai
                genai.configure(api_key=google_key)
                model = genai.GenerativeModel("gemini-1.5-flash")
                
                import asyncio
                from functools import partial
                
                loop = asyncio.get_running_loop()
                response = await loop.run_in_executor(
                    None,
                    partial(
                        model.generate_content,
                        prompt,
                        generation_config=genai.GenerationConfig(
                            response_mime_type="application/json",
                            response_schema=ResumeData,
                            temperature=0.0
                        )
                    )
                )
                logger.info("Native Gemini parsing successful")
                data = json.loads(response.text)
                return ResumeData(**data)
            else:
                logger.info("Invoking OpenAI (via Langchain) for resume parsing...")
                result = await self.structured_llm.ainvoke([
                    SystemMessage(content="You are a professional resume parser. Extract every detail into the structured format provided."),
                    HumanMessage(content=prompt)
                ])
                return result
        except Exception as e:
            logger.error(f"LLM Parsing failed: {e}. Using regex fallback.", exc_info=True)
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
        
        # Simple email/phone regex
        email = re.search(r'[\w\.-]+@[\w\.-]+', text)
        phone = re.search(r'\(?\d{3}\)?[-.\s]?\d{3}[-.\s]?\d{4}', text)
        
        return ResumeData(
            full_name="Extracted Candidate",
            email=email.group(0) if email else None,
            phone=phone.group(0) if phone else None,
            skills=found_skills,
            experience=[],
            education=[],
            projects=[]
        )

    def _get_empty_fallback(self) -> ResumeData:
        return ResumeData(
            full_name=None, email=None, phone=None, 
            skills=[], experience=[], education=[], projects=[]
        )
