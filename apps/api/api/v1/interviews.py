from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Depends, HTTPException, Response
import asyncio
import time
from sqlalchemy.orm import Session
from db.session import get_db
from db.models import Interview, Resume, InterviewData, InterviewAnalytics, User
from core.deps import get_current_user, get_current_user_ws
from agents.adaptive_orchestrator import adaptive_interview_graph
from services.voice_service import VoiceService
from services.interview_analytics import analyze_interview, analyze_interview_async, serialize_analytics, generate_analytics_pdf
import uuid
import json
import logging
import base64
import re
from typing import List
from pydantic import BaseModel
from datetime import datetime

router = APIRouter(prefix="/api/v1/interviews", tags=["interviews"])
logger = logging.getLogger(__name__)
voice_service = VoiceService()
MAX_LIVE_TURNS = 5

class InterviewSchema(BaseModel):
    id: uuid.UUID
    status: str
    overall_score: float = None
    created_at: datetime

    class Config:
        from_attributes = True

def build_final_report(state: dict) -> dict:
    history = state.get("answer_history", [])
    if not history:
        return {
            "overall_score": 0,
            "technical_score": 0,
            "communication_score": 0,
            "knowledge_depth": 0,
            "confidence_score": 0,
            "summary": "Interview completed.",
            "total_questions": 0,
            "question_history": []
        }

    def average(metric: str) -> float:
        values = [
            item.get("evaluation", {}).get(metric, 0)
            for item in history
            if item.get("evaluation")
        ]
        return sum(values) / len(values) if values else 0

    technical = average("technical_score")
    communication = average("communication_score")
    depth = average("knowledge_depth")
    confidence = average("confidence_score")
    overall = (technical * 0.4) + (communication * 0.2) + (depth * 0.3) + (confidence * 0.1)

    return {
        "overall_score": overall,
        "technical_score": technical,
        "communication_score": communication,
        "knowledge_depth": depth,
        "confidence_score": confidence,
        "summary": "Interview completed after five focused questions with live scoring.",
        "total_questions": len(history),
        "question_history": [item.get("question") for item in history]
    }

def build_fallback_eval(question: str = "", answer: str = "", profile: dict = None, role: str = "") -> dict:
    profile = profile or {}
    answer_text = (answer or "").strip()
    answer_lower = answer_text.lower()
    words = re.findall(r"\b\w+\b", answer_lower)
    word_total = len(words)

    resume_terms = []
    for key in ("technologies", "core_skills"):
        value = profile.get(key) or []
        if isinstance(value, list):
            resume_terms.extend(str(item).lower() for item in value if str(item).strip())

    project_terms = []
    for project in profile.get("projects") or []:
        if isinstance(project, dict):
            project_terms.append(str(project.get("name") or "").lower())

    technical_keywords = [
        "because", "tradeoff", "architecture", "design", "scale", "scalable", "database",
        "api", "testing", "debug", "performance", "security", "deploy", "monitor",
        "optimized", "implemented", "measured", "result", "latency", "cache"
    ]
    vague_phrases = ["i don't know", "not sure", "no idea", "maybe", "nothing", "can't remember"]

    detail_score = min(word_total * 1.1, 35)
    relevance_hits = sum(1 for term in resume_terms[:20] if term and term in answer_lower)
    project_hits = sum(1 for term in project_terms[:8] if term and term in answer_lower)
    technical_hits = sum(1 for keyword in technical_keywords if keyword in answer_lower)
    vague_penalty = 25 if any(phrase in answer_lower for phrase in vague_phrases) else 0
    too_short_penalty = 25 if word_total < 12 else 0

    technical = 25 + detail_score + min(relevance_hits * 8, 24) + min(project_hits * 8, 16) + min(technical_hits * 4, 20) - vague_penalty - too_short_penalty
    communication = 30 + min(word_total * 0.9, 35) + (12 if any(token in answer_lower for token in ["first", "then", "finally", "for example", "result"]) else 0) - (15 if word_total < 10 else 0)
    confidence = 35 + min(word_total * 0.6, 25) - (18 if any(phrase in answer_lower for phrase in ["maybe", "i think", "not sure"]) else 0)
    depth = 25 + min(technical_hits * 7, 35) + min(relevance_hits * 6, 24) + (10 if any(token in answer_lower for token in ["why", "because", "tradeoff", "alternative"]) else 0) - too_short_penalty

    def clamp(value: float) -> int:
        return int(max(0, min(100, round(value))))

    weak_areas = []
    strong_areas = []
    if word_total < 30:
        weak_areas.append("Answer needs more detail and concrete evidence.")
    if relevance_hits == 0:
        weak_areas.append("Response did not clearly connect to resume skills or projects.")
    if technical_hits < 2:
        weak_areas.append("Add more technical reasoning, tradeoffs, and measurable outcomes.")
    if word_total >= 45:
        strong_areas.append("Gave a detailed response with enough context to evaluate.")
    if relevance_hits > 0 or project_hits > 0:
        strong_areas.append("Connected the answer to resume-specific experience.")
    if technical_hits >= 3:
        strong_areas.append("Included technical reasoning and implementation signals.")

    return {
        "technical_score": clamp(technical),
        "communication_score": clamp(communication),
        "confidence_score": clamp(confidence),
        "knowledge_depth": clamp(depth),
        "weak_areas": weak_areas or ["Add a little more structure to make the answer easier to assess."],
        "strong_areas": strong_areas or ["Response captured successfully."],
        "reasoning": "Fast quality-based fallback evaluation used after the live AI analysis timeout."
    }

