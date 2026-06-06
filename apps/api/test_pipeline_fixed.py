import asyncio
import json
import os
import logging
from services.resume_parser_v2 import ResumeParserService
from services.resume_analyzer import ResumeAnalyzerService
from dotenv import load_dotenv

logging.basicConfig(level=logging.INFO)

async def test_pipeline():
    load_dotenv()
    print("\n--- [START] Complete Resume Pipeline Test ---")
    
    parser = ResumeParserService()
    analyzer = ResumeAnalyzerService()
    
    # Simulate a resume text
    mock_text = """
    ALEX SMITH
    Email: alex.smith@email.com
    Phone: 555-0199
    
    SKILLS:
    Python, FastAPI, React, Docker, Kubernetes, AWS, PostgreSQL, TensorFlow.
    
    EXPERIENCE:
    Senior Software Engineer at CloudSystems (2020-2024)
    - Designed and implemented microservices using FastAPI and Go.
    - Orchestrated container deployment using Kubernetes on AWS.
    - Improved API response time by 40% through Redis caching.
    
    PROJECTS:
    AI Resume Screener: Built a tool using GPT-4 and Python to automate recruitment.
    """
    
    print("\n1. Testing Parser Fallback (Simulating Text)...")
    parsed_data = parser._regex_fallback(mock_text)
    print(f"Parsed Skills: {parsed_data.skills}")
    
    print("\n2. Testing Full Analyzer (LLM + Fallback)...")
    analysis = await analyzer.analyze(parsed_data.model_dump())
    
    print("\n--- GENERATED JOB PREFERENCES ---")
    if analysis.suggested_roles:
        for pref in analysis.suggested_roles:
            print(f"Role: {pref.role}")
            print(f"Confidence: {pref.confidence}%")
            print(f"Reasoning: {pref.reasoning}")
            print("-" * 15)
    else:
        print("FAILED: No roles generated.")

    print("\n3. Verifying Database Model Integrity...")
    from db.models import Resume
    import uuid
    
    res = Resume(
        id=uuid.uuid4(),
        file_url="test.pdf",
        parsed_content=parsed_data.model_dump(),
        analysis_result=analysis.model_dump()
    )
    print(f"Resume Model Object Created with ID: {res.id}")
    print(f"Analysis Result in Object: {res.analysis_result['suggested_roles'][0]['role']}...")

    print("\n--- [SUCCESS] Pipeline Verified End-to-End ---")

if __name__ == "__main__":
    asyncio.run(test_pipeline())
