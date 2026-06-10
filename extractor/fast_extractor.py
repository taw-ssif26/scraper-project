from playwright.async_api import Page


async def extract_with_structure(page: Page, structure: dict) -> list[dict]:
    """
    Use cached CSS selectors to extract data directly.
    No LLM call. Pure Playwright.
    Returns list of records or empty list if structure seems broken.
    """
    fields = structure.get("fields", {})
    if not fields:
        return []

    # Find the count of the first field to know how many records exist
    first_selector = list(fields.values())[0]
    try:
        elements = await page.query_selector_all(first_selector)
        count = len(elements)
    except Exception:
        return []

    if count == 0:
        return []

    # Extract each field for all records
    records = [{} for _ in range(count)]

    for field_name, selector in fields.items():
        try:
            elements = await page.query_selector_all(selector)
            for i, el in enumerate(elements):
                if i >= count:
                    break
                text = await el.inner_text()
                records[i][field_name] = text.strip()
        except Exception:
            continue

    # Filter out completely empty records
    records = [r for r in records if any(v for v in r.values())]
    return records


def structure_seems_broken(records: list[dict], expected_min: int = 1) -> bool:
    """
    Returns True if extraction returned suspiciously few results.
    This triggers a new LLM call to re-learn the structure.
    """
    return len(records) < expected_min
