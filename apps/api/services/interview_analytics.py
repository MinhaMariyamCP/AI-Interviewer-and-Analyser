import io
import re
import uuid
import logging
from typing import Dict, List, Any
from xml.sax.saxutils import escape
from sqlalchemy.orm import Session
from reportlab.lib import colors
from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
from reportlab.lib.units import inch

from db.session import SessionLocal
from db.models import Interview, InterviewData, InterviewAnalytics, Resume

logger = logging.getLogger(__name__)

FILLER_WORDS = ["um", "uh", "like", "basically", "actually", "you know"]
TECH_CATEGORIES = ["architecture", "scalability", "optimization", "testing", "deployment", "debugging", "security", "databases"]
BEHAVIORAL_CATEGORIES = ["leadership", "teamwork", "ownership", "adaptability", "conflict_resolution", "communication"]
TOPIC_KEYWORDS = {
    "Python": ["python", "fastapi", "django", "flask", "pandas"],
    "Java": ["java", "spring", "jvm"],
    "Docker": ["docker", "container", "image", "compose", "kubernetes"],
    "System Design": ["architecture", "scale", "scalability", "load", "distributed", "cache"],
    "Databases": ["database", "sql", "postgres", "mysql", "redis", "query"],
    "Machine Learning": ["machine learning", "model", "ai", "ml", "training"],
    "Web Development": ["react", "next", "api", "frontend", "backend", "web"],
}


def clamp(value: float) -> float:
    return round(max(0, min(100, value)), 1)


def average(values: List[float], fallback: float = 0) -> float:
    values = [float(v) for v in values if v is not None]
    return clamp(sum(values) / len(values)) if values else fallback


def word_count(text: str) -> int:
    return len(re.findall(r"\b\w+\b", text or ""))


def score_from_keywords(answer: str, keywords: List[str], base: float = 45) -> float:
    text = (answer or "").lower()
    hits = sum(1 for keyword in keywords if keyword in text)
    return clamp(base + min(hits * 12, 45) + min(word_count(text) / 12, 10))


def extract_turn_eval(turn: InterviewData) -> Dict[str, Any]:
    data = turn.detailed_evaluation or {}
    return {
        "technical_score": data.get("technical_score", turn.technical_score or 0),
        "communication_score": data.get("communication_score", turn.communication_score or 0),
        "confidence_score": data.get("confidence_score", 0),
        "knowledge_depth": data.get("knowledge_depth", turn.depth_score or 0),
        "strong_areas": data.get("strong_areas") or data.get("strengths") or [],
        "weak_areas": data.get("weak_areas") or data.get("weaknesses") or [],
        "reasoning": data.get("reasoning") or turn.feedback or "",
    }


def analyze_fillers(turns: List[InterviewData]) -> Dict[str, Any]:
    text = " ".join((turn.answer_transcript or "").lower() for turn in turns)
    total_words = max(word_count(text), 1)
    counts = {}
    for filler in FILLER_WORDS:
        pattern = r"\b" + re.escape(filler) + r"\b"
        counts[filler] = len(re.findall(pattern, text))
    total = sum(counts.values())
    common = sorted(counts.items(), key=lambda item: item[1], reverse=True)
    return {
        "total_count": total,
        "frequency_per_100_words": round((total / total_words) * 100, 2),
        "most_common": [{"word": word, "count": count} for word, count in common if count > 0][:5],
        "recommendations": [
            "Pause silently before answering instead of using filler words.",
            "Structure answers in short points: context, decision, result.",
        ] if total else ["Filler word usage is low. Maintain the same speaking discipline."],
    }


def infer_topic(question: str, answer: str) -> str:
    text = f"{question} {answer}".lower()
    for topic, keywords in TOPIC_KEYWORDS.items():
        if any(keyword in text for keyword in keywords):
            return topic
    return "General Technical"


def build_strengths(turns: List[InterviewData]) -> List[Dict[str, Any]]:
    strengths = []
    for turn in turns:
        eval_data = extract_turn_eval(turn)
        for item in eval_data["strong_areas"][:2]:
            strengths.append({
                "title": str(item)[:80],
                "score": clamp(eval_data["technical_score"] or eval_data["communication_score"] or 65),
                "explanation": f"Demonstrated during the response to: {turn.question_text[:120]}",
                "evidence": (turn.answer_transcript or "")[:260],
            })
    if not strengths and turns:
        best = max(turns, key=lambda item: (item.technical_score or 0) + (item.communication_score or 0))
        strengths.append({
            "title": "Solid technical communication",
            "score": clamp((best.technical_score or 55) + 5),
            "explanation": "The answer showed enough structure and technical relevance to establish a positive signal.",
            "evidence": (best.answer_transcript or "")[:260],
        })
    return strengths[:6]


