import os
from dotenv import load_dotenv

load_dotenv()

TOKEN = os.getenv("TELEGRAM_TOKEN")
CHAT_ID = os.getenv("CHAT_ID")
AI_KEY = os.getenv("OPENROUTER_KEY")
FASCIA_ORARIA = (6, 21)