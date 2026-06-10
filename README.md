# AI Web Scraper

Natural language web scraper. Give it a URL and describe what you want — it extracts structured data and saves CSV + JSON.

## Features
- Plain English extraction tasks
- Human-like browsing via Playwright + stealth
- Captcha detection → pauses → you solve → resumes
- Pagination handling
- Groq or OpenRouter as free LLM backends
- Simple Gradio UI

## Setup

### 1. Install dependencies
```bash
pip install -r requirements.txt
playwright install chromium
```

### 2. Configure environment
```bash
cp .env.example .env
# Edit .env and add your Groq or OpenRouter API key
```

Get a free Groq key at: https://console.groq.com  
Get a free OpenRouter key at: https://openrouter.ai

### 3. Run
```bash
python main.py
```

Opens at http://127.0.0.1:7860

## Test Sites (safe to scrape)
- http://books.toscrape.com — books with prices and ratings
- http://quotes.toscrape.com — quotes with authors and tags

## Example Tasks
- "Extract all book titles, prices, and star ratings"
- "Get all quote text and author names"
- "Find all product names and their prices"

## Switching LLM Provider
Edit `.env`:
```
LLM_PROVIDER=openrouter
LLM_MODEL=meta-llama/llama-3.1-8b-instruct:free
OPENROUTER_API_KEY=your_key
```

## Project Structure
```
scraper-project/
├── main.py               # Entry point
├── config.py             # All settings
├── orchestrator.py       # Scraping state machine
├── browser/
│   ├── engine.py         # Playwright browser control
│   ├── dom_cleaner.py    # HTML → clean text
│   └── captcha_detector.py
├── extractor/
│   ├── llm_client.py     # Groq / OpenRouter unified client
│   └── prompt_builder.py
├── output/
│   └── writer.py         # CSV + JSON output
└── ui/
    └── interface.py      # Gradio UI
```
