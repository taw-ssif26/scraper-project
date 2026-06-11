def build_structure_prompt(page_html: str, user_task: str) -> str:
    return f"""You are a web scraping expert analyzing real HTML.

TASK: {user_task}

HTML:
{page_html}

INSTRUCTIONS:
- Find the REPEATING elements that contain the requested data.
- Look for lists, grids, tables, or card layouts — data is almost always repeated.
- Use EXACT class names from the HTML. Copy them character for character.
- Test your selector mentally: does it match multiple similar elements?
- If class names look randomized or minified, use tag+position selectors instead.
- If you cannot identify reliable selectors, return empty fields object.

RETURN ONLY THIS JSON, nothing else:
{{"fields": {{"field_name": "css_selector"}}}}

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