def build_weaknesses(turns: List[InterviewData]) -> List[Dict[str, Any]]:
    weaknesses = []
    for turn in turns:
        eval_data = extract_turn_eval(turn)
        for item in eval_data["weak_areas"][:2]:
            weaknesses.append({
                "severity": "high" if (eval_data["technical_score"] or 0) < 50 else "medium",
                "title": str(item)[:80],
                "explanation": eval_data["reasoning"][:220] or "The response can be improved with deeper detail.",
                "evidence": (turn.answer_transcript or "")[:260],
                "improvement_suggestion": "Add concrete examples, tradeoffs, and measurable outcomes.",
            })
    if not weaknesses and turns:
        weaknesses.append({
            "severity": "medium",
            "title": "Add more technical evidence",
            "explanation": "Some answers would be stronger with implementation details and alternatives considered.",
            "evidence": (turns[-1].answer_transcript or "")[:260],
            "improvement_suggestion": "Use the STAR format plus one technical tradeoff per answer.",
        })
    return weaknesses[:6]


def build_topic_scores(turns: List[InterviewData]) -> List[Dict[str, Any]]:
    grouped: Dict[str, List[InterviewData]] = {}
    for turn in turns:
        grouped.setdefault(infer_topic(turn.question_text, turn.answer_transcript or ""), []).append(turn)
    topics = []
    for topic, topic_turns in grouped.items():
        tech = average([turn.technical_score for turn in topic_turns], 55)
        depth = average([extract_turn_eval(turn)["knowledge_depth"] for turn in topic_turns], tech)
        comm = average([turn.communication_score for turn in topic_turns], 55)
        topics.append({
            "topic": topic,
            "topic_score": clamp((tech * 0.5) + (depth * 0.3) + (comm * 0.2)),
            "clarity_score": comm,
            "depth_score": depth,
            "explanation": f"Based on {len(topic_turns)} answer(s) that discussed {topic.lower()}.",
        })
    return sorted(topics, key=lambda item: item["topic_score"], reverse=True)


def build_question_analytics(turns: List[InterviewData]) -> Dict[str, Any]:
    items = []
    for index, turn in enumerate(turns, start=1):
        eval_data = extract_turn_eval(turn)
        technical = clamp(eval_data["technical_score"])
        communication = clamp(eval_data["communication_score"])
        confidence = clamp(eval_data["confidence_score"] or (communication + technical) / 2)
        clarity = clamp((communication * 0.7) + (confidence * 0.3))
        total = clamp((technical * 0.45) + (communication * 0.25) + (confidence * 0.15) + (clarity * 0.15))
        items.append({
            "index": index,
            "question": turn.question_text,
            "answer": turn.answer_transcript or "",
            "topic": infer_topic(turn.question_text, turn.answer_transcript or ""),
            "confidence_score": confidence,
            "clarity_score": clarity,
            "technical_score": technical,
            "communication_score": communication,
            "overall_score": total,
        })
    strongest = max(items, key=lambda item: item["overall_score"], default=None)
    weakest = min(items, key=lambda item: item["overall_score"], default=None)
    return {
        "items": items,
        "strongest_answer": strongest,
        "weakest_answer": weakest,
        "performance_timeline": [{"name": f"Q{item['index']}", "score": item["overall_score"]} for item in items],
    }


