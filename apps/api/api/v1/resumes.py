from fastapi import APIRouter, UploadFile, File, HTTPException, status, Depends
from sqlalchemy.orm import Session
from db.session import get_db
from db.models import Resume
from services.resume_parser_v2 import ResumeParserService
from services.resume_analyzer import ResumeAnalyzerService
import uuid
import logging

router = APIRouter(prefix="/api/v1/resumes", tags=["resumes"])
logger = logging.getLogger(__name__)
parser_service = ResumeParserService()
analyzer_service = ResumeAnalyzerService()

@router.post("/upload")
async def upload_resume(file: UploadFile = File(...), db: Session = Depends(get_db)):
    """
    Upload, parse, and analyze a resume.
    """
    filename = file.filename.lower()
    logger.info(f"--- POST /upload started for file: {filename} ---")
    if not (filename.endswith(".pdf") or filename.endswith(".docx")):
        logger.error(f"Unsupported file format attempted: {filename}")
        raise HTTPException(status_code=400, detail="Only PDF and DOCX supported.")
    
    try:
        file_bytes = await file.read()
        logger.info(f"File read successful. Size: {len(file_bytes)} bytes")
        
        # 1. Parse Resume to structured JSON
        structured_data = await parser_service.parse_resume(file_bytes, filename)
        logger.info(f"Step 1: Parsing complete. Skills extracted: {structured_data.skills}")
        
        # 2. Analyze Resume for Job Preferences
        logger.info("Step 2: Starting AI/Rule-based Analysis...")
        analysis_result = await analyzer_service.analyze(structured_data.model_dump())
        logger.info(f"Step 2: Analysis complete. Roles generated: {[r.role for r in analysis_result.suggested_roles]}")
        
        # 3. Save to Database
        new_resume = Resume(
            id=uuid.uuid4(),
            file_url=filename, 
            parsed_content=structured_data.model_dump(),
            analysis_result=analysis_result.model_dump()
        )
        db.add(new_resume)
        db.commit()
        db.refresh(new_resume)
        
        logger.info(f"Step 3: Resume persisted to DB with ID: {new_resume.id}")
        
        return {
            "id": str(new_resume.id),
            "status": "success",
            "data": structured_data.model_dump(),
            "analysis": analysis_result.model_dump()
        }

    except Exception as e:
        logger.error(f"CRITICAL: Upload pipeline failed: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        await file.close()

@router.post("/{resume_id}/reanalyze")
async def reanalyze_resume(resume_id: str, db: Session = Depends(get_db)):
    """
    Re-run role analysis for an already uploaded resume.
    Useful after role-matching logic changes or when old analysis was too generic.
    """
    logger.info(f"--- POST /resumes/{resume_id}/reanalyze requested ---")
    try:
        resume_uuid = uuid.UUID(resume_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid resume_id format")

    resume = db.query(Resume).filter(Resume.id == resume_uuid).first()
    if not resume:
        raise HTTPException(status_code=404, detail="Resume not found")

    analysis_result = await analyzer_service.analyze(resume.parsed_content or {})
    resume.analysis_result = analysis_result.model_dump()
    db.commit()
    db.refresh(resume)

    return {
        "id": str(resume.id),
        "parsed_content": resume.parsed_content,
        "analysis_result": resume.analysis_result
    }

@router.get("/{resume_id}")
async def get_resume_data(resume_id: str, db: Session = Depends(get_db)):
    """
    Fetches stored resume data and its AI analysis.
    """
    logger.info(f"--- GET /resumes/{resume_id} requested ---")
    try:
        resume_uuid = uuid.UUID(resume_id)
        resume = db.query(Resume).filter(Resume.id == resume_uuid).first()
        if not resume:
            logger.warning(f"Resume {resume_id} not found in database.")
            raise HTTPException(status_code=404, detail="Resume not found")
            
        logger.info(f"Resume found. Analysis Result present: {resume.analysis_result is not None}")
        if resume.analysis_result:
            roles = resume.analysis_result.get('suggested_roles', [])
            logger.info(f"Returning {len(roles)} suggested roles.")
            
        return {
            "id": str(resume.id),
            "parsed_content": resume.parsed_content,
            "analysis_result": resume.analysis_result
        }
    except ValueError:
        logger.error(f"Invalid UUID format: {resume_id}")
        raise HTTPException(status_code=400, detail="Invalid resume_id format")
