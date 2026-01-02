#!/usr/bin/env python
"""
Startup script for Railway deployment.
Reads PORT from environment and starts uvicorn.
"""
import os
import subprocess
import sys

port = os.environ.get("PORT", "8000")

subprocess.run([
    sys.executable, "-m", "uvicorn",
    "app.main:app",
    "--host", "0.0.0.0",
    "--port", port
])
