import json
import re
import httpx
import config
from extractor.prompt_builder import build_extraction_prompt
import asyncio

def _get_base_url():
    if config.LLM_PROVIDER == "groq":
        return "https://api.groq.com/openai/v1"
    elif config.LLM_PROVIDER == "openrouter":
        return "https://openrouter.ai/api/v1"
    raise ValueError(f"Unknown LLM provider: {config.LLM_PROVIDER}")


def _get_api_key():
    if config.LLM_PROVIDER == "groq":
        return config.GROQ_API_KEY
    elif config.LLM_PROVIDER == "openrouter":
        return config.OPENROUTER_API_KEY
    raise ValueError(f"Unknown LLM provider: {config.LLM_PROVIDER}")


async def extract_data(page_text, user_task):
    prompt = build_extraction_prompt(page_text, user_task)
    url = _get_base_url() + "/chat/completions"
    payload = {
        "model": config.LLM_MODEL,
        "messages": [{"role": "user", "content": prompt}],
        "temperature": 0,
        "max_tokens": 2048,
    }
    headers = {
        "Authorization": "Bearer " + _get_api_key(),
        "Content-Type": "application/json",
    }
    try:
        async with httpx.AsyncClient(timeout=60) as client:
            response = await client.post(url, json=payload, headers=headers)
            response.raise_for_status()
            data = response.json()
            raw = data["choices"][0]["message"]["content"].strip()
            return _parse_json(raw)
    except Exception as e:
        print(f"[LLM] Extraction failed: {e}")
        return []


def _parse_json(raw):
    raw = re.sub(r"```(?:json)?", "", raw).strip()
    start = raw.find("[")
    end = raw.rfind("]")
    if start == -1 or end == -1:
        print(f"[LLM] No JSON array found: {raw[:200]}")
        return []
    try:
        result = json.loads(raw[start:end + 1])
        if isinstance(result, list):
            return result
        if isinstance(result, dict):
            return [result]
        return []
    except json.JSONDecodeError as e:
        print(f"[LLM] JSON parse error: {e}")
        return []
async def learn_structure(page_text: str, user_task: str) -> dict:
    """
    Ask LLM to identify CSS selectors for the requested data.
    Returns structure dict or empty dict on failure.
    """
    from extractor.prompt_builder import build_structure_prompt
    prompt = build_structure_prompt(page_text, user_task)
    url = _get_base_url() + "/chat/completions"
    payload = {
        "model": config.LLM_MODEL,
        "messages": [{"role": "user", "content": prompt}],
        "temperature": 0,
        "max_tokens": 512,
    }
    headers = {
        "Authorization": "Bearer " + _get_api_key(),
        "Content-Type": "application/json",
    }
    try:
        async with httpx.AsyncClient(timeout=60) as client:
            response = await client.post(url, json=payload, headers=headers)
            response.raise_for_status()
            data = response.json()
            raw = data["choices"][0]["message"]["content"].strip()
            return _parse_structure(raw)
    except Exception as e:
        print(f"[LLM] Structure learning failed: {e}")
        return {}


def _parse_structure(raw: str) -> dict:
    import re
    raw = re.sub(r"```(?:json)?", "", raw).strip()
    start = raw.find("{")
    end = raw.rfind("}")
    if start == -1 or end == -1:
        return {}
    try:
        result = json.loads(raw[start:end + 1])
        if isinstance(result, dict) and "fields" in result:
            return result
        return {}
    except json.JSONDecodeError:
        return {}
