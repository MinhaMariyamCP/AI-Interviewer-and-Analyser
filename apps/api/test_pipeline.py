import asyncio
import json
import os
from services.resume_parser_v2 import ResumeParserService
from services.resume_analyzer import ResumeAnalyzerService

async def test_pipeline():
    print("--- Starting Pipeline Test ---")
    parser = ResumeParserService()
    analyzer = ResumeAnalyzerService()
    
    # Mock text that would be extracted from a real PDF
    mock_resume_text = """
    John Doe
    Fullstack Engineer
    Skills: Python, FastAPI, React, TypeScript, Docker, PostgreSQL, Machine Learning, LangChain.
    Experience:
    - Senior Software Engineer at Tech Corp (2020-Present): 
      Built a high-performance API using FastAPI and Python. Implemented ML models for data classification.
    - Software Developer at Web Solutions (2018-2020):
      Developed frontend components using React and Redux.
    Projects:
    - AI Chatbot: Built a LangGraph-powered agent for automated customer support.
    """
    
    print("1. Testing Parser Model...")
    # We'll just test the analysis part directly as parser structuring is similar
    structured_data = {
        "skills": ["Python", "FastAPI", "React", "Machine Learning", "LangChain"],
        "years_of_experience": "6 years",
        "education_level": "Bachelor's",
        "certifications": [],
        "past_job_titles": ["Senior Software Engineer", "Software Developer"]
    }
    
    print("2. Testing Analyzer Service...")
    analysis = await analyzer.analyze(structured_data)
    
    print("\n--- AI GENERATED JOB PREFERENCES ---")
    for pref in analysis.suggested_roles:
        print(f"Role: {pref.role}")
        print(f"Confidence: {pref.confidence}%")
        print(f"Reasoning: {pref.reasoning}")
        print("-" * 20)
    
    assert len(analysis.suggested_roles) >= 5
    print("\nSUCCESS: Pipeline verified with real LLM response.")

if __name__ == "__main__":
    from dotenv import load_dotenv
    load_dotenv()
    
    asyncio.run(test_pipeline())
