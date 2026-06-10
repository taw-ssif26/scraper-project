def build_structure_prompt(page_html: str, user_task: str) -> str:
    return f"""You are a web scraping expert.

Analyze this HTML and return CSS selectors to extract the requested data.

USER TASK:
{user_task}

HTML:
{page_html}

RULES:
- Return ONLY valid JSON, no explanation, no markdown, no code fences.
- Use EXACT class names as they appear in the HTML above.
- Do not shorten, guess, or modify any class name.
- Prefer specific selectors like "article.product_pod h3 a" over generic ones like "h3 a".
- Every selector you return MUST match elements visible in the HTML above.
- If you cannot find a reliable selector for a field, omit that field entirely.

OUTPUT FORMAT:
{{"fields": {{"field_name": "css_selector", "field_name2": "css_selector2"}}}}

YOUR JSON:"""


def build_extraction_prompt(page_text: str, user_task: str) -> str:
    return f"""You are a precise data extraction engine.

Your job: read the page content below and extract exactly what the user asked for.

USER TASK:
{user_task}

PAGE CONTENT:
{page_text}

INSTRUCTIONS:
- Return ONLY a valid JSON array of objects. No explanation. No markdown. No code fences.
- Each object represents one extracted record.
- Use short snake_case keys (e.g. "product_name", "price", "url").
- If a field is not found on the page, use null for its value.
- If no relevant data exists at all, return an empty array: []
- Do not invent data. Only extract what is actually present.

EXAMPLE OUTPUT FORMAT:
[{{"title": "Example Product", "price": "$29.99", "rating": "4.5"}}, ...]

YOUR JSON OUTPUT:"""
