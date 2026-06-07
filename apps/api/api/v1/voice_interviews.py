import uuid
from typing import Any, Dict, List

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from core.deps import get_current_user
from db.models import User, VoiceInterviewProfile
from db.session import get_db
from services.voice_profile_generator import VoiceInterviewProfileGenerator

router = APIRouter(prefix="/api/v1/voice-interviews", tags=["voice-interviews"])
profile_generator = VoiceInterviewProfileGenerator()


class TranscriptTurn(BaseModel):
    role: str = Field(default="user")
    content: str
    timestamp: str | None = None


class VoiceInterviewAnalyzeRequest(BaseModel):
    transcript: List[TranscriptTurn]
    duration_seconds: int = 0


@router.post("/analyze")
async def analyze_voice_interview(
    payload: VoiceInterviewAnalyzeRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    if not payload.transcript:
        raise HTTPException(status_code=400, detail="Transcript is required")

    result = await profile_generator.generate([turn.model_dump() for turn in payload.transcript])
    record = VoiceInterviewProfile(
        id=uuid.uuid4(),
        user_id=current_user.id,
        status="completed",
        candidate_profile=result["candidate_profile"],
        recommended_roles=result["recommended_roles"],
        transcript=[turn.model_dump() for turn in payload.transcript],
        overall_score=result["overall_score"],
    )
    db.add(record)
    db.commit()
    db.refresh(record)

    return {
        "id": str(record.id),
        "status": record.status,
        "candidate_profile": record.candidate_profile,
        "recommended_roles": record.recommended_roles,
        "all_suggested_roles": result.get("all_suggested_roles", []),
        "overall_score": record.overall_score,
        "created_at": record.created_at.isoformat(),
    }


@router.get("/history")
async def voice_interview_history(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    records = (
        db.query(VoiceInterviewProfile)
        .filter(VoiceInterviewProfile.user_id == current_user.id)
        .order_by(VoiceInterviewProfile.created_at.desc())
        .all()
    )
    return [
        {
            "id": str(record.id),
            "status": record.status,
            "candidate_profile": record.candidate_profile,
            "recommended_roles": record.recommended_roles,
            "overall_score": record.overall_score,
            "created_at": record.created_at.isoformat(),
        }
        for record in records
    ]


@router.get("/{profile_id}")
async def get_voice_interview_profile(
    profile_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    try:
        profile_uuid = uuid.UUID(profile_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid profile id")

    record = (
        db.query(VoiceInterviewProfile)
        .filter(VoiceInterviewProfile.id == profile_uuid, VoiceInterviewProfile.user_id == current_user.id)
        .first()
    )
    if not record:
        raise HTTPException(status_code=404, detail="Voice interview profile not found")

    return {
        "id": str(record.id),
        "status": record.status,
        "candidate_profile": record.candidate_profile,
        "recommended_roles": record.recommended_roles,
        "transcript": record.transcript,
        "overall_score": record.overall_score,
        "created_at": record.created_at.isoformat(),
    }
