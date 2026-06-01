import pytest
from services.resume_parser_v2 import ResumeParserService
import os

@pytest.fixture
def parser():
    return ResumeParserService()

def test_extract_text_pdf(parser):
    # This test would require a sample PDF file
    # For CI, we can mock or use a minimal generated PDF
    pass

@pytest.mark.asyncio
async def test_llm_parsing_mock(parser, mocker):
    mock_resume_text = "John Doe, python developer at Google for 5 years. Skills: Python, Docker."
    
    # Mock the LLM response to avoid API costs during tests
    mock_data = {
        "full_name": "John Doe",
        "email": "john@doe.com",
        "skills": ["Python", "Docker"],
        "experience": [{"company": "Google", "role": "Developer", "duration": "5 years", "description": []}],
        "education": [],
        "projects": []
    }
    
    mocker.patch.object(parser.structured_llm, 'ainvoke', return_value=mock_data)
    
    # We need to mock the file extraction as well or provide a dummy file
    mocker.patch.object(parser, 'extract_text_from_pdf', return_value=mock_resume_text)
    
    result = await parser.parse_resume(b"dummy_bytes", "test.pdf")
    
    assert result["full_name"] == "John Doe"
    assert "Python" in result["skills"]
