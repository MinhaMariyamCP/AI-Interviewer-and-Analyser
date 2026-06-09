from typing import Dict, List, Optional, Set
from pydantic import BaseModel, Field
from langchain_openai import ChatOpenAI
from langchain_core.messages import HumanMessage, SystemMessage
import os
import json
import logging
import re

logger = logging.getLogger(__name__)

# --- Output Schema ---

class JobPreference(BaseModel):
    role: Optional[str] = Field(default="", description="Recommended job title (e.g., Senior AI Engineer)")
    confidence: Optional[float] = Field(default=0.0, description="Confidence score from 0-100")
    reasoning: Optional[str] = Field(default="", description="Brief explanation of why this role matches the resume")
    supporting_skills: List[str] = Field(default_factory=list, description="Resume skills that support this recommendation")
    missing_skills: List[str] = Field(default_factory=list, description="Skills to add to become more competitive")
    domain: Optional[str] = Field(default="", description="Career domain for deduplication and grouping")

class CandidateSkillProfile(BaseModel):
    skills: List[str] = Field(default_factory=list)
    technologies: List[str] = Field(default_factory=list)
    certifications: List[str] = Field(default_factory=list)
    coursework: List[str] = Field(default_factory=list)
    projects: List[str] = Field(default_factory=list)
    experience_years: Optional[str] = "Not specified"
    education: Optional[str] = "Not specified"
    past_job_titles: List[str] = Field(default_factory=list)

class ResumeAnalysis(BaseModel):
    skills: List[str] = Field(default_factory=list, description="Core hard skills and soft skills extracted from the resume")
    technologies: List[str] = Field(default_factory=list, description="Specific tools, frameworks, and programming languages")
    experience_level: Optional[str] = Field(default="Mid-level", description="Calculated seniority: Junior, Mid-level, Senior, or Lead")
    strengths: List[str] = Field(default_factory=list, description="Top 3-5 unique value propositions")
    candidate_profile: CandidateSkillProfile = Field(default_factory=CandidateSkillProfile)
    recommended_roles: List[JobPreference] = Field(default_factory=list, description="Top 3 strongest role recommendations")
    suggested_roles: List[JobPreference] = Field(default_factory=list, description="5 to 8 personalized, distinct internship role recommendations")

# Rebuild models for Pydantic v2 compatibility
ResumeAnalysis.model_rebuild()

# --- Service Implementation ---

