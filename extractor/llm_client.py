import json
import re
import asyncio
import httpx
import config
from extractor.prompt_builder import build_extraction_prompt, build_structure_prompt


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


async def _call_llm(prompt: str, max_tokens: int = 2048) -> str:
    """Base LLM call. Returns raw text or empty string on failure."""
    url = _get_base_url() + "/chat/completions"
    payload = {
        "model": config.LLM_MODEL,
        "messages": [{"role": "user", "content": prompt}],
        "temperature": 0,
        "max_tokens": max_tokens,
    }
    headers = {
        "Authorization": "Bearer " + _get_api_key(),
        "Content-Type": "application/json",
    }
    for attempt in range(3):
        try:
            async with httpx.AsyncClient(timeout=60) as client:
                response = await client.post(url, json=payload, headers=headers)
                if response.status_code == 429:
                    wait = 10 * (attempt + 1)
                    print(f"[LLM] Rate limited. Waiting {wait}s...")
                    await asyncio.sleep(wait)
                    continue
                response.raise_for_status()
                data = response.json()
                return data["choices"][0]["message"]["content"].strip()
        except Exception as e:
            print(f"[LLM] Call failed (attempt {attempt + 1}): {type(e).__name__}: {e}")
            if attempt < 2:
                await asyncio.sleep(3)
    return ""


async def extract_data(page_text: str, user_task: str) -> list[dict]:
    """
    Direct LLM text extraction — no CSS selectors.
    Reliable on any site. Used as fallback when selector extraction fails.
    """
    prompt = build_extraction_prompt(page_text, user_task)
    raw = await _call_llm(prompt, max_tokens=2048)
    if not raw:
        return []
    return _parse_json_array(raw)


async def learn_structure(page_html: str, user_task: str) -> dict:
    """
    Ask LLM to identify CSS selectors for the requested data.
    Returns structure dict or empty dict on failure.
    """
    prompt = build_structure_prompt(page_html, user_task)
    raw = await _call_llm(prompt, max_tokens=512)
    if not raw:
        return {}
    return _parse_json_object(raw)


def _parse_json_array(raw: str) -> list[dict]:
    raw = re.sub(r"```(?:json)?", "", raw).strip()
    start = raw.find("[")
    end   = raw.rfind("]")
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


def _parse_json_object(raw: str) -> dict:
    raw = re.sub(r"```(?:json)?", "", raw).strip()
    start = raw.find("{")
    end   = raw.rfind("}")
    if start == -1 or end == -1:
        return {}
    try:
        result = json.loads(raw[start:end + 1])
        if isinstance(result, dict) and "fields" in result:
            return result
        return {}
    except json.JSONDecodeError:
        return {}
