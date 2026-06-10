import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import uvicorn

if __name__ == "__main__":
    print("Starting AI Web Scraper...")
    print("Open your browser at http://127.0.0.1:8000\n")
    uvicorn.run(
        "ui.interface:app",
        host="127.0.0.1",
        port=8000,
        reload=False,
    )
