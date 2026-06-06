import os
import json
import logging
from typing import Dict, List
from langchain_openai import ChatOpenAI, OpenAIEmbeddings
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_core.messages import HumanMessage, SystemMessage
from pydantic import BaseModel
import numpy as np

from .state import InterviewState, CandidateProfile, GeneratedQuestion, TurnEval

logger = logging.getLogger(__name__)
MAX_LIVE_TURNS = 5

def _safe_list(value, fallback):
    if isinstance(value, list):
        cleaned = [str(item).strip() for item in value if str(item).strip()]
        return cleaned or fallback
    if isinstance(value, str) and value.strip():
        return [value.strip()]
    return fallback

# Rebuild Pydantic models for nested structures (Python 3.14 + Pydantic v2)
CandidateProfile.model_rebuild()
GeneratedQuestion.model_rebuild()
TurnEval.model_rebuild()

class AdaptiveAgents:
    def __init__(self, api_key: str = None):
        self.openai_key = api_key or os.getenv("OPENAI_API_KEY")
        self.google_key = os.getenv("GOOGLE_API_KEY")
        
        # Check if keys are valid
        openai_is_valid = self.openai_key and self.openai_key.startswith("sk-") and len(self.openai_key) > 20
        google_is_valid = self.google_key and not self.google_key.startswith("AQ.") and len(self.google_key) > 10
        
        if google_is_valid and not openai_is_valid:
            logger.info("Using Google Gemini as primary LLM for AdaptiveAgents")
            self.llm = ChatGoogleGenerativeAI(
                model="gemini-1.5-flash",
                google_api_key=self.google_key,
                temperature=0.7
            )
            self.fallback_llm = None
            try:
                from langchain_google_genai import GoogleGenerativeAIEmbeddings
                self.embeddings = GoogleGenerativeAIEmbeddings(
                    model="models/embedding-001",
                    google_api_key=self.google_key
                )
            except Exception as embed_err:
                logger.error(f"Failed to load Google embeddings: {embed_err}")
                self.embeddings = None
        else:
            logger.info("Using OpenAI as primary LLM for AdaptiveAgents")
            self.llm = ChatOpenAI(
                model="gpt-4o-mini",
                openai_api_key=self.openai_key,
                temperature=0.7
            )
            self.fallback_llm = None
            if google_is_valid:
                self.fallback_llm = ChatGoogleGenerativeAI(
                    model="gemini-1.5-flash",
                    google_api_key=self.google_key,
                    temperature=0.7
                )
            self.embeddings = OpenAIEmbeddings(openai_api_key=self.openai_key)

    async def _safe_structured_output(self, prompt: str, schema, system_msg: str):
        """Tries primary LLM first, falls back to alternative LLM if any error occurs."""
        try:
            structured_llm = self.llm.with_structured_output(schema)
            return await structured_llm.ainvoke([
                SystemMessage(content=system_msg),
                HumanMessage(content=prompt)
            ])
        except Exception as e:
            if self.fallback_llm:
                logger.warning(f"Primary LLM failed (Error: {e}). Falling back to Gemini...")
                try:
                    structured_fallback = self.fallback_llm.with_structured_output(schema)
                    return await structured_fallback.ainvoke([
                        SystemMessage(content=system_msg),
                        HumanMessage(content=prompt)
                    ])
                except Exception as fallback_err:
                    logger.error(f"Fallback LLM also failed: {fallback_err}")
            raise e

    # --- Agent 1: Resume Analyzer ---
    async def analyze_resume(self, state: InterviewState) -> Dict:
        """Builds Candidate Knowledge Graph from raw parsed JSON."""
        resume = state.get("resume_data", {})
        
        prompt = f"""
        Extract a highly detailed Candidate Profile from this resume data.
        Focus on specific technical skills, detailed technologies mentioned, notable projects (with descriptions), work experience, and key achievements.
        Resume: {json.dumps(resume, indent=2)}
        """
        
        try:
            profile = await self._safe_structured_output(
                prompt, CandidateProfile, 
                "You are an expert technical interviewer building a deep candidate knowledge graph. Do not omit any technical details."
            )
            logger.info(f"Agent 1: Candidate Knowledge Graph built via LLM. Profile: {json.dumps(profile.model_dump(), indent=2)}")
            return {
                "candidate_profile": profile.model_dump(),
                "attempted_questions": []
            }
        except Exception as e:
            logger.error(f"Agent 1 Error: {e}. Using intelligent fallback.")
            
            # Intelligent Fallback using actual data
            skills = _safe_list(resume.get("skills"), ["Software Engineering", "Problem Solving", "Communication"])
            projects = resume.get("projects") or []
            experience = resume.get("experience") or []
            
            proj_mapped = [{"name": p.get("name", "Project"), "desc": str(p.get("description", ""))} for p in projects]
            exp_mapped = [{"role": e.get("role", "Engineer"), "company": e.get("company", "Company")} for e in experience]
            
            fallback_profile = CandidateProfile(
                core_skills=skills[:10],
                technologies=skills,
                projects=proj_mapped,
                experience=exp_mapped,
                achievements=[],
                education=[],
                summary="Candidate with experience in " + ", ".join(skills[:3])
            )
            return {
                "candidate_profile": fallback_profile.model_dump(),
                "attempted_questions": []
            }

    # --- Agent 2: Question Planner ---
    async def plan_question(self, state: InterviewState) -> Dict:
        """Generates the next core question based on remaining topics and knowledge graph."""
        profile = state.get("candidate_profile", {})
        role = state.get("job_role", "Software Engineer")
        remaining = state.get("remaining_topics", [])
        covered = state.get("covered_topics", [])
        asked = state.get("asked_questions", [])
        attempted = state.get("attempted_questions", [])
        last_answer = state.get("current_answer", "N/A")
        
        if not remaining:
            logger.info("Agent 2: No topics left. Generating final report.")
            return {"next_step": "report", "current_question": ""}

        # Force diversity: Pick the next topic in line
        topic = remaining[0]
        
        logger.info(f"--- Question Planning Debug ---")
        logger.info(f"Selected Topic: {topic}")
        logger.info(f"Previously Asked Questions ({len(asked)}): {asked}")
        logger.info(f"Previously Attempted (Rejected): {attempted}")
        logger.info(f"Covered Topics: {covered}")
        logger.info(f"Remaining Topics: {remaining}")
        
        prompt = f"""
        Target Role: {role}
        Topic to cover: {topic}
        Candidate Profile: {json.dumps(profile, indent=2)}
        
        BLACKLIST (Questions already asked - DO NOT REPEAT OR REPHRASE THESE):
        {json.dumps(asked + attempted)}
        
        Last Candidate Answer (for context):
        {last_answer}
        
        Generate ONE highly specific interview question.
        
        CRITICAL RULES:
        1. PERSISTENT MEMORY: You MUST NOT ask any question that is semantically similar to the BLACKLIST.
        2. NO REPHRASING: Even if you use different words, if the core technical concept or project being probed is the same as a blacklisted question, it is a FAILURE.
        3. DIVERSITY: Ensure this question probes a DIFFERENT aspect of the candidate's background than previous questions.
        4. RESUME DRIVEN: The question MUST be directly derived from specific details in the candidate's resume (specific projects, technologies, or roles).
        5. NO GENERICS: Never ask generic questions like 'Explain your implementation' or 'Tell me about yourself'. Be surgical.
        6. TOPIC ADHERENCE: The question MUST strictly align with the current topic: {topic}.
        """
        
        try:
            q = await self._safe_structured_output(
                prompt, GeneratedQuestion,
                "You are a senior technical interviewer. You are precise, challenging, and have a perfect memory of the interview so far."
            )
            logger.info(f"Agent 2: Core Question generated for topic [{topic}]. Reasoning: {q.reasoning}")
            
            return {
                "current_question": q.text,
                "current_topic": topic,
                "next_step": "manage_state",
                "duplicate_detected": False
            }
        except Exception as e:
            logger.error(f"Agent 2 Error: {e}. Using intelligent fallback.")
            # Fallback question generation: Randomized to avoid exact repetition
            technologies = _safe_list(
                profile.get("technologies") or profile.get("core_skills"),
                ["your technical background"]
            )
            core_skills = _safe_list(profile.get("core_skills") or technologies, ["your experience"])
            projects = profile.get("projects") or []
            experiences = profile.get("experience") or []
            first_technology = technologies[0]
            last_technology = technologies[-1]
            first_skill = core_skills[0]
            project_name = "one of your listed projects"
            project_desc = ""
            if projects and isinstance(projects[0], dict):
                project_name = projects[0].get("name") or project_name
                project_desc = projects[0].get("desc") or projects[0].get("description") or ""
            role_context = role
            if experiences and isinstance(experiences[0], dict):
                role_context = experiences[0].get("role") or role_context
            fallbacks = {
                "Resume Projects": f"In {project_name}, what exact problem were you solving, what did you build, and how did {first_technology} affect your design choices?",
                "Technical Skills": f"Your resume mentions {first_skill}. Can you explain a real task where you used it, including one implementation detail and one limitation?",
                "System Design": f"If you had to scale {project_name}, what bottleneck would you handle first and what tradeoff would you make?",
                "Problem Solving": f"Tell me about a difficult issue from {project_name or role_context}. What clues did you use to find the root cause?",
                "Behavioral Questions": f"In your {role_context} experience, describe a moment where you had to adapt your approach and what changed because of it.",
                "Leadership": f"Describe a time you influenced a technical or project decision related to {project_name}. How did you align others?",
                "Communication": f"How would you explain {project_name}{' (' + project_desc[:90] + ')' if project_desc else ''} to a non-technical stakeholder?"
            }
            fallback_q = fallbacks.get(topic, f"Can you describe a specific resume-based example where you used {last_technology} and explain the key tradeoff?")
            
            return {
                "current_question": fallback_q,
                "current_topic": topic,
                "next_step": "manage_state",
                "duplicate_detected": False
            }

    # --- Agent 3: Answer Evaluator ---
    async def evaluate_answer(self, state: InterviewState) -> Dict:
        """Real-time analysis of the candidate's answer."""
        q = state.get("current_question", "")
        a = state.get("current_answer", "")
        
        if not a:
            return {}

        prompt = f"""
        Question: {q}
        Answer: {a}
        
        Analyze this answer like a senior technical interviewer. 
        Evaluate:
        1. Technical Accuracy: Is the answer factually correct?
        2. Depth of Knowledge: Does the candidate show deep understanding or just surface level?
        3. Communication Clarity: Is the explanation structured and easy to follow?
        4. Confidence: Does the candidate sound sure of their answer?
        5. Completeness: Did they address all parts of the question?
        6. Examples Used: Did they provide concrete real-world examples from their resume?
        7. Tradeoff Awareness: Did they mention alternative approaches or pros/cons?
        8. System Design Thinking: If applicable, did they consider scalability, reliability, or constraints?

        Provide scores (0-100) and specific strengths and weaknesses.
        """
        
        try:
            eval_res = await self._safe_structured_output(
                prompt, TurnEval,
                "You are a strict but fair technical assessor for a top-tier tech company."
            )
            logger.info(f"Agent 3: Evaluation complete. Scores: {eval_res.technical_score} Tech, {eval_res.communication_score} Comm")
            eval_dict = eval_res.model_dump()
        except Exception as e:
            logger.error(f"Agent 3 Error: {e}. Using intelligent fallback.")
            eval_dict = TurnEval(
                technical_score=50,
                communication_score=50,
                confidence_score=50,
                knowledge_depth=50,
                weak_areas=["Could not perform detailed analysis due to system error."],
                strong_areas=[],
                reasoning="Fallback evaluation."
            ).model_dump()
            
        return {
            "current_turn_eval": eval_dict,
            "answer_history": [{
                "question": q,
                "answer": a,
                "evaluation": eval_dict
            }],
            "next_step": "report" if state.get("turn_count", 0) + 1 >= MAX_LIVE_TURNS else "follow_up_decision"
        }

    # --- Agent 4: Follow-Up Generator ---
    async def generate_follow_up(self, state: InterviewState) -> Dict:
        """Decides to ask a follow-up or move to next core topic."""
        # Only allow 1 follow-up per core question to maintain balance
        if "follow-up" in state.get("current_question", "").lower():
            logger.info("Agent 4: Already asked a follow-up. Moving to next topic.")
            return {"next_step": "plan"}
            
        q = state.get("current_question", "")
        a = state.get("current_answer", "")
        eval_dict = state.get("current_turn_eval", {})
        asked = state.get("asked_questions", [])
        attempted = state.get("attempted_questions", [])
        resume_context = state.get("candidate_profile", {})
        
        prompt = f"""
        Previous Question: {q}
        Candidate Answer: {a}
        Analysis of Answer: {json.dumps(eval_dict)}
        Candidate Resume Context: {json.dumps(resume_context)}
        
        BLACKLIST (DO NOT REPEAT):
        {json.dumps(asked + attempted)}

        Based on the answer and the resume, decide if a deep-dive follow-up is needed.
        If the answer lacks tradeoff awareness, depth in a specific technology mentioned in the resume, or concrete implementation details, generate ONE highly specific follow-up question.
        
        CRITICAL: 
        1. The follow-up must probe deeper into the EXACT answer provided while tying back to their resume.
        2. NEVER ask a generic follow-up like 'Can you explain more?'.
        3. DO NOT repeat or rephrase any blacklisted questions.
        
        If the answer is fully comprehensive, return needs_follow_up: false.
        """
        
        class FollowUpDecision(BaseModel):
            needs_follow_up: bool
            question_text: str
            reasoning: str
            
        try:
            res = await self._safe_structured_output(
                prompt, FollowUpDecision,
                "You are a senior technical interviewer probing for depth. You never ask generic follow-ups."
            )
            
            if res.needs_follow_up and res.question_text:
                logger.info(f"Agent 4: Follow-up generated: {res.question_text}. Reasoning: {res.reasoning}")
                return {
                    "current_question": res.question_text,
                    "next_step": "manage_state"
                }
            else:
                logger.info("Agent 4: No follow-up needed. Moving to next topic.")
                return {"next_step": "plan"}
                
        except Exception as e:
            logger.error(f"Agent 4 Error: {e}. Moving to next topic.")
            return {"next_step": "plan"}

    # --- Agent 5: State Manager (Duplicate Detection) ---
    async def manage_state(self, state: InterviewState) -> Dict:
        """Manages topic progression and performs semantic duplicate detection."""
        new_q = state.get("current_question", "")
        asked = state.get("asked_questions", [])
        attempted = state.get("attempted_questions", [])
        remaining = state.get("remaining_topics", [])
        covered = state.get("covered_topics", [])
        current_topic = state.get("current_topic")
        
        logger.info(f"Agent 5: Managing State for question: {new_q[:50]}...")

        # Semantic Duplicate Detection using Embeddings
        all_blacklist = asked + attempted
        if not all_blacklist:
            logger.info("First question, skipping duplicate check.")
            new_covered = list(covered)
            new_remaining = list(remaining)
            if current_topic and current_topic in new_remaining:
                new_remaining.remove(current_topic)
                new_covered.append(current_topic)
                
            return {
                "asked_questions": [new_q],
                "duplicate_detected": False,
                "covered_topics": new_covered,
                "remaining_topics": new_remaining,
                "next_step": "wait_for_answer"
            }

        try:
            texts_to_embed = all_blacklist + [new_q]
            embeddings = await self.embeddings.aembed_documents(texts_to_embed)
            
            new_q_embedding = np.array(embeddings[-1])
            blacklist_embeddings = np.array(embeddings[:-1])
            
            # Calculate cosine similarities
            similarities = np.dot(blacklist_embeddings, new_q_embedding) / (
                np.linalg.norm(blacklist_embeddings, axis=1) * np.linalg.norm(new_q_embedding)
            )
            
            max_similarity = np.max(similarities)
            logger.info(f"Agent 5: Max semantic similarity: {max_similarity:.4f}")
            
            if max_similarity > 0.82: # Lowered threshold for stricter duplicate rejection
                logger.warning(f"Agent 5: Duplicate detected! Similarity: {max_similarity:.4f}. Re-planning...")
                return {
                    "duplicate_detected": True,
                    "attempted_questions": attempted + [new_q],
                    "next_step": "plan"
                }
            
            # Update topics if this was a core question (not a follow-up)
            new_covered = list(covered)
            new_remaining = list(remaining)
            
            if current_topic and current_topic in new_remaining and "follow-up" not in new_q.lower():
                new_remaining.remove(current_topic)
                new_covered.append(current_topic)
                logger.info(f"Agent 5: Topic [{current_topic}] moved to covered.")
            
            return {
                "asked_questions": asked + [new_q],
                "duplicate_detected": False,
                "covered_topics": new_covered,
                "remaining_topics": new_remaining,
                "next_step": "wait_for_answer"
            }
        except Exception as e:
            logger.error(f"Agent 5 Error: {e}")
            
            # Fallback to basic string match for duplicate detection
            is_duplicate = False
            for prev_q in all_blacklist:
                if new_q.lower().strip() == prev_q.lower().strip():
                    is_duplicate = True
                    break
            
            if is_duplicate:
                return {
                    "duplicate_detected": True,
                    "attempted_questions": attempted + [new_q],
                    "next_step": "plan"
                }

            # Update topics even on embedding error to ensure progression
            new_covered = list(covered)
            new_remaining = list(remaining)
            
            if current_topic and current_topic in new_remaining and "follow-up" not in new_q.lower():
                new_remaining.remove(current_topic)
                new_covered.append(current_topic)
                logger.info(f"Agent 5 (Error Path): Topic [{current_topic}] moved to covered.")
            
            return {
                "asked_questions": asked + [new_q],
                "duplicate_detected": False,
                "covered_topics": new_covered,
                "remaining_topics": new_remaining,
                "next_step": "wait_for_answer"
            }

    # --- Agent 6: Report Generator ---
    async def generate_report(self, state: InterviewState) -> Dict:
        """Aggregates all scores into a final report."""
        history = state.get("answer_history", [])
        
        if not history:
            return {"is_completed": True, "next_step": "end"}
            
        t_scores = [h["evaluation"]["technical_score"] for h in history]
        c_scores = [h["evaluation"]["communication_score"] for h in history]
        d_scores = [h["evaluation"]["knowledge_depth"] for h in history]
        conf_scores = [h["evaluation"]["confidence_score"] for h in history]
        
        avg_t = sum(t_scores) / len(t_scores)
        avg_c = sum(c_scores) / len(c_scores)
        avg_d = sum(d_scores) / len(d_scores)
        avg_conf = sum(conf_scores) / len(conf_scores)
        
        overall = (avg_t * 0.4) + (avg_c * 0.2) + (avg_d * 0.3) + (avg_conf * 0.1)
        
        report = {
            "overall_score": overall,
            "technical_score": avg_t,
            "communication_score": avg_c,
            "knowledge_depth": avg_d,
            "confidence_score": avg_conf,
            "summary": "Interview completed successfully with deep resume-aware analysis.",
            "total_questions": len(history),
            "question_history": [h["question"] for h in history]
        }
        logger.info(f"Agent 6: Final Report Generated. Overall: {overall:.2f}")
        
        return {
            "final_report": report,
            "is_completed": True,
            "next_step": "end"
        }
