import pytest
from services.resume_parser_v2 import ResumeParserService, ResumeData
import os

@pytest.fixture
def parser():
    return ResumeParserService()

def test_extract_text_pdf(parser):
    pass

@pytest.mark.anyio
async def test_llm_parsing_mock(parser, mocker):
    mock_resume_text = "John Doe, python developer at Google for 5 years. Skills: Python, Docker."
    
    # Mock the LLM response to match the simplified schema
    mock_data = ResumeData(
        skills=["Python", "Docker"],
        years_of_experience="5 years",
        education_level="Not specified",
        certifications=[],
        past_job_titles=["Developer"]
    )
    
    mocker.patch.dict(os.environ, {"OPENAI_API_KEY": "sk-12345678901234567890"})
    
    mock_runnable = mocker.MagicMock()
    mock_runnable.ainvoke = mocker.AsyncMock(return_value=mock_data)
    parser.structured_llm = mock_runnable
    mocker.patch.object(parser, 'extract_text_from_pdf', return_value=mock_resume_text)
    
    result = await parser.parse_resume(b"dummy_bytes", "test.pdf")
    
    assert "Python" in result.skills
    assert result.years_of_experience == "5 years"
    assert "Developer" in result.past_job_titles
