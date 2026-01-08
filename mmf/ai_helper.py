# mmf/ai_helper.py
from __future__ import annotations

import os
from dataclasses import dataclass
from typing import Any, Dict, Optional

# Load dotenv if available (no hard dependency)
try:
    from dotenv import load_dotenv  # type: ignore
except Exception:  # pragma: no cover
    load_dotenv = None


@dataclass(frozen=True)
class AIConfig:
    provider: str  # "openai" | "anthropic" | "gemini"
    model: str
    max_tokens: int = 600
    temperature: float = 0.2


def load_env() -> None:
    """
    Loads .env into environment variables if python-dotenv is installed.
    Safe to call multiple times.
    """
    if load_dotenv:
        load_dotenv()


def rewrite_description(cfg: AIConfig, context: Dict[str, Any]) -> str:
    prompt = _prompt_rewrite_description(context)
    return _call_model(cfg, prompt)


def draft_tests(cfg: AIConfig, context: Dict[str, Any]) -> str:
    prompt = _prompt_draft_tests(context)
    return _call_model(cfg, prompt)


def explain_warning(cfg: AIConfig, context: Dict[str, Any], warning: Dict[str, str]) -> str:
    prompt = _prompt_explain_warning(context, warning)
    return _call_model(cfg, prompt)


# -------------------------
# Prompts (boring on purpose)
# -------------------------

def _prompt_rewrite_description(ctx: Dict[str, Any]) -> str:
    m = ctx.get("metric", {})
    return f"""Rewrite the metric description in clear, professional language.

Rules:
- Keep the original meaning.
- 1–2 sentences only.
- Mention unit and grain if provided.
- If tier is V0, it’s okay to say it’s an early proxy.
- Do not invent data sources, numbers, or thresholds.
- Return only the rewritten description text. No bullet points.

Metric:
- id: {m.get("id")}
- name: {m.get("name")}
- tier: {m.get("tier")}
- unit: {m.get("unit")}
- grain: {m.get("grain")}
- current_description: {m.get("description") or ""}
"""


def _prompt_draft_tests(ctx: Dict[str, Any]) -> str:
    m = ctx.get("metric", {})
    d = ctx.get("deterministic", {})
    return f"""Propose practical data quality tests for this metric.

Rules:
- Keep them cheap and generic (null checks, freshness, duplicates, basic range).
- Use the unit and grain.
- Do not invent hard thresholds. If a threshold is needed, use placeholders and explain how to set them.
- Output YAML only: a list under `tests:` items. No extra commentary.

Metric:
- id: {m.get("id")}
- name: {m.get("name")}
- tier: {m.get("tier")}
- unit: {m.get("unit")}
- grain: {m.get("grain")}
Deterministic context:
- score: {d.get("score")}
- gaps: {d.get("gaps")}
"""


def _prompt_explain_warning(ctx: Dict[str, Any], warning: Dict[str, str]) -> str:
    m = ctx.get("metric", {})
    return f"""Explain this validation warning in plain English.

Rules:
- 2–4 short sentences.
- First sentence: what it means.
- Second sentence: why it matters.
- Third sentence: what to do next (concrete action).
- Do not mention internal paths or JSON pointers.

Metric:
- id: {m.get("id")}
- name: {m.get("name")}

Warning:
- code: {warning.get("code")}
- message: {warning.get("message")}
- location: {warning.get("location")}
"""


# -------------------------
# Providers (dotenv keys)
# -------------------------

def _call_model(cfg: AIConfig, prompt: str) -> str:
    provider = (cfg.provider or "").lower().strip()

    if provider == "openai":
        return _call_openai(cfg, prompt)
    if provider == "anthropic":
        return _call_anthropic(cfg, prompt)
    if provider == "gemini":
        return _call_gemini(cfg, prompt)

    raise RuntimeError(f"Unknown AI provider: {cfg.provider}")


def _call_openai(cfg: AIConfig, prompt: str) -> str:
    key = os.getenv("OPENAI_API_KEY")
    if not key:
        raise RuntimeError("OPENAI_API_KEY is not set.")

    # Prefer the official SDK if installed
    try:
        from openai import OpenAI  # type: ignore
        client = OpenAI(api_key=key)

        # Newer SDKs support Responses API
        try:
            resp = client.responses.create(
                model=cfg.model,
                input=prompt,
                temperature=cfg.temperature,
                max_output_tokens=cfg.max_tokens,
            )
            text = getattr(resp, "output_text", None)
            if text:
                return text.strip()
        except Exception:
            pass

        # Fallback: Chat Completions style
        resp = client.chat.completions.create(
            model=cfg.model,
            messages=[{"role": "user", "content": prompt}],
            temperature=cfg.temperature,
            max_tokens=cfg.max_tokens,
        )
        return resp.choices[0].message.content.strip()
    except ImportError:
        raise RuntimeError("OpenAI SDK not installed. Install `openai` or switch provider.")


def _call_anthropic(cfg: AIConfig, prompt: str) -> str:
    key = os.getenv("ANTHROPIC_API_KEY")
    if not key:
        raise RuntimeError("ANTHROPIC_API_KEY is not set.")

    try:
        from anthropic import Anthropic  # type: ignore
        client = Anthropic(api_key=key)
        msg = client.messages.create(
            model=cfg.model,
            max_tokens=cfg.max_tokens,
            temperature=cfg.temperature,
            messages=[{"role": "user", "content": prompt}],
        )
        # Anthropics SDK returns content blocks
        parts = []
        for block in getattr(msg, "content", []) or []:
            text = getattr(block, "text", None)
            if text:
                parts.append(text)
        out = "\n".join(parts).strip()
        return out or str(msg)
    except ImportError:
        raise RuntimeError("Anthropic SDK not installed. Install `anthropic` or switch provider.")


def _call_gemini(cfg: AIConfig, prompt: str) -> str:
    key = os.getenv("GOOGLE_API_KEY") or os.getenv("GEMINI_API_KEY")
    if not key:
        raise RuntimeError("GOOGLE_API_KEY (or GEMINI_API_KEY) is not set.")

    try:
        import google.generativeai as genai  # type: ignore
        genai.configure(api_key=key)
        model = genai.GenerativeModel(cfg.model)
        resp = model.generate_content(prompt)
        text = getattr(resp, "text", None)
        if text:
            return text.strip()
        return str(resp)
    except ImportError:
        raise RuntimeError("Gemini SDK not installed. Install `google-generativeai` or switch provider.")
