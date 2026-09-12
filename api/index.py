import os
import sys

# Add parent directory to python path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app import app

# Export app for Vercel serverless execution
app = app
