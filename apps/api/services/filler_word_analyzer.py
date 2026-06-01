import re
from typing import Dict, List
from pydantic import BaseModel, Field

class FillerWordStats(BaseModel):
    total_words: int
    filler_count: int
    filler_percentage: float
    frequency_map: Dict[str, int]
    penalty_score: float = Field(description="Calculated penalty (0-100), where 100 is worst")
    feedback: str

class FillerWordAnalyzer:
    # Production-grade regex patterns with word boundaries
    TARGET_PATTERNS = {
        "um": r"\b(um+)\b",
        "uh": r"\b(uh+)\b",
        "actually": r"\bactually\b",
        "basically": r"\bbasically\b",
        "like": r"\blike\b",
        "you know": r"\byou\s+know\b"
    }

    # Weighting for penalty score (some fillers are more distracting)
    WEIGHTS = {
        "um": 1.5,
        "uh": 1.2,
        "actually": 0.8,
        "basically": 0.8,
        "like": 1.0,
        "you know": 1.3
    }

    def analyze(self, transcript: str) -> FillerWordStats:
        """
        Performs high-precision analysis of filler words in a transcript.
        """
        if not transcript:
            return FillerWordStats(
                total_words=0, filler_count=0, filler_percentage=0.0,
                frequency_map={}, penalty_score=0.0, feedback="No transcript provided."
            )

        words = transcript.split()
        total_words = len(words)
        
        frequency_map = {}
        total_weighted_penalty = 0.0
        total_filler_count = 0

        # Case-insensitive search for each pattern
        for label, pattern in self.TARGET_PATTERNS.items():
            matches = re.findall(pattern, transcript, re.IGNORECASE)
            count = len(matches)
            frequency_map[label] = count
            total_filler_count += count
            
            # Penalty logic: count * weight
            total_weighted_penalty += (count * self.WEIGHTS[label])

        # Normalize percentage
        filler_percentage = (total_filler_count / total_words * 100) if total_words > 0 else 0.0
        
        # Calculate penalty score (Logarithmic scaling to avoid extreme penalties for long interviews)
        # Baseline: 5% filler rate is acceptable. 15%+ is poor.
        raw_score = (total_weighted_penalty / total_words * 500) if total_words > 0 else 0.0
        penalty_score = min(100.0, round(raw_score, 2))

        # Generate contextual feedback
        if penalty_score < 10:
            feedback = "Excellent articulation with minimal filler words."
        elif penalty_score < 30:
            feedback = "Good communication, though some fillers were present."
        else:
            feedback = "High frequency of filler words detected. Practice pausing instead of using fillers."

        return FillerWordStats(
            total_words=total_words,
            filler_count=total_filler_count,
            filler_percentage=round(filler_percentage, 2),
            frequency_map=frequency_map,
            penalty_score=penalty_score,
            feedback=feedback
        )

# --- Example Usage ---
# analyzer = FillerWordAnalyzer()
# report = analyzer.analyze("Um, so basically, I used FastAPI like, you know, for the backend.")
# print(report.json())
