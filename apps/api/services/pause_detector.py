from typing import List, Dict, Optional
from pydantic import BaseModel, Field

class PauseMetrics(BaseModel):
    average_pause_duration: float = Field(description="Average duration of pauses in seconds")
    longest_pause: float = Field(description="Longest single pause in seconds")
    pause_frequency: float = Field(description="Pauses per minute of speech")
    total_silence_duration: float
    fluency_score: float = Field(description="Score from 0-100, where 100 is perfectly fluent")
    feedback: str

class PauseDetector:
    def __init__(self, silence_threshold: float = 0.8):
        """
        silence_threshold: Gaps larger than this (in seconds) are considered 'pauses'.
        Gaps smaller than this are considered natural word boundaries.
        """
        self.silence_threshold = silence_threshold

    def analyze_timestamps(self, segments: List[Dict]) -> PauseMetrics:
        """
        Analyzes Whisper segments (which contain 'start' and 'end' times).
        Example segment: {'start': 0.0, 'end': 2.5, 'text': '...'}
        """
        if not segments or len(segments) < 2:
            return PauseMetrics(
                average_pause_duration=0.0, longest_pause=0.0,
                pause_frequency=0.0, total_silence_duration=0.0,
                fluency_score=100.0, feedback="Not enough speech data to analyze."
            )

        pauses = []
        total_duration = segments[-1]['end'] - segments[0]['start']
        
        # Calculate gaps between segments
        for i in range(len(segments) - 1):
            gap = segments[i+1]['start'] - segments[i]['end']
            if gap >= self.silence_threshold:
                pauses.append(gap)

        if not pauses:
            return PauseMetrics(
                average_pause_duration=0.0, longest_pause=0.0,
                pause_frequency=0.0, total_silence_duration=0.0,
                fluency_score=100.0, feedback="Highly fluent speech with no significant pauses."
            )

        avg_pause = sum(pauses) / len(pauses)
        max_pause = max(pauses)
        total_silence = sum(pauses)
        
        # Pauses per minute
        duration_minutes = total_duration / 60
        pause_freq = len(pauses) / duration_minutes if duration_minutes > 0 else 0

        # --- Scoring Logic ---
        # 1. Penalty for frequency (ideal is 2-5 natural pauses per minute)
        # 2. Penalty for duration (pauses > 3s are distracting)
        
        freq_penalty = max(0, (pause_freq - 8) * 5) # Penalty starts after 8 pauses/min
        duration_penalty = max(0, (avg_pause - 1.5) * 10) # Penalty starts after 1.5s avg
        long_pause_penalty = max(0, (max_pause - 4.0) * 15) # Heavy penalty for >4s pauses

        fluency_score = max(0, 100 - (freq_penalty + duration_penalty + long_pause_penalty))

        # Contextual Feedback
        if max_pause > 5.0:
            feedback = "Detected very long pauses (over 5s). This may indicate hesitation or technical issues."
        elif avg_pause > 2.0:
            feedback = "Speech pace is slow with significant thinking time between sentences."
        elif fluency_score > 85:
            feedback = "Excellent fluency with natural, well-timed pauses."
        else:
            feedback = "Communication is generally clear, but pause frequency could be reduced for better flow."

        return PauseMetrics(
            average_pause_duration=round(avg_pause, 2),
            longest_pause=round(max_pause, 2),
            pause_frequency=round(pause_freq, 2),
            total_silence_duration=round(total_silence, 2),
            fluency_score=round(fluency_score, 2),
            feedback=feedback
        )

# --- Integration Example ---
# detector = PauseDetector()
# results = detector.analyze_timestamps([
#     {'start': 0.0, 'end': 2.0, 'text': 'I am a developer.'},
#     {'start': 5.0, 'end': 7.0, 'text': 'I work with Python.'} # 3 second gap
# ])
