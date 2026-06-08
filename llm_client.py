import os
from groq import Groq

def get_client() -> Groq:
    return Groq(api_key=os.environ.get("GROQ_API_KEY"))

def get_model() -> str:
    return os.environ.get("LLM_MODEL", "openai/gpt-oss-120b")
