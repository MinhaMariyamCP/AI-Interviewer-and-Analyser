from typing import List
from pydantic import BaseModel, Field
from langchain_openai import ChatOpenAI
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_core.messages import HumanMessage, SystemMessage
import os
import json
import logging
import re

logger = logging.getLogger(__name__)

# --- Output Schema ---

class JobPreference(BaseModel):
    role: str = Field(description="Recommended job title (e.g., Senior AI Engineer)")
    confidence: float = Field(description="Confidence score from 0-100")
    reasoning: str = Field(description="Brief explanation of why this role matches the resume")

class ResumeAnalysis(BaseModel):
    skills: List[str] = Field(description="Core hard skills and soft skills extracted from the resume")
    technologies: List[str] = Field(description="Specific tools, frameworks, and programming languages")
    experience_level: str = Field(description="Calculated seniority: Junior, Mid-level, Senior, or Lead")
    strengths: List[str] = Field(description="Top 3-5 unique value propositions")
    suggested_roles: List[JobPreference] = Field(description="At least 10 personalized job role recommendations")

# Rebuild models for Pydantic v2 compatibility
ResumeAnalysis.model_rebuild()

# --- Service Implementation ---

class ResumeAnalyzerService:
    def __init__(self, api_key: str = None):
        google_key = os.getenv("GOOGLE_API_KEY")
        openai_key = api_key or os.getenv("OPENAI_API_KEY")
        
        if google_key and google_key.startswith("AIzaSy"):
            logger.info("Using Google Gemini for ResumeAnalyzerService")
            self.llm = ChatGoogleGenerativeAI(
                model="gemini-1.5-flash",
                google_api_key=google_key,
                temperature=0
            )
        else:
            logger.info("Using OpenAI GPT for ResumeAnalyzerService")
            self.llm = ChatOpenAI(
                model="gpt-4o-mini",
                openai_api_key=openai_key,
                temperature=0
            )
        self.structured_llm = self.llm.with_structured_output(ResumeAnalysis)

    async def analyze(self, resume_json: dict) -> ResumeAnalysis:
        """
        Perform deep semantic analysis on resume data to generate job preferences.
        """
        prompt = f"""
        You are an expert technical recruiter. Analyze the following structured resume data.
        Your goal is to:
        1. Recommend 6 to 10 specific job roles that this candidate is qualified for.
        2. Every recommendation MUST be supported by explicit evidence from the resume: skills, projects, experience, education, or domain terms.
        3. Do NOT add generic software roles unless the resume clearly contains software engineering evidence.
        4. If the resume is non-technical, recommend domain-appropriate interview roles instead of forcing tech roles.
        5. In each reasoning field, cite the exact resume evidence that caused the match.
        
        Resume Data:
        {json.dumps(resume_json, indent=2)}
        """

        try:
            logger.info("Calling LLM for Resume Analysis")
            result = await self.structured_llm.ainvoke([
                SystemMessage(content="You are a highly accurate AI career recruiter. Generate personalized job matches."),
                HumanMessage(content=prompt)
            ])
            return result
            
        except Exception as e:
            logger.error(f"LLM Analysis failed: {str(e)}. Using rule-based fallback.")
            return self._rule_based_analysis(resume_json)

    def _resume_text(self, resume_json: dict) -> str:
        parts = []
        for key in ("skills", "technologies"):
            parts.extend(str(item) for item in resume_json.get(key) or [])
        for item in resume_json.get("experience") or []:
            if isinstance(item, dict):
                parts.extend([
                    str(item.get("role") or ""),
                    str(item.get("company") or ""),
                    " ".join(item.get("description") or []),
                ])
        for item in resume_json.get("projects") or []:
            if isinstance(item, dict):
                parts.extend([
                    str(item.get("name") or ""),
                    str(item.get("description") or ""),
                    " ".join(item.get("technologies") or []),
                ])
        for item in resume_json.get("education") or []:
            if isinstance(item, dict):
                parts.extend([str(item.get("degree") or ""), str(item.get("institution") or "")])
        return " ".join(parts).lower()

    def _add_role(self, roles: dict, role: str, confidence: float, reasoning: str) -> None:
        key = role.lower()
        item = JobPreference(role=role, confidence=confidence, reasoning=reasoning)
        if key not in roles or item.confidence > roles[key].confidence:
            roles[key] = item

    def _dominant_domain(self, text: str) -> str:
        domain_keywords = {
            "fitness": ["fitness", "trainer", "personal trainer", "workout", "nutrition", "coaching", "gym", "wellness"],
            "data": ["sql", "excel", "dashboard", "power bi", "tableau", "report", "metrics", "kpi", "analytics", "data analysis"],
            "software": ["python", "java", "react", "node", "api", "database", "software", "developer", "frontend", "backend", "typescript", "javascript"],
            "business": ["requirements", "stakeholder", "process", "documentation", "business analysis", "workflow", "operations"],
            "support": ["customer support", "technical support", "troubleshoot", "ticket", "service desk"],
            "sales": ["sales", "crm", "lead", "marketing", "campaign", "business development"],
            "devops": ["docker", "kubernetes", "aws", "azure", "gcp", "cloud", "ci/cd", "devops", "deployment"],
        }

        scores = {}
        for domain, keywords in domain_keywords.items():
            score = 0
            for keyword in keywords:
                pattern = r"(?<![a-z0-9])" + re.escape(keyword) + r"(?![a-z0-9])"
                score += len(re.findall(pattern, text))
            scores[domain] = score

        best_domain, best_score = max(scores.items(), key=lambda item: item[1])
        return best_domain if best_score > 0 else "general"

    def _filter_to_dominant_path(self, roles: List[JobPreference], text: str) -> List[JobPreference]:
        domain = self._dominant_domain(text)
        role_domains = {
            "Backend Software Engineer": "software",
            "Frontend Developer": "software",
            "Fullstack Developer": "software",
            "AI/ML Engineer": "software",
            "DevOps Engineer": "devops",
            "QA Automation Engineer": "software",
            "Data Analyst": "data",
            "Business Analyst": "business",
            "Support Engineer": "support",
            "Customer Success Specialist": "support",
            "Sales Engineer": "sales",
            "Operations Manager": "business",
            "Fitness Trainer": "fitness",
            "Wellness Program Coordinator": "fitness",
            "Client Wellness Coach": "fitness",
        }

        if domain == "general":
            return roles[:3]

        compatible = {
            "software": {"software", "devops", "data"},
            "data": {"data", "business"},
            "business": {"business", "data", "support"},
            "support": {"support", "business"},
            "sales": {"sales", "support", "business"},
            "fitness": {"fitness"},
            "devops": {"devops", "software"},
        }
        allowed = compatible.get(domain, {domain})
        filtered = [role for role in roles if role_domains.get(role.role) in allowed]
        return filtered[:4] if filtered else roles[:1]

    def _evidence_roles(self, resume_json: dict) -> List[JobPreference]:
        text = self._resume_text(resume_json)
        roles = {}

        def has(*keywords: str) -> bool:
            for keyword in keywords:
                pattern = r"(?<![a-z0-9])" + re.escape(keyword.lower()) + r"(?![a-z0-9])"
                if re.search(pattern, text):
                    return True
            return False

        backend_evidence = has("python", "fastapi", "django", "flask", "node", "backend", "postgres", "database", "server")
        frontend_evidence = has("react", "next", "frontend", "typescript", "javascript", "css", "html", "ui")

        if backend_evidence:
            self._add_role(roles, "Backend Software Engineer", 88, "Matched resume evidence for APIs, backend tools, databases, or server-side engineering.")
        if frontend_evidence:
            self._add_role(roles, "Frontend Developer", 86, "Matched resume evidence for frontend technologies or UI implementation.")
        if frontend_evidence and backend_evidence:
            self._add_role(roles, "Fullstack Developer", 84, "Matched resume evidence across both frontend and backend work.")
        if has("machine learning", "tensorflow", "pytorch", "model", "ml", "artificial intelligence", "data science"):
            self._add_role(roles, "AI/ML Engineer", 88, "Matched resume evidence for machine learning, AI models, or data science.")
        if has("sql", "excel", "dashboard", "power bi", "tableau", "report", "metrics", "kpi", "analytics", "data analysis"):
            self._add_role(roles, "Data Analyst", 88, "Matched resume evidence for reporting, dashboards, metrics, SQL, Excel, or analytics.")
        if has("requirements", "stakeholder", "process", "documentation", "business analysis", "client", "workflow"):
            self._add_role(roles, "Business Analyst", 86, "Matched resume evidence for requirements, stakeholders, process, documentation, or client work.")
        if has("docker", "kubernetes", "aws", "azure", "gcp", "cloud", "ci/cd", "devops", "deployment"):
            self._add_role(roles, "DevOps Engineer", 84, "Matched resume evidence for cloud, deployment, DevOps, or containerization.")
        if has("test", "testing", "qa", "automation", "selenium", "quality"):
            self._add_role(roles, "QA Automation Engineer", 80, "Matched resume evidence for testing, QA, or automation.")
        if has("customer", "support", "troubleshoot", "ticket", "service desk", "technical support"):
            self._add_role(roles, "Support Engineer", 82, "Matched resume evidence for troubleshooting, customer support, tickets, or service work.")
        if has("sales", "crm", "lead", "marketing", "campaign", "business development"):
            self._add_role(roles, "Sales Engineer", 76, "Matched resume evidence for sales, CRM, leads, marketing, or business development.")
        if has("operations", "coordination", "scheduling", "process improvement", "team management"):
            self._add_role(roles, "Operations Manager", 78, "Matched resume evidence for operations, coordination, process improvement, or team management.")
        if has("fitness", "trainer", "personal trainer", "training", "coaching", "nutrition", "workout"):
            self._add_role(roles, "Fitness Trainer", 90, "Matched resume evidence for fitness, coaching, training, nutrition, or client workout guidance.")
            self._add_role(roles, "Wellness Program Coordinator", 82, "Matched resume evidence for client training, wellness guidance, or program coordination.")

        sorted_roles = sorted(roles.values(), key=lambda item: item.confidence, reverse=True)
        return self._filter_to_dominant_path(sorted_roles, text)

    def _merge_with_evidence(self, resume_json: dict, llm_result: ResumeAnalysis) -> ResumeAnalysis:
        evidence_roles = self._evidence_roles(resume_json)
        if not evidence_roles:
            return self._rule_based_analysis(resume_json)

        role_map = {role.role.lower(): role for role in evidence_roles}
        evidence_text = self._resume_text(resume_json)
        generic_software_roles = ["software engineer", "fullstack developer", "frontend developer", "backend software engineer", "system architect"]
        has_software_evidence = any(term in evidence_text for term in ["python", "java", "react", "api", "database", "software", "developer", "frontend", "backend"])

        for role in llm_result.suggested_roles or []:
            key = role.role.lower()
            if key in role_map:
                continue
            if key in generic_software_roles and not has_software_evidence:
                continue
            if len(role_map) >= 8:
                break
            role_map[key] = JobPreference(
                role=role.role,
                confidence=min(float(role.confidence or 70), 76),
                reasoning=f"AI-supported match. {role.reasoning}"
            )

        return ResumeAnalysis(
            skills=llm_result.skills or resume_json.get("skills") or [],
            technologies=llm_result.technologies or resume_json.get("skills") or [],
            experience_level=llm_result.experience_level or "Mid-level",
            strengths=llm_result.strengths or ["Resume evidence matched to target roles"],
            suggested_roles=sorted(role_map.values(), key=lambda item: item.confidence, reverse=True)
        )

    def _rule_based_analysis(self, resume_json: dict) -> ResumeAnalysis:
        """
        Fallback logic to ensure the UI is populated even if AI APIs are down/unauthorized.
        """
        skills = resume_json.get("skills") or []
        skills_str = self._resume_text(resume_json)
        
        potential_roles = self._evidence_roles(resume_json)
        
        # Ensure we always have a broad interview catalogue for the UI requirement.
        generic_roles = []
        domain = self._dominant_domain(skills_str)
        if domain in {"software", "devops"} and any(kw in skills_str for kw in ["python", "java", "react", "software", "developer", "api", "database", "cloud", "docker"]):
            generic_roles.extend([
                ("Fullstack Developer", "Resume contains software or web-development evidence."),
                ("Junior Software Engineer", "Resume contains foundational software engineering evidence."),
                ("QA Automation Engineer", "Resume contains technical skills that can support software testing interviews."),
            ])
        if domain in {"data", "business"} and any(kw in skills_str for kw in ["analysis", "excel", "report", "dashboard", "business", "stakeholder", "process"]):
            generic_roles.extend([
                ("Data Analyst", "Resume contains analysis, reporting, dashboard, or metrics evidence."),
                ("Business Analyst", "Resume contains business, process, stakeholder, or documentation evidence."),
            ])
        if domain in {"support", "sales", "business"} and any(kw in skills_str for kw in ["customer", "support", "service", "client", "communication"]):
            generic_roles.append(("Customer Success Specialist", "Resume contains customer, client, service, or communication evidence."))
        if domain == "fitness" and any(kw in skills_str for kw in ["training", "trainer", "fitness", "coaching", "nutrition"]):
            generic_roles.extend([
                ("Fitness Trainer", "Resume contains training, coaching, fitness, or nutrition evidence."),
                ("Client Wellness Coach", "Resume contains client guidance or wellness coaching evidence."),
            ])
        
        while len(potential_roles) < 8 and generic_roles:
            role, reason = generic_roles.pop(0)
            if role.lower() not in {item.role.lower() for item in potential_roles}:
                potential_roles.append(JobPreference(role=role, confidence=64.0, reasoning=reason))

        if not potential_roles:
            potential_roles.append(JobPreference(
                role="General Interview Practice",
                confidence=50.0,
                reasoning="The parsed resume did not contain enough clear role evidence, so a custom role is recommended."
            ))

        return ResumeAnalysis(
            skills=skills,
            technologies=skills,
            experience_level="Mid-level",
            strengths=["Technically proficient", "Well-rounded candidate"],
            suggested_roles=potential_roles
        )
