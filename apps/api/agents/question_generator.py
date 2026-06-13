from typing import List, TypedDict, Dict, Optional
import os
import json
import logging
import re

import google.generativeai as genai
from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)

# ── 1. Models ───────────────────────────────────────────────────────────────

class Question(BaseModel):
    text: str = Field(description="The actual question text")
    type: str = Field(description="technical, behavioral, or project_based")
    topic: str = Field(description="Resume Projects | Core Skills | Problem Solving | System Design | Behavioral")
    reasoning: str = Field(description="Which resume evidence drove this question")

class AgentState(TypedDict):
    resume_data: dict
    job_role: str
    conversation_history: List[dict]
    covered_topics: List[str]
    asked_questions: List[str]
    next_question: Optional[Question]

ALL_TOPICS = ["Resume Projects", "Core Skills", "Problem Solving", "System Design", "Behavioral"]

# ── 2. Resume parser ─────────────────────────────────────────────────────────

class ResumeContext:
    """
    Extracts rich, structured context from a parsed resume dict so every
    generated question is anchored to something the candidate actually did.
    """

    def __init__(self, resume: dict):
        self.raw          = resume
        self.skills       = self._as_list(resume.get("skills"))
        self.technologies = self._as_list(resume.get("technologies"))
        self.all_skills   = self._dedupe(self.skills + self.technologies)
        self.projects     = self._parse_projects(resume.get("projects") or [])
        self.experience   = self._parse_experience(resume.get("experience") or [])
        self.certifications = self._as_list(resume.get("certifications"))
        self.education    = str(resume.get("education_level") or resume.get("education") or "")
        self.experience_years = str(resume.get("years_of_experience") or "Not specified")
        self.past_titles  = self._as_list(resume.get("past_job_titles"))

    # ── serialisers ──────────────────────────────────────────────────────────

    def to_prompt_block(self) -> str:
        """Returns a tightly formatted block for injection into the LLM prompt."""
        lines = []

        if self.all_skills:
            lines.append(f"SKILLS & TECH: {', '.join(self.all_skills[:18])}")

        for i, p in enumerate(self.projects[:4], 1):
            tech_str = f" [{', '.join(p['tech'][:6])}]" if p['tech'] else ""
            desc_str = f" — {p['description'][:140]}" if p['description'] else ""
            lines.append(f"PROJECT {i}: {p['name']}{tech_str}{desc_str}")

        for i, e in enumerate(self.experience[:3], 1):
            lines.append(f"ROLE {i}: {e['title']} @ {e['company']} — {e['summary'][:120]}")

        if self.past_titles:
            lines.append(f"PAST TITLES: {', '.join(self.past_titles[:4])}")

        if self.certifications:
            lines.append(f"CERTIFICATIONS: {', '.join(self.certifications[:4])}")

        if self.education:
            lines.append(f"EDUCATION: {self.education}")

        return "\n".join(lines) if lines else "No structured resume data available."

    def best_project(self) -> Optional[dict]:
        return self.projects[0] if self.projects else None

    def top_skill(self, exclude: List[str] = None) -> str:
        exclude = [s.lower() for s in (exclude or [])]
        for s in self.all_skills:
            if s.lower() not in exclude:
                return s
        return "your primary stack"

    def project_tech_str(self, project: dict) -> str:
        return ", ".join(project.get("tech", [])[:4]) or "the project stack"

    # ── internal ─────────────────────────────────────────────────────────────

    def _as_list(self, value) -> List[str]:
        if isinstance(value, list):
            return [str(i).strip() for i in value if str(i).strip()]
        return [str(value).strip()] if value else []

    def _dedupe(self, items: List[str]) -> List[str]:
        seen, out = set(), []
        for item in items:
            k = item.lower()
            if k not in seen:
                seen.add(k)
                out.append(item)
        return out

    def _parse_projects(self, raw: list) -> List[dict]:
        out = []
        for p in raw:
            if isinstance(p, dict):
                techs = p.get("technologies") or []
                out.append({
                    "name":        str(p.get("name") or "Unnamed Project"),
                    "description": str(p.get("description") or ""),
                    "tech":        [str(t) for t in techs if str(t).strip()],
                })
            elif isinstance(p, str) and p.strip():
                out.append({"name": p.strip(), "description": "", "tech": []})
        return out

    def _parse_experience(self, raw: list) -> List[dict]:
        out = []
        for e in raw:
            if isinstance(e, dict):
                descs = e.get("description") or []
                summary = descs[0] if isinstance(descs, list) and descs else str(descs)[:120]
                out.append({
                    "title":   str(e.get("role") or e.get("title") or ""),
                    "company": str(e.get("company") or ""),
                    "summary": str(summary)[:150],
                })
            elif isinstance(e, str) and e.strip():
                out.append({"title": e.strip(), "company": "", "summary": ""})
        return out


