import io
from datetime import datetime
from typing import List, Dict, Any, Optional
from reportlab.lib.pagesizes import letter
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, PageBreak
from reportlab.lib.units import inch
from pydantic import BaseModel
import os
import logging
from sqlalchemy.orm import Session
from db.models import Interview, InterviewData, User

logger = logging.getLogger(__name__)

# --- 1. Data Models for Report ---

class ReportData(BaseModel):
    candidate_name: str
    job_role: str
    overall_score: float
    technical_score: float
    communication_score: float
    behavioral_score: float
    strengths: List[str]
    weaknesses: List[str]
    recommendations: List[str]
    interview_date: str
    transcript_summary: List[Dict[str, str]]

# --- 2. Report Generation Logic ---

class PDFReportGenerator:
    def __init__(self):
        self.styles = getSampleStyleSheet()
        self.custom_styles = self._create_custom_styles()

    def _create_custom_styles(self):
        styles = {}
        styles['Title'] = ParagraphStyle(
            'ReportTitle',
            parent=self.styles['Heading1'],
            fontSize=24,
            textColor=colors.HexColor("#1E40AF"), 
            spaceAfter=20,
            alignment=1 
        )
        styles['SectionHeader'] = ParagraphStyle(
            'SectionHeader',
            parent=self.styles['Heading2'],
            fontSize=16,
            textColor=colors.HexColor("#1F2937"),
            spaceBefore=15,
            spaceAfter=10,
        )
        return styles

    def generate(self, data: ReportData) -> bytes:
        buffer = io.BytesIO()
        doc = SimpleDocTemplate(buffer, pagesize=letter, rightMargin=72, leftMargin=72, topMargin=72, bottomMargin=50)
        elements = []

        # --- Header Section ---
        elements.append(Paragraph("AI Interview Assessment Report", self.custom_styles['Title']))
        elements.append(Paragraph(f"<b>Candidate:</b> {data.candidate_name}", self.styles['Normal']))
        elements.append(Paragraph(f"<b>Target Role:</b> {data.job_role}", self.styles['Normal']))
        elements.append(Paragraph(f"<b>Date:</b> {data.interview_date}", self.styles['Normal']))
        elements.append(Spacer(1, 0.3 * inch))

        # --- Executive Summary Table ---
        elements.append(Paragraph("Executive Summary", self.custom_styles['SectionHeader']))
        
        score_data = [
            ['Dimension', 'Score'],
            ['Overall Proficiency', f"{data.overall_score:.1f}%"],
            ['Technical Depth', f"{data.technical_score:.1f}%"],
            ['Communication Skills', f"{data.communication_score:.1f}%"],
            ['Behavioral Alignment', f"{data.behavioral_score:.1f}%"]
        ]
        
        table = Table(score_data, colWidths=[3*inch, 2*inch])
        table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor("#EFF6FF")),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.HexColor("#1E40AF")),
            ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('GRID', (0, 0), (-1, -1), 1, colors.HexColor("#DBEAFE")),
            ('BOTTOMPADDING', (0, 0), (-1, 0), 10),
            ('TOPPADDING', (0, 1), (-1, -1), 8),
        ]))
        elements.append(table)
        elements.append(Spacer(1, 0.4 * inch))

        # --- Qualitative Analysis ---
        elements.append(Paragraph("Candidate Analysis", self.custom_styles['SectionHeader']))
        
        # Strengths
        elements.append(Paragraph("<b>Key Strengths:</b>", self.styles['Normal']))
        for s in data.strengths:
            elements.append(Paragraph(f"• {s}", self.styles['Normal']))
        elements.append(Spacer(1, 0.1 * inch))

        # Weaknesses
        elements.append(Paragraph("<b>Areas for Improvement:</b>", self.styles['Normal']))
        for w in data.weaknesses:
            elements.append(Paragraph(f"• {w}", self.styles['Normal']))
        elements.append(Spacer(1, 0.1 * inch))

        # Recommendations
        elements.append(Paragraph("<b>Hiring Recommendation:</b>", self.styles['Normal']))
        for r in data.recommendations:
            elements.append(Paragraph(f"• {r}", self.styles['Normal']))
        
        elements.append(PageBreak())

        # --- Interview Transcript Summary ---
        elements.append(Paragraph("Detailed Interview Log", self.custom_styles['SectionHeader']))
        for turn in data.transcript_summary:
            elements.append(Paragraph(f"<b>Q:</b> {turn['question']}", self.styles['Normal']))
            elements.append(Paragraph(f"<i>A:</i> {turn['answer']}", self.styles['Normal']))
            elements.append(Spacer(1, 0.15 * inch))

        doc.build(elements)
        pdf_bytes = buffer.getvalue()
        buffer.close()
        return pdf_bytes

async def get_report_data_from_db(interview_id: str, db: Session) -> Optional[ReportData]:
    """Aggregates real data from the database for a specific interview."""
    interview = db.query(Interview).filter(Interview.id == interview_id).first()
    if not interview:
        return None
        
    user = db.query(User).filter(User.id == interview.user_id).first()
    turns = db.query(InterviewData).filter(InterviewData.interview_id == interview_id).all()
    
    # Aggregate Scores
    tech_scores = [t.technical_score for t in turns if t.technical_score is not None]
    comm_scores = [t.communication_score for t in turns if t.communication_score is not None]
    
    avg_tech = sum(tech_scores) / len(tech_scores) if tech_scores else 0
    avg_comm = sum(comm_scores) / len(comm_scores) if comm_scores else 0
    
    # Extract Strengths/Weaknesses from detailed evaluations
    strengths = []
    weaknesses = []
    transcript_summary = []
    
    for t in turns:
        if t.detailed_evaluation:
            strengths.extend(t.detailed_evaluation.get("strengths", []))
            weaknesses.extend(t.detailed_evaluation.get("weaknesses", []))
        
        transcript_summary.append({
            "question": t.question_text,
            "answer": t.answer_transcript or "[No answer recorded]"
        })

    # Deduplicate and limit
    strengths = list(set(strengths))[:5]
    weaknesses = list(set(weaknesses))[:5]

    return ReportData(
        candidate_name=user.full_name if user else "Candidate",
        job_role=interview.job_role or "Software Engineer",
        overall_score=interview.overall_score or 0,
        technical_score=avg_tech,
        communication_score=avg_comm,
        behavioral_score=avg_tech, # Placeholder for behavioral specific agg
        strengths=strengths if strengths else ["Demonstrated core technical knowledge"],
        weaknesses=weaknesses if weaknesses else ["Could provide more specific examples in some areas"],
        recommendations=["Proceed to technical round" if (interview.overall_score or 0) > 70 else "Consider for junior roles"],
        interview_date=interview.created_at.strftime("%Y-%m-%d"),
        transcript_summary=transcript_summary
    )
