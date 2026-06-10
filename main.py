import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import uvicorn

if __name__ == "__main__":
    port = int(os.getenv("PORT", 8000))
    print(f"Starting AI Web Scraper on port {port}...")
    uvicorn.run(
        "ui.interface:app",
        host="0.0.0.0",
        port=port,
        reload=False,
    )
