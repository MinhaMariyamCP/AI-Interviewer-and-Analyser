from typing import List, TypedDict, Dict, Optional
import operator
import os
import json
import logging

import google.generativeai as genai
from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)

# ── 1. Pydantic models ──────────────────────────────────────────────────────

class Question(BaseModel):
    text: str = Field(description="The actual question text")
    type: str = Field(description="technical, behavioral, or project_based")
    topic: str = Field(description="Resume Projects | Core Skills | Problem Solving | System Design | Behavioral")
    reasoning: str = Field(description="Why this question was selected based on resume and role")

class AgentState(TypedDict):
    resume_data: dict
    job_role: str
    conversation_history: List[dict]
    covered_topics: List[str]
    asked_questions: List[str]
    next_question: Optional[Question]

# ── 2. Gemini helpers ───────────────────────────────────────────────────────

ALL_TOPICS = ["Resume Projects", "Core Skills", "Problem Solving", "System Design", "Behavioral"]

def _build_resume_highlights(resume: dict) -> str:
    """Pull the most resume-specific details to ground every question."""
    parts = []

    skills = resume.get("skills") or []
    techs  = resume.get("technologies") or []
    if skills or techs:
        parts.append(f"Skills/Tech: {', '.join((skills + techs)[:15])}")

    projects = resume.get("projects") or []
    for p in projects[:3]:
        if isinstance(p, dict):
            name = p.get("name") or ""
            desc = p.get("description") or ""
            tech = ", ".join(p.get("technologies") or [])
            parts.append(f"Project — {name}: {desc[:120]} [{tech}]")
        elif isinstance(p, str):
            parts.append(f"Project: {p[:120]}")

    experience = resume.get("experience") or []
    for e in experience[:2]:
        if isinstance(e, dict):
            role    = e.get("role") or e.get("title") or ""
            company = e.get("company") or ""
            descs   = e.get("description") or []
            bullet  = descs[0] if isinstance(descs, list) and descs else str(descs)[:100]
            parts.append(f"Experience — {role} @ {company}: {bullet}")

    edu = resume.get("education_level") or resume.get("education") or ""
    if edu:
        parts.append(f"Education: {edu}")

    certs = resume.get("certifications") or []
    if certs:
        parts.append(f"Certifications: {', '.join(str(c) for c in certs[:4])}")

    return "\n".join(parts) if parts else "No structured resume data available."


def _parse_gemini_question(raw: str) -> dict:
    """
    Extract JSON from Gemini's response even when it wraps it in markdown fences.
    Falls back to a best-effort dict so the caller never crashes.
    """
    import re
    # Strip ```json ... ``` fences
    cleaned = re.sub(r"```(?:json)?", "", raw).replace("```", "").strip()
    try:
        return json.loads(cleaned)
    except json.JSONDecodeError:
        # Try to find the first {...} block
        match = re.search(r"\{.*\}", cleaned, re.DOTALL)
        if match:
            try:
                return json.loads(match.group(0))
            except Exception:
                pass
    logger.warning("Could not parse Gemini JSON response; using empty dict.")
    return {}


# ── 3. Agent ────────────────────────────────────────────────────────────────