def plan_fallback_question(state: dict) -> dict:
    profile = state.get("candidate_profile") or {}
    remaining = list(state.get("remaining_topics") or [])
    covered = list(state.get("covered_topics") or [])
    asked = list(state.get("asked_questions") or [])
    topic = remaining[0] if remaining else "Technical Skills"
    skills = profile.get("technologies") or profile.get("core_skills") or ["your main technical stack"]
    skill = skills[min(len(asked), len(skills) - 1)] if skills else "your main technical stack"
    question = f"For {topic}, can you describe a concrete example where you used {skill} and explain the key tradeoff you made?"

    if topic in remaining:
        remaining.remove(topic)
        covered.append(topic)

    return {
        "current_question": question,
        "current_topic": topic,
        "asked_questions": asked + [question],
        "covered_topics": covered,
        "remaining_topics": remaining,
        "duplicate_detected": False,
        "next_step": "wait_for_answer"
    }

@router.get("/history", response_model=List[InterviewSchema])
async def get_interview_history(db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    interviews = db.query(Interview).filter(Interview.user_id == current_user.id).order_by(Interview.created_at.desc()).all()
    return interviews

@router.post("/init")
async def init_interview(resume_id: str, job_role: str = "Software Engineer", db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    try:
        resume_uuid = uuid.UUID(resume_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid resume_id format")

    resume = db.query(Resume).filter(Resume.id == resume_uuid, Resume.user_id == current_user.id).first()
    if not resume:
        raise HTTPException(status_code=404, detail="Resume not found")
    
    interview = Interview(
        id=uuid.uuid4(),
        resume_id=resume.id,
        user_id=resume.user_id,
        job_role=job_role,
        status="started"
    )
    db.add(interview)
    db.commit()
    db.refresh(interview)
    
    return {"interview_id": str(interview.id), "status": "initialized"}

def get_interview_or_404(interview_id: str, db: Session, current_user: User) -> Interview:
    try:
        interview_uuid = uuid.UUID(interview_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid interview_id format")

    interview = db.query(Interview).filter(Interview.id == interview_uuid, Interview.user_id == current_user.id).first()
    if not interview:
        raise HTTPException(status_code=404, detail="Interview not found")
    return interview

@router.post("/{interview_id}/analyze")
async def analyze_interview_endpoint(interview_id: str, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    get_interview_or_404(interview_id, db, current_user)
    analytics = analyze_interview(interview_id, db)
    return serialize_analytics(analytics)

@router.get("/{interview_id}/analytics")
async def get_interview_analytics(interview_id: str, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    interview = get_interview_or_404(interview_id, db, current_user)
    analytics = db.query(InterviewAnalytics).filter(InterviewAnalytics.interview_id == interview.id).first()
    if not analytics:
        return {"status": "pending", "message": "Generating Interview Insights..."}
    if not (analytics.charts or {}).get("career_recommendations"):
        analytics = analyze_interview(interview_id, db)
    return serialize_analytics(analytics)

@router.get("/{interview_id}/charts")
async def get_interview_charts(interview_id: str, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    interview = get_interview_or_404(interview_id, db, current_user)
    analytics = db.query(InterviewAnalytics).filter(InterviewAnalytics.interview_id == interview.id).first()
    if not analytics:
        return {"status": "pending", "charts": {}}
    return {"status": analytics.status, "charts": analytics.charts or {}}

@router.get("/{interview_id}/improvements")
async def get_interview_improvements(interview_id: str, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    interview = get_interview_or_404(interview_id, db, current_user)
    analytics = db.query(InterviewAnalytics).filter(InterviewAnalytics.interview_id == interview.id).first()
    if not analytics:
        return {"status": "pending", "improvement_roadmap": []}
    return {"status": analytics.status, "improvement_roadmap": analytics.improvement_roadmap or []}

@router.get("/{interview_id}/report")
async def download_interview_analytics_report(interview_id: str, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    interview = get_interview_or_404(interview_id, db, current_user)
    analytics = db.query(InterviewAnalytics).filter(InterviewAnalytics.interview_id == interview.id).first()
    if not analytics or not (analytics.charts or {}).get("career_recommendations"):
        analytics = analyze_interview(interview_id, db)
    pdf = generate_analytics_pdf(analytics, interview)
    return Response(
        content=pdf,
        media_type="application/pdf",
        headers={"Content-Disposition": f"attachment; filename=Interview_Analytics_{interview_id[:8]}.pdf"}
    )

@router.websocket("/{interview_id}/stream")
async def interview_stream(websocket: WebSocket, interview_id: str, token: str, db: Session = Depends(get_db)):
    start_handshake = time.time()
    await websocket.accept()
    logger.info(f"--- WebSocket connected for interview {interview_id} ---")
    
    try:
        current_user = get_current_user_ws(token, db)
    except ValueError as e:
        await websocket.send_json({"type": "error", "message": str(e)})
        await websocket.close(code=4001, reason=str(e))
        return

    try:
        interview_uuid = uuid.UUID(interview_id)
    except ValueError:
        await websocket.send_json({"type": "error", "message": "Invalid interview_id format"})
        await websocket.close(code=4000)
        return

    interview = db.query(Interview).filter(Interview.id == interview_uuid, Interview.user_id == current_user.id).first()
    if not interview:
        logger.error(f"Interview {interview_id} not found in DB")
        await websocket.send_json({"type": "error", "message": "Interview not found"})
        await websocket.close(code=4004)
        return
        
    resume = db.query(Resume).filter(Resume.id == interview.resume_id).first()
    logger.info(f"Session data loaded. Resume ID: {interview.resume_id}")
    
    # Synchronization Lock
    turn_lock = asyncio.Lock()
    
    state = {
        "resume_data": resume.parsed_content or {},
        "job_role": interview.job_role or "Software Engineer",
        "candidate_profile": None,
        "covered_topics": [],
        "remaining_topics": ["Resume Projects", "Technical Skills", "System Design", "Problem Solving", "Behavioral Questions", "Leadership", "Communication"],
        "asked_questions": [],
        "attempted_questions": [],
        "answer_history": [],
        "current_question": "",
        "current_answer": "",
        "current_turn_eval": None,
        "turn_count": 0,
        "duplicate_detected": False,
        "scores": {},
        "next_step": "analyze_resume",
        "final_report": None,
        "is_completed": False
    }
    
    try:
        # 1. Start Interview - Initial Question
        logger.info("Step 1: Invoking adaptive_interview_graph.ainvoke for setup...")
        start_q1 = time.time()
        
        try:
            # First turn: analyze_resume -> plan_question
            state = await asyncio.wait_for(adaptive_interview_graph.ainvoke(state), timeout=25.0)
            logger.info(f"Step 1: Graph execution successful ({time.time() - start_q1:.2f}s)")
        except asyncio.TimeoutError:
            logger.error("Step 1 Failed: adaptive_interview_graph.ainvoke timed out (25s)")
            await websocket.send_json({"type": "error", "message": "AI System Timeout. Please try again."})
            return
        except Exception as graph_err:
            logger.error(f"Step 1 Failed: Graph execution error: {graph_err}", exc_info=True)
            await websocket.send_json({"type": "error", "message": f"Graph Error: {str(graph_err)}"})
            return
            
        # Synthesize Audio
        logger.info(f"Step 2: Synthesizing audio for question: {state['current_question'][:50]}...")
        start_tts = time.time()
        try:
            audio_bytes = await voice_service.text_to_speech(state["current_question"])
            logger.info(f"Step 2: TTS Complete ({time.time() - start_tts:.2f}s)")
        except Exception as tts_err:
            logger.error(f"Step 2 Failed: TTS Error: {tts_err}")
            audio_bytes = None

        audio_base64 = base64.b64encode(audio_bytes).decode('utf-8') if audio_bytes else None

        await websocket.send_json({
            "type": "question", 
            "text": state["current_question"],
            "audio": audio_base64
        })
        
        # Send initial topic info
        total_topics = len(state.get("covered_topics", [])) + len(state.get("remaining_topics", []))
        coverage = (len(state.get("covered_topics", [])) / total_topics * 100) if total_topics > 0 else 0
        
        await websocket.send_json({
            "type": "live_scores",
            "scores": {
                "technical_score": 0,
                "communication_score": 0,
                "confidence_score": 0,
                "knowledge_depth": 0,
                "topic_coverage": coverage,
                "remaining_topics_count": len(state.get("remaining_topics", [])),
                "current_topic": state.get("current_topic"),
                "strengths": [],
                "weaknesses": []
            },
            "covered_topics": state.get("covered_topics", [])
        })
        
        logger.info("Step 3: First question and initial metrics sent to client.")
        
        while not state.get("is_completed", False):
            # Receive Message
            message_data = await websocket.receive()
            
            # Use lock to ensure only one message is processed at a time
            async with turn_lock:
                message_start = time.time()
                answer_text = ""
                
                if "bytes" in message_data:
                    audio_bytes = message_data["bytes"]
                    logger.info(f"Audio received: {len(audio_bytes)} bytes")
                    await websocket.send_json({"type": "processing", "stage": "Transcribing your answer..."})
                    
                    # STT Timing
                    stt_start = time.time()
                    answer_text = await voice_service.transcribe_audio(audio_bytes)
                    stt_duration = time.time() - stt_start
                    logger.info(f"STT Complete: {stt_duration:.2f}s | Result: {answer_text[:50]}...")
                    
                    if not answer_text:
                        await websocket.send_json({"type": "error", "message": "Could not understand audio. Please try again or type your answer."})
                        continue
                    await websocket.send_json({"type": "transcript", "text": answer_text})
                
                elif "text" in message_data:
                    # Handle JSON Text Answer (Legacy/Chat support)
                    msg = json.loads(message_data["text"])
                    if msg["type"] == "answer":
                        answer_text = msg["text"]
                
                if answer_text:
                    # Reset turn-specific state to prevent bleeding
                    last_question = state["current_question"]
                    state["current_answer"] = answer_text
                    state["current_turn_eval"] = None 
                    state["duplicate_detected"] = False
                    
                    # 2. Run Evaluation + Next Step
                    await websocket.send_json({"type": "processing", "stage": "Analyzing your response..."})
                    logger.info(f"Orchestrator: Invoking graph for evaluation of Turn {state['turn_count'] + 1}...")
                    eval_start = time.time()
                    
                    try:
                        # CRITICAL: Re-invoke graph with updated state
                        state = await asyncio.wait_for(adaptive_interview_graph.ainvoke(state), timeout=25.0)
                        eval_duration = time.time() - eval_start
                        logger.info(f"Evaluation Complete: {eval_duration:.2f}s")
                    except asyncio.TimeoutError:
                        logger.error("Evaluation Timeout (25s)")
                        await websocket.send_json({"type": "processing", "stage": "Using fast scoring so the interview can continue..."})
                        fallback_eval = build_fallback_eval(
                            question=last_question,
                            answer=answer_text,
                            profile=state.get("candidate_profile") or {},
                            role=state.get("job_role") or ""
                        )
                        state["current_turn_eval"] = fallback_eval
                        state["answer_history"] = state.get("answer_history", []) + [{
                            "question": last_question,
                            "answer": answer_text,
                            "evaluation": fallback_eval
                        }]
                        state.update(plan_fallback_question(state))
                    
                    # Increment turn count after successful processing
                    state["turn_count"] += 1
                    if state["turn_count"] >= MAX_LIVE_TURNS:
                        state["is_completed"] = True
                        state["final_report"] = build_final_report(state)
                    
                    # Save turn data to DB
                    try:
                        turn_data = InterviewData(
                            id=uuid.uuid4(),
                            interview_id=interview.id,
                            question_text=last_question,
                            answer_transcript=answer_text
                        )
                        
                        eval_dict = state.get("current_turn_eval")
                        if eval_dict:
                            turn_data.technical_score = eval_dict.get("technical_score")
                            turn_data.communication_score = eval_dict.get("communication_score")
                            turn_data.feedback = eval_dict.get("reasoning")
                            turn_data.detailed_evaluation = eval_dict
                            
                            # Calculate coverage
                            total_topics = len(state.get("covered_topics", [])) + len(state.get("remaining_topics", []))
                            coverage = (len(state.get("covered_topics", [])) / total_topics * 100) if total_topics > 0 else 0

                            # Send live scores to frontend
                            await websocket.send_json({
                                "type": "live_scores",
                                "scores": {
                                    "technical_score": eval_dict.get("technical_score"),
                                    "communication_score": eval_dict.get("communication_score"),
                                    "confidence_score": eval_dict.get("confidence_score"),
                                    "knowledge_depth": eval_dict.get("knowledge_depth"),
                                    "topic_coverage": coverage,
                                    "remaining_topics_count": len(state.get("remaining_topics", [])),
                                    "current_topic": state.get("current_topic"),
                                    "strengths": eval_dict.get("strong_areas", []),
                                    "weaknesses": eval_dict.get("weak_areas", [])
                                },
                                "covered_topics": state.get("covered_topics", [])
                            })

                        db.add(turn_data)
                        db.commit()
                    except Exception as db_err:
                        logger.error(f"Failed to save turn data: {db_err}")

                    if state.get("is_completed"):
                        await websocket.send_json({
                            "type": "final_report", 
                            "report": state.get("final_report")
                        })
                        break
                    
                    # 3. Send Next Question + Audio
                    await websocket.send_json({"type": "processing", "stage": "Preparing next question..."})
                    next_q = state["current_question"]
                    
                    tts_start = time.time()
                    audio_bytes = await voice_service.text_to_speech(next_q)
                    tts_duration = time.time() - tts_start
                    logger.info(f"TTS Complete: {tts_duration:.2f}s")
                    
                    audio_base64 = base64.b64encode(audio_bytes).decode('utf-8') if audio_bytes else None

                    await websocket.send_json({
                        "type": "question", 
                        "text": next_q,
                        "audio": audio_base64
                    })
                    logger.info(f"Total Turn Duration: {time.time() - message_start:.2f}s")
                    
                    # Reset turn-specific input/output for next turn
                    state["current_answer"] = ""
                    state["current_turn_eval"] = None
                
    except WebSocketDisconnect:
        logger.info(f"Client disconnected from interview {interview_id}")
    except Exception as e:
        logger.error(f"Error in interview stream: {e}", exc_info=True)
        try:
            await websocket.send_json({"type": "error", "message": str(e)})
        except:
            pass
    finally:
        if state.get("is_completed"):
            interview.status = "completed"
            interview.transcript = state.get("full_transcript")
            if state.get("final_report"):
                interview.overall_score = state["final_report"].get("overall_score")
            db.commit()
            asyncio.create_task(analyze_interview_async(str(interview.id)))
        
        try:
            await websocket.close()
        except:
            pass
