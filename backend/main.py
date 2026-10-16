"""Development/deployment launcher.

ngrok is opt-in via ENABLE_NGROK=true. Production should normally sit behind
a managed HTTPS reverse proxy or platform ingress.
"""
from __future__ import annotations

import os
import sys

import uvicorn


def main() -> None:
    host = os.getenv("HOST", "0.0.0.0")
    port = int(os.getenv("PORT", "8000"))
    reload_enabled = os.getenv("UVICORN_RELOAD", "false").lower() == "true"

    if os.getenv("ENABLE_NGROK", "false").lower() == "true":
        try:
            from pyngrok import ngrok

            public_url = ngrok.connect(port).public_url
            print(f"Public URL: {public_url}")
        except ImportError:
            print("Warning: ENABLE_NGROK=true but pyngrok not installed")

    sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
    uvicorn.run("app:app", host=host, port=port, reload=reload_enabled)


if __name__ == "__main__":
    main()
