import re
from typing import List

PERSONA_PROMPTS = {
    "Friendly Companion": (
        "You are Nova, an ultra-smart, warm, witty, and deeply caring companion speaking to your close friend. "
        "Your voice is lively, conversational, and natural. Use natural conversational phrases like 'Oh hey!', "
        "'Totally get you', 'Here's the scoop', and conversational cadence. Be empathetic and direct in 1-2 sentences. "
        "Never use robotic bullet lists or formal corporate jargon."
    ),
    "Creative Genius": (
        "You are Nova, an imaginative, vibrant, and artistic creative collaborator. "
        "Offer vivid, inspiring, and sharp insights with enthusiastic warmth in 1-2 captivating sentences."
    ),
    "Executive Assistant": (
        "You are Nova, an ultra-crisp, efficient, and proactive chief-of-staff. "
        "Deliver clear, high-precision answers with polite warmth and zero fluff in 1-2 concise sentences."
    )
}

class VoiceEngine:
    """
    Handles natural human-like prosody, persona modulation,
    and speech sanitization for zero-robotic conversational TTS.
    """
    def __init__(self, persona: str = "Friendly Companion"):
        self.persona = persona

    def get_system_prompt(self) -> str:
        """Returns tailored system prompt for chosen human companion persona."""
        return PERSONA_PROMPTS.get(self.persona, PERSONA_PROMPTS["Friendly Companion"])

    def sanitize_for_speech(self, text: str) -> str:
        """
        Strips markdown asterisks, hashtags, code blocks, and brackets so
        TTS reads smooth, expressive natural speech instead of punctuation.
        """
        if not text:
            return ""
        
        # Remove code blocks and inline code
        clean = re.sub(r'```.*?```', '', text, flags=re.DOTALL)
        clean = re.sub(r'`([^`]+)`', r'\1', clean)
        
        # Remove markdown headers, bold, italics
        clean = re.sub(r'[#*_~>]+', ' ', clean)
        
        # Remove URLs
        clean = re.sub(r'https?://\S+', 'link', clean)
        
        # Normalize whitespace
        clean = re.sub(r'\s+', ' ', clean).strip()
        return clean

    def split_into_speech_chunks(self, text: str) -> List[str]:
        """
        Splits paragraph into natural vocal breath chunks for streaming playback.
        """
        sanitized = self.sanitize_for_speech(text)
        if not sanitized:
            return []
        
        # Split on natural clause boundaries (. ! ? ; or comma for long sentences)
        sentences = re.split(r'(?<=[.!?]) +', sanitized)
        return [s.strip() for s in sentences if s.strip()]


_voice_engine = None


def get_voice_engine(persona: str = "Friendly Companion") -> VoiceEngine:
    """Returns the singleton VoiceEngine instance."""
    global _voice_engine
    if _voice_engine is None:
        _voice_engine = VoiceEngine(persona=persona)
    return _voice_engine
