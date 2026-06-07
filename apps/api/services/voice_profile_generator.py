import json
import logging
import os
import re
from typing import Any, Dict, List

from langchain_core.messages import HumanMessage, SystemMessage
from langchain_openai import ChatOpenAI

from services.resume_analyzer import ResumeAnalyzerService

logger = logging.getLogger(__name__)


INTERVIEW_PROFILE_SYSTEM_PROMPT = """
You are a professional AI career profile analyst.
Convert a voice interview transcript into structured candidate data.
Return strict JSON only with these keys:
name, education, degree, graduation_year, skills, certifications, experience, projects, career_interests.
Use arrays for skills, certifications, experience, projects, and career_interests.
Do not invent details. If unknown, use an empty string or empty array.
"""


class VoiceInterviewProfileGenerator:
    def __init__(self):
        self.analyzer = ResumeAnalyzerService()
        api_key = os.getenv("OPENAI_API_KEY")
        self.llm = None
        if api_key and api_key.startswith("sk-"):
            self.llm = ChatOpenAI(model="gpt-4o-mini", temperature=0.1)

    async def generate(self, transcript: List[Dict[str, Any]]) -> Dict[str, Any]:
        profile = await self._llm_profile(transcript)
        if not profile:
            profile = self._fallback_profile(transcript)

        resume_like = {
            "skills": profile.get("skills", []),
            "technologies": profile.get("skills", []),
            "certifications": profile.get("certifications", []),
            "coursework": [],
            "projects": profile.get("projects", []),
            "experience": profile.get("experience", []),
            "education": profile.get("education") or profile.get("degree"),
            "education_level": profile.get("degree") or profile.get("education"),
            "past_job_titles": profile.get("career_interests", []),
            "years_of_experience": self._experience_hint(profile),
        }
        analysis = await self.analyzer.analyze(resume_like)
        roles = [
            {
                "role": role.role,
                "confidence": role.confidence,
                "reason": role.reasoning,
                "supporting_skills": role.supporting_skills,
                "missing_skills": role.missing_skills,
                "domain": role.domain,
            }
            for role in analysis.recommended_roles[:3]
        ]

        return {
            "candidate_profile": profile,
            "recommended_roles": roles,
            "all_suggested_roles": [
                {
                    "role": role.role,
                    "confidence": role.confidence,
                    "reason": role.reasoning,
                    "supporting_skills": role.supporting_skills,
                    "missing_skills": role.missing_skills,
                    "domain": role.domain,
                }
                for role in analysis.suggested_roles
            ],
            "overall_score": self._overall_score(roles),
        }

    async def _llm_profile(self, transcript: List[Dict[str, Any]]) -> Dict[str, Any]:
        if not self.llm:
            return {}

        transcript_text = self._transcript_text(transcript)
        try:
            response = await self.llm.ainvoke([
                SystemMessage(content=INTERVIEW_PROFILE_SYSTEM_PROMPT),
                HumanMessage(content=f"Voice interview transcript:\n{transcript_text}"),
            ])
            content = response.content.strip()
            if content.startswith("```"):
                content = re.sub(r"^```(?:json)?|```$", "", content, flags=re.MULTILINE).strip()
            data = json.loads(content)
            return self._normalize_profile(data)
        except Exception as exc:
            logger.warning("LLM voice profile generation failed, using fallback: %s", exc)
            return {}

    def _fallback_profile(self, transcript: List[Dict[str, Any]]) -> Dict[str, Any]:
        text = self._user_text(transcript)
        lower = text.lower()
        skills_catalog = [
            "python", "java", "javascript", "typescript", "react", "next.js", "node.js", "fastapi",
            "django", "express", "mongodb", "postgresql", "sql", "mysql", "docker", "kubernetes",
            "aws", "azure", "gcp", "machine learning", "deep learning", "tensorflow", "pytorch",
            "scikit-learn", "pandas", "numpy", "power bi", "tableau", "excel", "flutter",
            "react native", "cybersecurity", "linux", "git", "github", "openai", "gemini", "llm",
        ]
        interests_catalog = [
            "frontend", "backend", "full stack", "ai", "machine learning", "data science",
            "data analytics", "devops", "cloud", "cybersecurity", "mobile",
        ]

        name_match = re.search(r"(?:my name is|i am|i'm)\s+([a-z][a-z\s]{1,40})", lower)
        grad_match = re.search(r"(20\d{2})", text)

        return self._normalize_profile({
            "name": name_match.group(1).title().strip() if name_match else "",
            "education": self._sentence_after(lower, ["education", "studying", "degree"]) or "",
            "degree": self._degree(text),
            "graduation_year": grad_match.group(1) if grad_match else "",
            "skills": [skill.title() for skill in skills_catalog if skill in lower],
            "certifications": self._phrases_near(text, ["certification", "certified", "course"]),
            "experience": self._phrases_near(text, ["internship", "experience", "worked", "leadership"]),
            "projects": self._phrases_near(text, ["project", "built", "developed", "created"]),
            "career_interests": [item.title() for item in interests_catalog if item in lower],
        })

    def _normalize_profile(self, data: Dict[str, Any]) -> Dict[str, Any]:
        return {
            "name": str(data.get("name") or "").strip(),
            "education": str(data.get("education") or "").strip(),
            "degree": str(data.get("degree") or "").strip(),
            "graduation_year": str(data.get("graduation_year") or "").strip(),
            "skills": self._as_list(data.get("skills")),
            "certifications": self._as_list(data.get("certifications")),
            "experience": self._as_list(data.get("experience")),
            "projects": self._as_list(data.get("projects")),
            "career_interests": self._as_list(data.get("career_interests")),
        }

    def _transcript_text(self, transcript: List[Dict[str, Any]]) -> str:
        lines = []
        for item in transcript:
            role = str(item.get("role") or "speaker")
            content = str(item.get("content") or item.get("transcript") or "")
            if content.strip():
                lines.append(f"{role}: {content.strip()}")
        return "\n".join(lines)

    def _user_text(self, transcript: List[Dict[str, Any]]) -> str:
        lines = []
        for item in transcript:
            role = str(item.get("role") or "").lower()
            content = str(item.get("content") or item.get("transcript") or "")
            if role in {"user", "candidate"} and content.strip():
                lines.append(content.strip())
        return "\n".join(lines)

    def _as_list(self, value: Any) -> List[str]:
        if isinstance(value, list):
            items = value
        elif value:
            items = [value]
        else:
            items = []
        result = []
        seen = set()
        for item in items:
            text = str(item).strip()
            key = text.lower()
            if text and key not in seen:
                seen.add(key)
                result.append(text)
        return result

    def _sentence_after(self, text: str, markers: List[str]) -> str:
        sentences = re.split(r"[.\n]", text)
        for sentence in sentences:
            if any(marker in sentence for marker in markers):
                return sentence.strip().capitalize()
        return ""

    def _phrases_near(self, text: str, markers: List[str]) -> List[str]:
        sentences = re.split(r"[.\n]", text)
        matches = []
        for sentence in sentences:
            clean = sentence.strip()
            if clean and any(marker in clean.lower() for marker in markers):
                matches.append(clean[:220])
        return self._as_list(matches)[:6]

    def _degree(self, text: str) -> str:
        match = re.search(r"\b(b\.?tech|bachelor'?s?|master'?s?|m\.?tech|bca|mca|mba|phd)\b[^.\n,]*", text, re.I)
        return match.group(0).strip() if match else ""

    def _experience_hint(self, profile: Dict[str, Any]) -> str:
        experience_count = len(profile.get("experience") or [])
        if experience_count >= 3:
            return "2"
        if experience_count:
            return "1"
        return "0"

    def _overall_score(self, roles: List[Dict[str, Any]]) -> float:
        if not roles:
            return 0.0
        return round(sum(float(role.get("confidence") or 0) for role in roles) / len(roles), 1)
