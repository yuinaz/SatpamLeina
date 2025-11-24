import os
from dotenv import load_dotenv
from flask import Flask

def load_config(app: Flask):
    """Load konfigurasi dari environment atau file .env ke Flask app."""
    load_dotenv()

    # Konfigurasi dasar bot
    app.config["DISCORD_BOT_TOKEN"] = os.getenv("DISCORD_BOT_TOKEN", "")
    app.config["OCR_BANNED_KEYWORDS"] = os.getenv("OCR_BANNED_KEYWORDS", "phishing,scam,penipuan").split(",")

    # Log level (opsional)
    app.config["LOG_LEVEL"] = os.getenv("LOG_LEVEL", "INFO")

    # Tambahkan konfigurasi lain jika dibutuhkan
    # app.config["DATABASE_URL"] = os.getenv("DATABASE_URL", "sqlite:///data.db")
