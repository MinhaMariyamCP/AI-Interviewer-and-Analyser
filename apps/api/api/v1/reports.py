from fastapi import APIRouter, Depends, HTTPException, Response
from sqlalchemy.orm import Session
from db.session import get_db
from services.report_generator import PDFReportGenerator, get_report_data_from_db
import uuid

router = APIRouter(prefix="/api/v1/reports", tags=["reports"])
generator = PDFReportGenerator()

@router.get("/{interview_id}/download")
async def download_interview_report(interview_id: str, db: Session = Depends(get_db)):
    """
    Generates and downloads a professional PDF report for a completed interview.
    Fetches real data from the database.
    """
    try:
        # 1. Aggregate real data from DB
        report_data = await get_report_data_from_db(interview_id, db)
        if not report_data:
            raise HTTPException(status_code=404, detail="Interview not found or has no evaluation data.")

        # 2. Generate PDF bytes
        pdf_bytes = generator.generate(report_data)

        # 3. Return as downloadable file
        filename = f"Interview_Report_{report_data.candidate_name.replace(' ', '_')}_{interview_id[:8]}.pdf"
        
        return Response(
            content=pdf_bytes,
            media_type="application/pdf",
            headers={
                "Content-Disposition": f"attachment; filename={filename}"
            }
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