def generate_analytics_payload(interview: Interview, resume: Resume, turns: List[InterviewData]) -> Dict[str, Any]:
    evals = [extract_turn_eval(turn) for turn in turns]
    technical = average([item["technical_score"] for item in evals], interview.overall_score or 0)
    communication = average([item["communication_score"] for item in evals], 0)
    confidence = average([item["confidence_score"] for item in evals], communication)
    depth = average([item["knowledge_depth"] for item in evals], technical)
    problem_solving = clamp((technical * 0.45) + (depth * 0.35) + 10)
    clarity = clamp(communication + 2)
    professionalism = clamp((communication * 0.6) + (confidence * 0.4))
    overall = clamp((technical * 0.35) + (communication * 0.18) + (confidence * 0.12) + (problem_solving * 0.15) + (clarity * 0.1) + (professionalism * 0.1))

    question_analytics = build_question_analytics(turns)
    topics = build_topic_scores(turns)
    filler_words = analyze_fillers(turns)
    all_answers = " ".join(turn.answer_transcript or "" for turn in turns)

    technical_depth = [
        {"category": category.replace("_", " ").title(), "score": score_from_keywords(all_answers, [category], technical - 10)}
        for category in TECH_CATEGORIES
    ]
    behavioral = [
        {
            "category": category.replace("_", " ").title(),
            "score": score_from_keywords(all_answers, [category.replace("_", " ")], communication - 5),
            "explanation": f"Signal inferred from answers related to {category.replace('_', ' ')}.",
        }
        for category in BEHAVIORAL_CATEGORIES
    ]

    strengths = build_strengths(turns)
    weaknesses = build_weaknesses(turns)
    roadmap = [
        {
            "priority": index + 1,
            "skill_gap": weakness["title"],
            "explanation": weakness["explanation"],
            "recommended_action": weakness["improvement_suggestion"],
            "expected_impact": "Improves technical interview signal and answer credibility.",
        }
        for index, weakness in enumerate(weaknesses[:4])
    ]

    return {
        "status": "completed",
        "overall_scores": {
            "overall_score": overall,
            "technical_knowledge": technical,
            "communication": communication,
            "confidence": confidence,
            "problem_solving": problem_solving,
            "clarity": clarity,
            "professionalism": professionalism,
        },
        "strengths": strengths,
        "weaknesses": weaknesses,
        "confidence": {
            "confidence_score": confidence,
            "confidence_trend": [{"name": f"Q{i + 1}", "score": item["confidence_score"]} for i, item in enumerate(question_analytics["items"])],
            "confidence_strengths": ["Consistent answers" if confidence >= 65 else "Completed the interview flow"],
            "confidence_weaknesses": ["Add more decisive language and complete examples"] if confidence < 70 else [],
        },
        "concept_clarity": topics,
        "communication": {
            "communication_score": communication,
            "strengths": [s["title"] for s in strengths if s["score"] >= 60][:3],
            "weaknesses": [w["title"] for w in weaknesses][:3],
            "organization": clarity,
            "conciseness": clamp(100 - max(0, average([word_count(t.answer_transcript or "") for t in turns], 0) - 120) / 2),
            "verbosity": clamp(average([word_count(t.answer_transcript or "") for t in turns], 0)),
        },
        "filler_words": filler_words,
        "technical_depth": technical_depth,
        "behavioral": behavioral,
        "question_analytics": question_analytics,
        "improvement_roadmap": roadmap,
        "charts": {
            "radar": [
                {"metric": "Technical", "score": technical},
                {"metric": "Communication", "score": communication},
                {"metric": "Confidence", "score": confidence},
                {"metric": "Problem Solving", "score": problem_solving},
                {"metric": "Clarity", "score": clarity},
                {"metric": "Professionalism", "score": professionalism},
            ],
            "topic_bars": topics,
            "timeline": question_analytics["performance_timeline"],
            "confidence_trend": [{"name": f"Q{i + 1}", "score": item["confidence_score"]} for i, item in enumerate(question_analytics["items"])],
            "technical_depth": technical_depth,
            "behavioral": behavioral,
        },
        "executive_summary": f"{interview.job_role or 'Technical'} interview completed with an overall intelligence score of {overall}%.",
    }


def analyze_interview(interview_id: str, db: Session) -> InterviewAnalytics:
    interview_uuid = uuid.UUID(str(interview_id))
    interview = db.query(Interview).filter(Interview.id == interview_uuid).first()
    if not interview:
        raise ValueError("Interview not found")

    existing = db.query(InterviewAnalytics).filter(InterviewAnalytics.interview_id == interview_uuid).first()
    if existing and existing.status == "completed":
        return existing

    analytics = existing or InterviewAnalytics(interview_id=interview_uuid, status="pending")
    if not existing:
        db.add(analytics)
        db.commit()
        db.refresh(analytics)

    turns = db.query(InterviewData).filter(InterviewData.interview_id == interview_uuid).all()
    resume = db.query(Resume).filter(Resume.id == interview.resume_id).first()
    payload = generate_analytics_payload(interview, resume, turns)

    analytics.status = payload["status"]
    analytics.overall_scores = payload["overall_scores"]
    analytics.strengths = payload["strengths"]
    analytics.weaknesses = payload["weaknesses"]
    analytics.confidence = payload["confidence"]
    analytics.concept_clarity = payload["concept_clarity"]
    analytics.communication = payload["communication"]
    analytics.filler_words = payload["filler_words"]
    analytics.technical_depth = payload["technical_depth"]
    analytics.behavioral = payload["behavioral"]
    analytics.question_analytics = payload["question_analytics"]
    analytics.improvement_roadmap = payload["improvement_roadmap"]
    analytics.charts = payload["charts"]
    analytics.executive_summary = payload["executive_summary"]
    interview.overall_score = payload["overall_scores"]["overall_score"]
    db.commit()
    db.refresh(analytics)
    return analytics


