"""Vercel serverless entry point for Cantonese Learning App."""

import os
import sys

# Ensure project root is on the path so "backend" package is importable
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Mark Vercel environment so backend skips static file routes
os.environ["VERCEL"] = "1"

from dotenv import load_dotenv
load_dotenv()

from backend.server import app
