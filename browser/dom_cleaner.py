import re

# Tags whose entire content we discard
_STRIP_TAGS = [
    "script", "style", "noscript", "svg", "iframe",
    "head", "meta", "link", "header", "footer", "nav"
]

# Tags we keep as structural anchors (class names matter for CSS selectors)
_KEEP_TAGS = {"div", "span", "a", "li", "ul", "ol", "article", "section", "p", "h1", "h2", "h3", "h4", "td", "tr", "table"}

# Max chars sent to LLM — skeleton can be longer since it's structured
_MAX_CHARS_SKELETON  = 4_000
_MAX_CHARS_TEXT      = 6_000


def clean_html(raw_html: str) -> str:
    """
    Plain text mode — for fallback LLM data extraction.
    Strips everything including tags. LLM reads content only.
    Used when CSS selector extraction fails and we fall back to text parsing.
    """
    text = raw_html

    for tag in _STRIP_TAGS:
        text = re.sub(rf"<{tag}[\s\S]*?</{tag}>", " ", text, flags=re.IGNORECASE)

    # Strip all tags including attributes
    text = re.sub(r"<[^>]+>", " ", text)

    text = _decode_entities(text)
    text = re.sub(r"\s+", " ", text).strip()

    if len(text) > _MAX_CHARS_TEXT:
        text = text[:_MAX_CHARS_TEXT] + "... [trimmed]"

    return text


def extract_html_skeleton(raw_html: str) -> str:
    """
    Skeleton mode — for structure learning.
    Keeps tags + class/id/href attributes so LLM can identify real CSS selectors.
    Strips tag content (text nodes) to reduce noise and token count.

    Output looks like:
        <div class="result"><span class="title"><a href="/item">...</a></span></div>

    The LLM reads this structure and returns accurate CSS selectors.
    """
    text = raw_html

    # Remove noise blocks entirely
    for tag in _STRIP_TAGS:
        text = re.sub(rf"<{tag}[\s\S]*?</{tag}>", "", text, flags=re.IGNORECASE)

    # Strip inline text between tags — keep only the tags themselves
    # Replace text nodes with ... to preserve readability
    text = re.sub(r">([^<]{1,80})<", r">...<", text)

    # Strip attributes we don't need — keep only class, id, href, data-testid
    def strip_attrs(match):
        tag_content = match.group(0)
        # Keep only useful attributes
        kept = re.findall(r'(?:class|id|href|data-testid)=["\'][^"\']*["\']', tag_content)
        tag_name = re.match(r"</?(\w+)", tag_content)
        if not tag_name:
            return ""
        name = tag_name.group(1).lower()
        if name not in _KEEP_TAGS and not tag_content.startswith("</"):
            return ""
        if tag_content.startswith("</"):
            return tag_content  # keep closing tags as-is
        attrs = " ".join(kept)
        return f"<{name} {attrs}>" if attrs else f"<{name}>"

    text = re.sub(r"<[^>]+>", strip_attrs, text)

    # Collapse excessive whitespace and blank lines
    text = re.sub(r"\n{3,}", "\n\n", text)
    text = re.sub(r"[ \t]+", " ", text)
    text = text.strip()

    if len(text) > _MAX_CHARS_SKELETON:
        text = text[:_MAX_CHARS_SKELETON] + "\n... [trimmed]"

    return text


def _decode_entities(text: str) -> str:
    return (
        text.replace("&amp;", "&")
            .replace("&lt;", "<")
            .replace("&gt;", ">")
            .replace("&quot;", '"')
            .replace("&#39;", "'")
            .replace("&nbsp;", " ")
    )