class QuestionGeneratorAgent:
    """Generates resume-grounded interview questions using Gemini 2.5 Flash."""

    def __init__(self, api_key: str = None):
        api_key = api_key or os.getenv("GEMINI_API_KEY") or os.getenv("GOOGLE_API_KEY")
        if not api_key:
            raise ValueError(
                "No Gemini API key found. Set GEMINI_API_KEY or GOOGLE_API_KEY in your .env"
            )
        genai.configure(api_key=api_key)
        self.model = genai.GenerativeModel(
            model_name="gemini-2.5-flash",
            generation_config=genai.GenerationConfig(
                temperature=0.7,
                max_output_tokens=512,
            ),
        )
        logger.info("QuestionGeneratorAgent: Gemini 2.5 Flash initialized.")

    # ── public ──────────────────────────────────────────────────────────────

    async def generate_next_question(self, state: AgentState) -> Dict:
        resume   = state.get("resume_data", {})
        role     = state.get("job_role", "Software Engineer")
        history  = state.get("conversation_history", [])
        covered  = state.get("covered_topics", [])
        asked    = state.get("asked_questions", [])

        remaining = [t for t in ALL_TOPICS if t not in covered]

        # All topics done → signal completion
        if not remaining and len(asked) >= 5:
            logger.info("QuestionGen: All topics covered — signaling completion.")
            return {"next_question": None}

        logger.info(f"QuestionGen: Generating for role='{role}', remaining={remaining}")

        prompt = self._build_prompt(resume, role, history, covered, asked, remaining)

        try:
            response = await self.model.generate_content_async(prompt)
            raw      = response.text.strip()
            data     = _parse_gemini_question(raw)

            if not data.get("text"):
                raise ValueError("Gemini returned empty question text")

            question = Question(
                text      = data.get("text", ""),
                type      = data.get("type", "technical"),
                topic     = data.get("topic", remaining[0] if remaining else "Core Skills"),
                reasoning = data.get("reasoning", ""),
            )

            logger.info(f"QuestionGen: topic={question.topic} | {question.text[:80]}...")
            return {
                "next_question":  question,
                "asked_questions": asked + [question.text],
                "covered_topics":  list(set(covered + [question.topic])),
            }

        except Exception as e:
            logger.error(f"QuestionGen: Gemini call failed — {e}. Using fallback.")
            fallback = self._heuristic_fallback(resume, role, asked, remaining)
            return {
                "next_question":  fallback,
                "asked_questions": asked + [fallback.text],
                "covered_topics":  list(set(covered + [fallback.topic])),
            }

    # ── private ─────────────────────────────────────────────────────────────

    def _build_prompt(
        self,
        resume: dict,
        role: str,
        history: list,
        covered: list,
        asked: list,
        remaining: list,
    ) -> str:
        highlights = _build_resume_highlights(resume)
        recent     = json.dumps(history[-4:], indent=2) if history else "[]"
        topic_hint = remaining[0] if remaining else "Core Skills"

        return f"""You are a senior technical interviewer at a top-tier tech company.
Your task: generate ONE highly personalised interview question for a {role} position.

━━━ CANDIDATE RESUME HIGHLIGHTS ━━━
{highlights}

━━━ INTERVIEW SO FAR (last 2 turns) ━━━
{recent}

━━━ ALREADY COVERED TOPICS ━━━
{covered or "None yet"}

━━━ ALREADY ASKED QUESTIONS ━━━
{json.dumps(asked, indent=2) if asked else "None yet"}

━━━ RULES ━━━
1. GROUNDING (mandatory): Every question MUST reference a specific skill, project,
   technology, or experience visible in the resume highlights above.
   DO NOT ask generic questions that could apply to any candidate.
2. TOPIC: Target the topic "{topic_hint}" — it has not been covered yet.
3. NO REPETITION: The question must not be semantically similar to anything already asked.
4. DEPTH: For technical topics, probe for tradeoffs, architecture decisions, or real
   implementation details — not surface-level definitions.
5. TONE: Sound like a curious, professional engineering manager.

━━━ OUTPUT FORMAT ━━━
Respond with ONLY valid JSON — no markdown fences, no extra text:
{{
  "text": "<the full question to ask the candidate>",
  "type": "<technical | behavioral | project_based>",
  "topic": "<one of: Resume Projects | Core Skills | Problem Solving | System Design | Behavioral>",
  "reasoning": "<one sentence explaining which resume evidence drove this question>"
}}"""

    def _heuristic_fallback(
        self,
        resume: dict,
        role: str,
        asked: List[str],
        remaining: List[str],
    ) -> Question:
        skills = resume.get("skills") or resume.get("technologies") or []
        if not skills:
            skills = ["software engineering", "system design", "problem solving"]

        s0 = skills[0]
        s1 = skills[1] if len(skills) > 1 else s0

        # Map topic → candidate question
        topic_pool: Dict[str, Question] = {
            "Core Skills": Question(
                text=f"You listed {s0} as a core skill. Walk me through the most complex "
                     f"technical tradeoff you navigated while using it in production.",
                type="technical", topic="Core Skills",
                reasoning=f"Fallback: deep-dive on resume skill '{s0}'.",
            ),
            "Resume Projects": Question(
                text=f"Tell me about the architecture of the most significant project where "
                     f"you used {s1}. What would you redesign today and why?",
                type="project_based", topic="Resume Projects",
                reasoning=f"Fallback: project walkthrough using skill '{s1}'.",
            ),
            "System Design": Question(
                text=f"If the system you built with {s0} needed to handle 10× its current "
                     f"load, what would your scaling strategy be?",
                type="technical", topic="System Design",
                reasoning=f"Fallback: scalability probe on '{s0}'.",
            ),
            "Problem Solving": Question(
                text="Describe a production bug that took you the longest to debug. "
                     "Walk me through your investigation process step by step.",
                type="technical", topic="Problem Solving",
                reasoning="Fallback: debugging process assessment.",
            ),
            "Behavioral": Question(
                text="Tell me about a time you disagreed with a technical decision made by "
                     "your team lead. How did you handle it and what was the outcome?",
                type="behavioral", topic="Behavioral",
                reasoning="Fallback: conflict-resolution / collaboration assessment.",
            ),
        }

        # Pick the first remaining topic that hasn't been asked
        for topic in (remaining or list(topic_pool.keys())):
            candidate = topic_pool.get(topic)
            if candidate and candidate.text not in asked:
                return candidate

        # Absolute last resort
        return Question(
            text=f"How do you ensure code quality and maintainability when working with {s0} "
                 f"in a team environment?",
            type="technical", topic="Core Skills",
            reasoning="Absolute fallback — all other options exhausted.",
        )
