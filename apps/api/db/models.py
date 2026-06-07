from sqlalchemy import Column, String, Float, DateTime, JSON, ForeignKey
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.dialects.postgresql import UUID
import uuid
import datetime

Base = declarative_base()

class User(Base):
    __tablename__ = "users"
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    email = Column(String, unique=True, nullable=False)
    password_hash = Column(String, nullable=False)
    full_name = Column(String)
    role = Column(String, default="candidate")

class Resume(Base):
    __tablename__ = "resumes"
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"))
    file_url = Column(String, nullable=False)
    parsed_content = Column(JSON)
    analysis_result = Column(JSON)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)

class Interview(Base):
    __tablename__ = "interviews"
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"))
    resume_id = Column(UUID(as_uuid=True), ForeignKey("resumes.id"))
    job_role = Column(String)
    status = Column(String, default="pending")
    overall_score = Column(Float)
    overall_feedback = Column(String)
    report_url = Column(String)
    transcript = Column(JSON)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)

class InterviewData(Base):
    __tablename__ = "interview_data"
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    interview_id = Column(UUID(as_uuid=True), ForeignKey("interviews.id"))
    question_text = Column(String, nullable=False)
    answer_transcript = Column(String)
    
    # Technical Scores
    technical_score = Column(Float)
    correctness_score = Column(Float)
    depth_score = Column(Float)
    examples_score = Column(Float)
    tradeoffs_score = Column(Float)
    
    # Communication Scores
    communication_score = Column(Float)
    
    feedback = Column(String)
    detailed_evaluation = Column(JSON)

class InterviewAnalytics(Base):
    __tablename__ = "interview_analytics"
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    interview_id = Column(UUID(as_uuid=True), ForeignKey("interviews.id"), unique=True, nullable=False)
    status = Column(String, default="pending")
    overall_scores = Column(JSON)
    strengths = Column(JSON)
    weaknesses = Column(JSON)
    confidence = Column(JSON)
    concept_clarity = Column(JSON)
    communication = Column(JSON)
    filler_words = Column(JSON)
    technical_depth = Column(JSON)
    behavioral = Column(JSON)
    question_analytics = Column(JSON)
    improvement_roadmap = Column(JSON)
    charts = Column(JSON)
    executive_summary = Column(String)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.datetime.utcnow, onupdate=datetime.datetime.utcnow)

class VoiceInterviewProfile(Base):
    __tablename__ = "voice_interview_profiles"
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"))
    status = Column(String, default="completed")
    candidate_profile = Column(JSON)
    recommended_roles = Column(JSON)
    transcript = Column(JSON)
    overall_score = Column(Float)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)
