from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import func
from typing import List, Dict
from pydantic import BaseModel
from db.session import get_db
from db.models import Interview, User, InterviewData, InterviewAnalytics
from services.interview_analytics import serialize_analytics, analyze_interview
import uuid

router = APIRouter(prefix="/api/v1/analytics", tags=["analytics"])

class PerformanceTrend(BaseModel):
    date: str
    overall_score: float
    technical_score: float
    communication_score: float

class AnalyticsSummary(BaseModel):
    total_interviews: int
    avg_overall_score: float
    avg_technical_score: float
    avg_communication_score: float
    trends: List[PerformanceTrend]

@router.get("/interviews")
async def get_all_interview_analytics(db: Session = Depends(get_db)):
    """
    Returns stored deep analytics for dashboard visualizations.
    Falls back to completed interview history when analytics are still pending.
    """
    completed_interviews = db.query(Interview).filter(Interview.status == "completed").all()
    for interview in completed_interviews:
        exists = db.query(InterviewAnalytics).filter(InterviewAnalytics.interview_id == interview.id).first()
        if not exists or not (exists.charts or {}).get("career_recommendations"):
            analyze_interview(str(interview.id), db)

    analytics_records = db.query(InterviewAnalytics).order_by(InterviewAnalytics.created_at.desc()).all()
    serialized = [serialize_analytics(record) for record in analytics_records]
    interviews = db.query(Interview).order_by(Interview.created_at.desc()).all()

    trends = []
    for interview in reversed(interviews):
        matching = next((item for item in serialized if item["interview_id"] == str(interview.id)), None)
        scores = matching.get("overall_scores", {}) if matching else {}
        trends.append({
            "name": interview.created_at.strftime("%b %d"),
            "interview_id": str(interview.id),
            "overall": scores.get("overall_score", interview.overall_score or 0),
            "technical": scores.get("technical_knowledge", interview.overall_score or 0),
            "communication": scores.get("communication", 0),
            "confidence": scores.get("confidence", 0),
        })

    completed = [item for item in serialized if item["status"] == "completed"]
    score_sets = [item["overall_scores"] for item in completed if item.get("overall_scores")]

    def avg(key: str) -> float:
        values = [scores.get(key, 0) for scores in score_sets if scores.get(key) is not None]
        return round(sum(values) / len(values), 1) if values else 0

    latest = serialized[0] if serialized else None
    return {
        "total": len(interviews),
        "completed_analytics": len(completed),
        "avg_scores": {
            "overall": avg("overall_score"),
            "technical": avg("technical_knowledge"),
            "communication": avg("communication"),
            "confidence": avg("confidence"),
            "problem_solving": avg("problem_solving"),
            "clarity": avg("clarity"),
            "professionalism": avg("professionalism"),
        },
        "trends": trends,
        "latest": latest,
        "records": serialized,
    }

@router.get("/user/{user_id}", response_model=AnalyticsSummary)
async def get_user_analytics(user_id: uuid.UUID, db: Session = Depends(get_db)):
    """
    Fetch aggregated analytics and trends for a specific user using real data.
    """
    # 1. Fetch all completed interviews for the user
    interviews = db.query(Interview).filter(
        Interview.user_id == user_id,
        Interview.status == "completed"
    ).order_by(Interview.created_at.asc()).all()

    if not interviews:
        return AnalyticsSummary(
            total_interviews=0,
            avg_overall_score=0,
            avg_technical_score=0,
            avg_communication_score=0,
            trends=[]
        )

    # 2. Fetch Detailed Turn Data for precise averaging
    interview_ids = [i.id for i in interviews]
    all_turns = db.query(InterviewData).filter(InterviewData.interview_id.in_(interview_ids)).all()

    # Aggregate Technical & Communication Scores
    tech_scores = [t.technical_score for t in all_turns if t.technical_score is not None]
    comm_scores = [t.communication_score for t in all_turns if t.communication_score is not None]

    avg_tech = sum(tech_scores) / len(tech_scores) if tech_scores else 0
    avg_comm = sum(comm_scores) / len(comm_scores) if comm_scores else 0
    
    total = len(interviews)
    avg_overall = sum(i.overall_score for i in interviews if i.overall_score) / total

    # 3. Build Trends
    trends = []
    for interview in interviews:
        # Get specific turn data for this interview to calculate per-session scores
        i_turns = [t for t in all_turns if t.interview_id == interview.id]
        i_tech = [t.technical_score for t in i_turns if t.technical_score is not None]
        i_comm = [t.communication_score for t in i_turns if t.communication_score is not None]
        
        trends.append(PerformanceTrend(
            date=interview.created_at.strftime("%Y-%m-%d"),
            overall_score=interview.overall_score or 0,
            technical_score=sum(i_tech) / len(i_tech) if i_tech else 0,
            communication_score=sum(i_comm) / len(i_comm) if i_comm else 0
        ))

    return AnalyticsSummary(
        total_interviews=total,
        avg_overall_score=round(avg_overall, 2),
        avg_technical_score=round(avg_tech, 2),
        avg_communication_score=round(avg_comm, 2),
        trends=trends
    )
