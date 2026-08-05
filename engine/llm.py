"""Single place where we talk to Gemini.

Two rules here. Everything comes back as JSON, and everything is validated
against a Pydantic schema before it leaves this module. Models drift on
schema compliance and an unvalidated parse will break the demo at the worst
possible moment.
"""

import json
import os
import google.generativeai as genai

CHAT_MODEL = "gemini-2.0-flash-lite"
EMBED_MODEL = "models/text-embedding-004"

_configured = False


def configure(api_key: str):
    global _configured
    genai.configure(api_key=api_key)
    _configured = True


def get_api_key(streamlit_secrets=None, sidebar_value: str = "") -> str:
    """Three places the key can come from, in order of preference."""
    if sidebar_value:
        return sidebar_value
    if streamlit_secrets is not None:
        try:
            key = streamlit_secrets.get("GEMINI_API_KEY", "")
            if key:
                return key
        except Exception:
            pass
    return os.environ.get("GEMINI_API_KEY", "")


def generate_json(prompt: str, schema_cls, temperature: float = 0.1):
    """Call the model, parse JSON, validate against the schema. One retry."""
    model = genai.GenerativeModel(
        CHAT_MODEL,
        generation_config={
            "response_mime_type": "application/json",
            "temperature": temperature,
        },
    )

    last_error = None
    for attempt in range(2):
        try:
            resp = model.generate_content(prompt)
            raw = resp.text.strip()
            if raw.startswith("```"):
                raw = raw.split("```")[1]
                if raw.startswith("json"):
                    raw = raw[4:]
            data = json.loads(raw)
            return schema_cls(**data), None
        except Exception as e:
            last_error = e
            prompt = prompt + "\n\nYour previous reply was not valid JSON matching the schema. Return only valid JSON."

    return None, f"Model output could not be parsed after two attempts: {last_error}"


def embed_documents(texts):
    """Batch embed catalogue entries."""
    result = genai.embed_content(
        model=EMBED_MODEL, content=texts, task_type="retrieval_document"
    )
    return result["embedding"]


def embed_query(text: str):
    result = genai.embed_content(
        model=EMBED_MODEL, content=text, task_type="retrieval_query"
    )
    return result["embedding"]
