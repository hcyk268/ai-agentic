"""
LLM Configuration and initialization helper.
"""

import os
from dotenv import load_dotenv
from langchain_openai import ChatOpenAI

load_dotenv()


def get_llm(temperature: float = 0.0) -> ChatOpenAI:
    """Khởi tạo đối tượng ChatOpenAI tương thích với endpoint cấu hình trong .env."""
    api_key = os.getenv("OPENAI_API_KEY", "dummy")
    base_url = os.getenv("OPENAI_BASE_URL", "http://localhost:20128/v1")
    model_name = os.getenv("OPENAI_MODEL", "ag/gemini-3.8-flash-medium")

    return ChatOpenAI(
        model=model_name,
        api_key=api_key,
        base_url=base_url,
        temperature=temperature,
        timeout=45.0,
        max_retries=2
    )
