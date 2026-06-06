import asyncio
import os
import sys
from dotenv import load_dotenv

# Ensure apps/api is in Python path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from services.resume_parser_v2 import ResumeParserService

async def main():
    load_dotenv()
    print("OPENAI_API_KEY present:", bool(os.getenv("OPENAI_API_KEY")))
    
    parser = ResumeParserService()
    
    # Create a small dummy PDF in memory
    from reportlab.pdfgen import canvas
    import io
    
    packet = io.BytesIO()
    c = canvas.Canvas(packet)
    c.drawString(100, 750, "Jane Doe")
    c.drawString(100, 730, "Email: jane.doe@example.com")
    c.drawString(100, 710, "Skills: Python, React, FastAPI, SQL, Machine Learning")
    c.drawString(100, 690, "Experience: Software Engineer at tech company (2022-2024)")
    c.save()
    
    packet.seek(0)
    pdf_bytes = packet.read()
    
    print("\nParsing resume using parse_resume (should invoke LLM)...")
    try:
        result = await parser.parse_resume(pdf_bytes, "test_resume.pdf")
        print("\nSUCCESS: Parsed Content:")
        print(result.model_dump_json(indent=2))
    except Exception as e:
        print("\nFAILED with exception:", e)
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(main())