class ResumeAnalyzerService:
    def __init__(self, api_key: str = None):
        openai_key = api_key or os.getenv("OPENAI_API_KEY")
        
        openai_is_valid = openai_key and openai_key.startswith("sk-") and len(openai_key) > 20
        
        if openai_is_valid:
            logger.info("Using OpenAI GPT-4o-Mini for ResumeAnalyzerService")
            self.llm = ChatOpenAI(
                model="gpt-4o-mini",
                openai_api_key=openai_key,
                temperature=0
            )
        else:
            logger.warning("No valid OpenAI API key found. Defaulting to OpenAI GPT-4o-Mini constructor (may fail).")
            self.llm = ChatOpenAI(
                model="gpt-4o-mini",
                openai_api_key=openai_key or "dummy-key",
                temperature=0
            )
        self.structured_llm = self.llm.with_structured_output(ResumeAnalysis)

    async def analyze(self, resume_json: dict) -> ResumeAnalysis:
        """
        Perform deep semantic analysis on resume data to generate job preferences.
        """
        return self._weighted_role_analysis(resume_json)

        prompt = f"""
        You are an expert technical recruiter. Given a candidate's resume, which includes their skills, experience, education, and certifications, classify the top job roles most aligned with their profile. 
        Ensure distinct differentiation by capturing key role-specific skills, tools, and responsibilities. Avoid overly broad classifications—focus on precise job titles.
        
        Your goal is to:
        1. Recommend 6 to 10 specific job roles that this candidate is qualified for, with the top, most-aligned role ranked first.
        2. Every recommendation MUST be supported by explicit evidence from the resume: skills, projects, experience, education, or domain terms.
        3. Do NOT add generic software roles unless the resume clearly contains software engineering evidence.
        4. If the resume is non-technical, recommend domain-appropriate interview roles instead of forcing tech roles.
        5. In each reasoning field, cite the exact resume evidence that caused the match.
        
        Resume Data:
        {json.dumps(resume_json, indent=2)}
        """

        openai_key = os.getenv("OPENAI_API_KEY")
        openai_is_valid = openai_key and openai_key.startswith("sk-") and len(openai_key) > 20

        if openai_is_valid:
            try:
                logger.info("Calling OpenAI (GPT-4o-Mini) for Resume Analysis")
                result = await self.structured_llm.ainvoke([
                    SystemMessage(content="You are a highly accurate AI career recruiter. Generate personalized job matches."),
                    HumanMessage(content=prompt)
                ])
                return result
            except Exception as openai_err:
                logger.error(f"OpenAI analysis failed: {openai_err}. Using rule-based fallback.")
                return self._rule_based_analysis(resume_json)
        else:
            logger.info("No valid OpenAI API key found. Using rule-based fallback.")
            return self._rule_based_analysis(resume_json)

    def _resume_text(self, resume_json: dict) -> str:
        parts = []
        for key in ("skills", "technologies", "certifications", "past_job_titles", "coursework", "courses"):
            parts.extend(str(item) for item in resume_json.get(key) or [])
        parts.append(str(resume_json.get("education_level") or ""))
        parts.append(str(resume_json.get("education") or ""))
        parts.append(str(resume_json.get("years_of_experience") or ""))
        for item in resume_json.get("projects") or []:
            if isinstance(item, dict):
                parts.extend([
                    str(item.get("name") or ""),
                    str(item.get("description") or ""),
                    " ".join(str(t) for t in item.get("technologies") or []),
                ])
            else:
                parts.append(str(item))
        for item in resume_json.get("experience") or []:
            if isinstance(item, dict):
                parts.extend([
                    str(item.get("role") or ""),
                    str(item.get("company") or ""),
                    " ".join(str(d) for d in item.get("description") or []),
                ])
            else:
                parts.append(str(item))
        return " ".join(parts).lower()

    def _as_list(self, value) -> List[str]:
        if isinstance(value, list):
            items = value
        elif value:
            items = [value]
        else:
            items = []
        return [str(item).strip() for item in items if str(item).strip()]

    def _candidate_profile(self, resume_json: dict) -> CandidateSkillProfile:
        projects = []
        for item in resume_json.get("projects") or []:
            if isinstance(item, dict):
                text = " ".join([
                    str(item.get("name") or ""),
                    str(item.get("description") or ""),
                    " ".join(str(t) for t in item.get("technologies") or []),
                ]).strip()
                if text:
                    projects.append(text)
            elif str(item).strip():
                projects.append(str(item).strip())

        return CandidateSkillProfile(
            skills=self._as_list(resume_json.get("skills")),
            technologies=self._as_list(resume_json.get("technologies")),
            certifications=self._as_list(resume_json.get("certifications")),
            coursework=self._as_list(resume_json.get("coursework") or resume_json.get("courses")),
            projects=projects,
            experience_years=str(resume_json.get("years_of_experience") or "Not specified"),
            education=str(resume_json.get("education_level") or resume_json.get("education") or "Not specified"),
            past_job_titles=self._as_list(resume_json.get("past_job_titles")),
        )

    def _keyword_hits(self, text: str, keywords: List[str]) -> List[str]:
        hits = []
        for keyword in keywords:
            pattern = r"(?<![a-z0-9])" + re.escape(keyword.lower()) + r"(?![a-z0-9])"
            if re.search(pattern, text):
                hits.append(keyword)
        return hits

    def _project_depth_score(self, resume_json: dict) -> int:
        projects = resume_json.get("projects") or []
        experience = resume_json.get("experience") or []
        text = self._resume_text(resume_json)
        project_count = len(projects)
        exp_count = len(experience)
        tech_density = len(self._keyword_hits(text, ["python", "react", "fastapi", "docker", "aws", "tensorflow", "pytorch", "sql", "api", "model", "deployment"]))
        return min(18, project_count * 3 + exp_count * 2 + tech_density)

    def _dynamic_role_candidates(self, resume_json: dict) -> List[Dict]:
        profile = self._candidate_profile(resume_json)
        text = self._resume_text(resume_json)
        project_text = " ".join(profile.projects).lower()
        tech_terms = self._dedupe(profile.skills + profile.technologies)

        ai_terms = self._keyword_hits(text, ["machine learning", "ml", "tensorflow", "pytorch", "llm", "nlp", "ai", "model", "deep learning", "classification", "prediction", "chatbot"])
        frontend_terms = self._keyword_hits(text, ["react", "next.js", "typescript", "javascript", "html", "css", "frontend", "ui", "tailwind"])
        backend_terms = self._keyword_hits(text, ["python", "fastapi", "django", "flask", "node.js", "express", "api", "database", "postgres", "mongodb", "sql", "server"])
        analytics_terms = self._keyword_hits(text, ["analytics", "dashboard", "power bi", "tableau", "excel", "sql", "report", "kpi", "metrics"])
        devops_terms = self._keyword_hits(text, ["docker", "kubernetes", "aws", "azure", "gcp", "ci/cd", "terraform", "devops", "deployment", "cloud"])
        security_terms = self._keyword_hits(text, ["security", "owasp", "vulnerability", "authentication", "encryption", "penetration", "cyber"])

        project_depth = self._project_depth_score(resume_json)

        candidates = []

        def add_candidate(role: str, domain: str, evidence: List[str], missing: List[str], reason: str, base_score: int):
            score = base_score + project_depth + (len(evidence) * 3) + (1 if "engineer" in role.lower() else 0)
            if not evidence:
                return
            if role.lower() in {item["role"].lower() for item in candidates}:
                return
            confidence = max(35, min(96, round(45 + score * 1.1 - (len(candidates) * 1.6))))
            if len(evidence) < 2:
                confidence -= 7
            if "project" not in " ".join(evidence).lower():
                confidence -= 3
            if (domain in {"ai_ml", "fullstack"} and project_depth < 6) or (domain == "analytics" and len(analytics_terms) < 2):
                confidence -= 4
            candidates.append({
                "role": role,
                "domain": domain,
                "score": score,
                "confidence": max(35, confidence),
                "evidence": self._dedupe(evidence)[:6],
                "missing": missing[:3],
                "reason": reason,
            })

        if ai_terms:
            add_candidate(
                "Machine Learning Engineer",
                "ai_ml",
                self._dedupe(ai_terms + [item for item in tech_terms if item.lower() in {"python", "tensorflow", "pytorch", "scikit-learn", "langchain", "openai", "gemini"}] + self._keyword_hits(project_text, ["model", "deployment", "chatbot", "classification", "prediction"]))[:8],
                ["MLOps", "Model Deployment", "Deep Learning Optimization"],
                f"The resume shows applied AI/ML work through {', '.join(ai_terms[:4])} and project evidence that matches machine-learning delivery.",
                26,
            )
        if frontend_terms and backend_terms:
            add_candidate(
                "Full-Stack Engineer",
                "fullstack",
                self._dedupe(frontend_terms + backend_terms + self._keyword_hits(project_text, ["api", "frontend", "backend", "web app", "dashboard"]))[:8],
                ["System Design", "End-to-End Testing", "Cloud Deployment"],
                "The profile combines front-end implementation and backend/API work, which is a strong signal for full-stack delivery.",
                24,
            )
        if frontend_terms:
            add_candidate(
                "Frontend Engineer",
                "frontend",
                self._dedupe(frontend_terms + self._keyword_hits(project_text, ["ui", "dashboard", "web app", "frontend"]))[:8],
                ["Accessibility", "Design Systems", "Testing"],
                "UI and web-interface evidence is strong across the resume and project descriptions.",
                18,
            )
        if backend_terms:
            add_candidate(
                "Backend Engineer",
                "backend",
                self._dedupe(backend_terms + self._keyword_hits(project_text, ["api", "server", "database", "auth"]))[:8],
                ["API Scaling", "Database Optimization", "Security Hardening"],
                "The resume demonstrates backend implementation, APIs, data handling, and service-layer development.",
                20,
            )
        if analytics_terms:
            add_candidate(
                "Data Analyst",
                "analytics",
                self._dedupe(analytics_terms + self._keyword_hits(project_text, ["dashboard", "metrics", "report", "analysis"]))[:8],
                ["Advanced SQL", "Statistical Modeling", "Stakeholder Storytelling"],
                "Analytics, dashboards, and reporting evidence align with data-focused roles.",
                18,
            )
        if devops_terms:
            add_candidate(
                "DevOps / Cloud Engineer",
                "devops",
                self._dedupe(devops_terms + self._keyword_hits(project_text, ["deployment", "pipeline", "container", "cloud"]))[:8],
                ["CI/CD Automation", "Infrastructure as Code", "Monitoring"],
                "Deployment, cloud tooling, and containerization are clearly present in the profile.",
                18,
            )
        if security_terms:
            add_candidate(
                "Security Engineer",
                "security",
                self._dedupe(security_terms + self._keyword_hits(project_text, ["auth", "secure", "encryption", "vulnerability"]))[:8],
                ["Threat Modeling", "Secure Coding", "OWASP Review"],
                "Security-focused skills and implementation evidence suggest a security-oriented profile.",
                16,
            )

        if not candidates:
            candidates.append({
                "role": "Software Engineer",
                "domain": "software",
                "score": 14 + project_depth,
                "confidence": 45,
                "evidence": tech_terms[:4] or ["Resume uploaded"],
                "missing": ["Role-specific project detail", "Targeted tool evidence"],
                "reason": "The resume contains general software-development evidence, so a broad engineering role is the safest fit.",
            })

        candidates.sort(key=lambda item: (item["score"], item["confidence"]), reverse=True)
        return candidates[:8]

    def _weighted_role_analysis(self, resume_json: dict) -> ResumeAnalysis:
        profile = self._candidate_profile(resume_json)
        candidates = self._dynamic_role_candidates(resume_json)
        all_skills = self._dedupe(profile.skills + profile.technologies)

        roles = []
        for index, item in enumerate(candidates):
            role = JobPreference(
                role=item["role"],
                confidence=self._unique_confidence(item["confidence"], index),
                reasoning=item["reason"] + f" Confidence is based on applied project depth, domain relevance, and experience level ({self._experience_level(profile.experience_years)}).",
                supporting_skills=item["evidence"],
                missing_skills=item["missing"],
                domain=item["domain"],
            )
            roles.append(role)

        return ResumeAnalysis(
            skills=all_skills,
            technologies=profile.technologies or all_skills,
            experience_level=self._experience_level(profile.experience_years),
            strengths=self._dedupe([skill for role in roles for skill in role.supporting_skills])[:5],
            candidate_profile=profile,
            recommended_roles=roles[:3],
            suggested_roles=roles,
        )

    def _role_reason(self, role: str, evidence: List[str], project_hits: List[str], title_hits: List[str], cert_hits: List[str], course_hits: List[str]) -> str:
        signals = []
        if evidence:
            signals.append(", ".join(evidence))
        if project_hits:
            signals.append("project evidence")
        if title_hits:
            signals.append("past role/title evidence")
        if cert_hits:
            signals.append("certification evidence")
        if course_hits:
            signals.append("coursework/education evidence")
        return f"{role} fits because the resume shows {', '.join(signals[:4])}."

    def _select_distinct_roles(self, scored_roles: List[Dict]) -> List[Dict]:
        selected = []
        used_domains: Set[str] = set()

        for role in scored_roles:
            domain = role["domain"]
            if domain in used_domains:
                continue
            selected.append(role)
            used_domains.add(domain)
            if len(selected) >= 8:
                break
        return selected

    def _fill_related_roles(self, selected: List[Dict], scored_roles: List[Dict]) -> List[Dict]:
        existing = {item["role"] for item in selected}
        used_domains = {item["domain"] for item in selected}

        for role in scored_roles:
            domain = role["domain"]
            if role["role"] not in existing and domain not in used_domains:
                selected.append(role)
                existing.add(role["role"])
                used_domains.add(domain)
            if len(selected) >= 5:
                break
        return selected

    def _unique_confidence(self, confidence: float, index: int) -> float:
        return max(35, min(96, round(float(confidence) - (index * 1.7), 1)))

    def _dedupe(self, items: List[str]) -> List[str]:
        seen = set()
        result = []
        for item in items:
            key = str(item).strip().lower()
            if key and key not in seen:
                seen.add(key)
                result.append(str(item).strip())
        return result

    def _experience_level(self, value: Optional[str]) -> str:
        match = re.search(r"\d+", str(value or ""))
        if not match:
            return "Internship / Entry-level"
        years = int(match.group(0))
        if years < 1:
            return "Internship / Entry-level"
        if years < 3:
            return "Junior"
        if years < 6:
            return "Mid-level"
        return "Senior"

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
