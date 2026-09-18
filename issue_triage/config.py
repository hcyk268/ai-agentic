"""Runtime configuration and OpenAI-compatible client creation."""

from __future__ import annotations

import os
from pathlib import Path

from dotenv import load_dotenv
from openai import OpenAI

PACKAGE_DIR = Path(__file__).resolve().parent
PROJECT_DIR = PACKAGE_DIR.parent


def load_environment() -> None:
    load_dotenv(PROJECT_DIR / ".env")


def model_name() -> str:
    load_environment()
    model = os.getenv("OPENAI_MODEL")
    if not model:
        raise RuntimeError("Thiếu OPENAI_MODEL trong .env")
    return model


def base_url() -> str:
    load_environment()
    value = os.getenv("OPENAI_BASE_URL")
    if not value:
        raise RuntimeError("Thiếu OPENAI_BASE_URL trong .env")
    return value


def openai_client() -> OpenAI:
    load_environment()
    api_key = os.getenv("OPENAI_API_KEY")
    url = os.getenv("OPENAI_BASE_URL")
    if not api_key:
        raise RuntimeError("Thiếu OPENAI_API_KEY trong .env")
    if not url:
        raise RuntimeError("Thiếu OPENAI_BASE_URL trong .env")
    return OpenAI(api_key=api_key, base_url=url)