# ── 3. Agent ────────────────────────────────────────────────────────────────

class QuestionGeneratorAgent:
    """
    Generates deeply resume-tailored interview questions using Gemini 2.5 Flash.
    Every question references a specific project, skill, or experience from the
    candidate's actual resume — never a generic fallback.
    """

    def __init__(self, api_key: str = None):
        key = api_key or os.getenv("GEMINI_API_KEY") or os.getenv("GOOGLE_API_KEY")
        if not key:
            raise ValueError("Set GEMINI_API_KEY or GOOGLE_API_KEY in your .env")
        genai.configure(api_key=key)
        self.model = genai.GenerativeModel(
            model_name="gemini-2.5-flash",
            generation_config=genai.GenerationConfig(
                temperature=0.7,
                max_output_tokens=600,
            ),
        )
        logger.info("QuestionGeneratorAgent: Gemini 2.5 Flash ready.")

    # ── public ──────────────────────────────────────────────────────────────

    async def generate_next_question(self, state: AgentState) -> Dict:
        resume  = state.get("resume_data", {})
        role    = state.get("job_role", "Software Engineer")
        history = state.get("conversation_history", [])
        covered = state.get("covered_topics", [])
        asked   = state.get("asked_questions", [])

        ctx       = ResumeContext(resume)
        remaining = [t for t in ALL_TOPICS if t not in covered]

        if not remaining and len(asked) >= 5:
            logger.info("QuestionGen: All topics covered — signalling completion.")
            return {"next_question": None}

        target_topic = remaining[0] if remaining else "Core Skills"
        logger.info(f"QuestionGen: role='{role}' | target='{target_topic}'")

        prompt = self._build_prompt(ctx, role, history, covered, asked, target_topic)

        try:
            response = await self.model.generate_content_async(prompt)
            data     = self._parse_json(response.text.strip())

            if not data.get("text"):
                raise ValueError("Empty question text from Gemini")

            question = Question(
                text      = data["text"],
                type      = data.get("type", "technical"),
                topic     = data.get("topic", target_topic),
                reasoning = data.get("reasoning", ""),
            )
            logger.info(f"QuestionGen ✓ [{question.topic}] {question.text[:90]}...")
            return {
                "next_question":   question,
                "asked_questions": asked + [question.text],
                "covered_topics":  list(set(covered + [question.topic])),
            }

        except Exception as e:
            logger.error(f"QuestionGen: Gemini failed — {e}. Using tailored fallback.")
            fallback = self._tailored_fallback(ctx, role, asked, remaining, target_topic)
            return {
                "next_question":   fallback,
                "asked_questions": asked + [fallback.text],
                "covered_topics":  list(set(covered + [fallback.topic])),
            }

    # ── prompt builder ───────────────────────────────────────────────────────

    def _build_prompt(
        self,
        ctx: ResumeContext,
        role: str,
        history: list,
        covered: list,
        asked: list,
        target_topic: str,
    ) -> str:

        resume_block = ctx.to_prompt_block()
        recent_turns = json.dumps(history[-4:], indent=2) if history else "[]"

        # Inject specific resume artifacts into the topic hint so Gemini
        # is forced to reference them rather than staying generic.
        topic_guidance = self._topic_guidance(ctx, target_topic, role)

        return f"""You are a senior engineering manager at a top-tier tech company conducting
a real job interview for a {role} position.

━━━━━━━━━━━━━━━━━ CANDIDATE RESUME ━━━━━━━━━━━━━━━━━
{resume_block}

━━━━━━━━━━━━━━━ CONVERSATION SO FAR ━━━━━━━━━━━━━━━
{recent_turns}

━━━━━━━━━━━━━━━━ ALREADY COVERED ━━━━━━━━━━━━━━━━━
Topics covered : {covered or 'None yet'}
Questions asked: {json.dumps(asked) if asked else 'None yet'}

━━━━━━━━━━━━━━━━━━━ YOUR TASK ━━━━━━━━━━━━━━━━━━━━
Generate ONE interview question for the topic: "{target_topic}"

{topic_guidance}

━━━━━━━━━━━━━━━━━━━━ RULES ━━━━━━━━━━━━━━━━━━━━━━━
1. SPECIFICITY (mandatory): The question MUST name a specific project, technology,
   skill, or experience from the CANDIDATE RESUME above.
   ✗ BAD : "Tell me about a challenging project you worked on."
   ✓ GOOD: "In your {ctx.best_project()['name'] if ctx.best_project() else 'most recent project'}, 
            you used {ctx.project_tech_str(ctx.best_project()) if ctx.best_project() else 'several technologies'}.
            Walk me through the biggest architectural decision you made there."

2. NO REPETITION: The question must NOT be semantically similar to anything in
   "Questions asked" above.

3. DEPTH: Probe for tradeoffs, real implementation choices, failure modes, or
   measurable outcomes — not surface-level definitions.

4. TONE: Curious, professional, direct — like a real engineering manager.

5. LENGTH: The question should be 1-3 sentences maximum.

━━━━━━━━━━━━━━━━━ OUTPUT FORMAT ━━━━━━━━━━━━━━━━━━
Respond with ONLY valid JSON — no markdown fences, no explanation:
{{
  "text": "<the full question, naming specific resume items>",
  "type": "<technical | behavioral | project_based>",
  "topic": "<one of: Resume Projects | Core Skills | Problem Solving | System Design | Behavioral>",
  "reasoning": "<one sentence: which resume evidence drove this question>"
}}"""

    def _topic_guidance(self, ctx: ResumeContext, topic: str, role: str) -> str:
        """
        Returns topic-specific instructions that reference concrete resume
        artifacts, nudging Gemini toward highly personalised questions.
        """
        project  = ctx.best_project()
        skill    = ctx.top_skill()
        p_name   = project["name"] if project else "your most significant project"
        p_tech   = self.project_tech_str(project) if project else skill
        exp_str  = ctx.experience[0]["title"] if ctx.experience else role

        guidance = {
            "Resume Projects": (
                f"Focus on '{p_name}'. Ask about a specific technical decision, "
                f"a challenge with {p_tech}, or what they'd improve if they rebuilt it."
            ),
            "Core Skills": (
                f"The candidate lists '{skill}' as a key skill. Ask about a real-world "
                f"situation where they applied it — requiring them to explain depth of understanding, "
                f"not just familiarity."
            ),
            "Problem Solving": (
                f"Reference a scenario plausible given their work on '{p_name}' or their "
                f"experience as {exp_str}. Ask about debugging a hard production issue, "
                f"handling an unexpected failure, or a complex algorithmic challenge they faced."
            ),
            "System Design": (
                f"Ask them to design or critique a system relevant to '{p_name}' or '{skill}'. "
                f"Probe for scalability, data modelling, API design, or failure handling — "
                f"at the level expected of a {role}."
            ),
            "Behavioral": (
                f"Ask a STAR-format question grounded in their actual background: "
                f"their time as {exp_str}, working on {p_name}, or navigating a technical "
                f"disagreement. Avoid clichés like 'tell me your biggest weakness'."
            ),
        }
        return guidance.get(topic, f"Generate a question appropriate for a {role} targeting '{topic}'.")

    # helper so _topic_guidance can call it without `self` issues
    def project_tech_str(self, project: Optional[dict]) -> str:
        if not project:
            return "the project stack"
        return ", ".join(project.get("tech", [])[:4]) or "the project stack"

    # ── JSON parser ──────────────────────────────────────────────────────────

    def _parse_json(self, raw: str) -> dict:
        cleaned = re.sub(r"```(?:json)?", "", raw).replace("```", "").strip()
        try:
            return json.loads(cleaned)
        except json.JSONDecodeError:
            match = re.search(r"\{.*\}", cleaned, re.DOTALL)
            if match:
                try:
                    return json.loads(match.group(0))
                except Exception:
                    pass
        logger.warning("QuestionGen: Could not parse Gemini JSON.")
        return {}

    # ── tailored fallback ────────────────────────────────────────────────────

    def _tailored_fallback(
        self,
        ctx: ResumeContext,
        role: str,
        asked: List[str],
        remaining: List[str],
        target_topic: str,
    ) -> Question:
        """
        Fallback questions that still reference real resume data —
        never generic, always grounded.
        """
        project = ctx.best_project()
        skill   = ctx.top_skill()
        s2      = ctx.top_skill(exclude=[skill])
        p_name  = project["name"] if project else "your most significant project"
        p_tech  = self.project_tech_str(project)
        exp     = ctx.experience[0]["title"] if ctx.experience else role

        pool: Dict[str, Question] = {
            "Resume Projects": Question(
                text=(
                    f"Walk me through the architecture of '{p_name}'. "
                    f"You used {p_tech} — what was the hardest design decision you made, "
                    f"and what would you do differently now?"
                ),
                type="project_based", topic="Resume Projects",
                reasoning=f"Fallback: architecture deep-dive on project '{p_name}'.",
            ),
            "Core Skills": Question(
                text=(
                    f"You have experience with {skill} and {s2}. "
                    f"Describe a situation where you had to choose between them or combine them — "
                    f"what drove your decision?"
                ),
                type="technical", topic="Core Skills",
                reasoning=f"Fallback: skill tradeoff between '{skill}' and '{s2}'.",
            ),
            "System Design": Question(
                text=(
                    f"Given your background with {skill}, how would you design a system "
                    f"that handles 100× the load of '{p_name}'? "
                    f"Walk me through your approach to scalability and failure recovery."
                ),
                type="technical", topic="System Design",
                reasoning=f"Fallback: scale challenge based on '{p_name}' and '{skill}'.",
            ),
            "Problem Solving": Question(
                text=(
                    f"Tell me about the most difficult production bug you encountered while "
                    f"working with {p_tech}. How did you investigate and resolve it?"
                ),
                type="technical", topic="Problem Solving",
                reasoning=f"Fallback: debugging probe using project tech '{p_tech}'.",
            ),
            "Behavioral": Question(
                text=(
                    f"As {exp}, tell me about a time a technical decision you championed "
                    f"was challenged by your team. How did you handle it, and what was the outcome?"
                ),
                type="behavioral", topic="Behavioral",
                reasoning=f"Fallback: conflict/collaboration using role context '{exp}'.",
            ),
        }

        # Try target topic first, then remaining, then any unused
        priority = [target_topic] + [t for t in remaining if t != target_topic] + list(pool.keys())
        for topic in priority:
            q = pool.get(topic)
            if q and q.text not in asked:
                return q

        return Question(
            text=(
                f"How do you approach ensuring code quality and long-term maintainability "
                f"when working with {skill} in a team environment?"
            ),
            type="technical", topic="Core Skills",
            reasoning="Absolute fallback — all options exhausted.",
        )