async def analyze_interview_async(interview_id: str) -> None:
    db = SessionLocal()
    try:
        analyze_interview(interview_id, db)
    except Exception as exc:
        logger.error("Failed to generate interview analytics for %s: %s", interview_id, exc, exc_info=True)
    finally:
        db.close()


def serialize_analytics(analytics: InterviewAnalytics) -> Dict[str, Any]:
    return {
        "id": str(analytics.id),
        "interview_id": str(analytics.interview_id),
        "status": analytics.status,
        "overall_scores": analytics.overall_scores or {},
        "strengths": analytics.strengths or [],
        "weaknesses": analytics.weaknesses or [],
        "confidence": analytics.confidence or {},
        "concept_clarity": analytics.concept_clarity or [],
        "communication": analytics.communication or {},
        "filler_words": analytics.filler_words or {},
        "technical_depth": analytics.technical_depth or [],
        "behavioral": analytics.behavioral or [],
        "question_analytics": analytics.question_analytics or {},
        "improvement_roadmap": analytics.improvement_roadmap or [],
        "charts": analytics.charts or {},
        "executive_summary": analytics.executive_summary,
        "created_at": analytics.created_at.isoformat() if analytics.created_at else None,
        "updated_at": analytics.updated_at.isoformat() if analytics.updated_at else None,
    }


def generate_analytics_pdf(analytics: InterviewAnalytics, interview: Interview) -> bytes:
    data = serialize_analytics(analytics)
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=letter, rightMargin=60, leftMargin=60, topMargin=60, bottomMargin=50)
    styles = getSampleStyleSheet()
    title = ParagraphStyle("AnalyticsTitle", parent=styles["Heading1"], fontSize=22, textColor=colors.HexColor("#1D4ED8"), alignment=1)
    section = ParagraphStyle("Section", parent=styles["Heading2"], fontSize=14, textColor=colors.HexColor("#111827"), spaceBefore=14)
    story = [
        Paragraph("Interview Intelligence Report", title),
        Spacer(1, 0.2 * inch),
        Paragraph(f"<b>Role:</b> {escape(str(interview.job_role or 'Technical Interview'))}", styles["Normal"]),
        Paragraph(f"<b>Summary:</b> {escape(str(data.get('executive_summary') or 'Analytics generated.'))}", styles["Normal"]),
        Spacer(1, 0.25 * inch),
    ]

    scores = data["overall_scores"]
    score_rows = [["Metric", "Score"]] + [[key.replace("_", " ").title(), f"{value}%"] for key, value in scores.items()]
    table = Table(score_rows, colWidths=[3.5 * inch, 1.5 * inch])
    table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#DBEAFE")),
        ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#CBD5E1")),
        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
        ("ALIGN", (1, 1), (1, -1), "CENTER"),
    ]))
    story.append(Paragraph("Overall Scores", section))
    story.append(table)

    for label, items, field in [
        ("Strengths", data["strengths"], "explanation"),
        ("Weaknesses", data["weaknesses"], "improvement_suggestion"),
        ("Improvement Roadmap", data["improvement_roadmap"], "recommended_action"),
    ]:
        story.append(Paragraph(label, section))
        for item in items[:6]:
            title_text = item.get("title") or item.get("skill_gap") or item.get("severity") or label
            body_text = item.get(field) or item.get("explanation") or ""
            story.append(Paragraph(f"<b>{escape(str(title_text))}</b>: {escape(str(body_text))}", styles["Normal"]))

    story.append(Paragraph("Topic Analysis", section))
    for topic in data["concept_clarity"][:8]:
        story.append(Paragraph(
            f"<b>{escape(str(topic['topic']))}</b>: {escape(str(topic['topic_score']))}% - {escape(str(topic['explanation']))}",
            styles["Normal"]
        ))

    doc.build(story)
    pdf = buffer.getvalue()
    buffer.close()
    return pdf
