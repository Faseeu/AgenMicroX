# config/config.py
import os
from dotenv import load_dotenv

load_dotenv()

GROQ_API_KEY = os.getenv("GROQ_API_KEY")
GROQ_API_BASE = "https://api.groq.com/openai/v1"

SEARXNG_INSTANCE = os.getenv("SEARXNG_INSTANCE", "https://searx.be")  # Replace with your preferred SearxNG instance or use an environment variable

# Add more configuration variables as needed
