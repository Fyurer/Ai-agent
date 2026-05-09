#!/usr/bin/env python3
"""
AI Agent Bot — AGMK 3-mis boyitish fabrika mexanigi uchun
aiogram + Telethon (userbot) + Groq + Gemini + ElevenLabs TTS + SQLite
"""

import asyncio
import logging
import os
import sys

from dotenv import load_dotenv
load_dotenv()

from aiogram import Bot, Dispatcher, F
from aiogram.types import Message
from aiogram.filters import Command
from aiogram.enums import ParseMode
from aiogram.client.default import DefaultBotProperties

from database import Database
from userbot import UserBot
from ai_services import AIServices
from handlers import register_handlers

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler("bot.log", encoding="utf-8"),
    ]
)
log = logging.getLogger(__name__)

# ── Config ───────────────────────────────────────────────────
BOT_TOKEN   = os.getenv("BOT_TOKEN", "")
OWNER_ID    = int(os.getenv("OWNER_CHAT_ID", "0"))
TG_API_ID   = int(os.getenv("TG_API_ID", "0"))
TG_API_HASH = os.getenv("TG_API_HASH", "")
TG_PHONE    = os.getenv("TG_PHONE", "")

async def main():
    log.info("🤖 AI Agent (AGMK Mexanik) ishga tushmoqda...")

    # Database
    db = Database()
    await db.init()
    log.info("✅ Database tayyor")

    # AI Services (mexanik uchun)
    ai = AIServices()

    # UserBot (Telethon)
    userbot = UserBot(TG_API_ID, TG_API_HASH, TG_PHONE)
    await userbot.start()
    log.info("✅ UserBot ulandi")

    # Aiogram Bot
    bot = Bot(
        token=BOT_TOKEN,
        default=DefaultBotProperties(parse_mode=ParseMode.MARKDOWN)
    )
    dp = Dispatcher()

    # Handlerlarni ro'yxatdan o'tkazish
    register_handlers(dp, db, ai, userbot, OWNER_ID)

    log.info("✅ Bot ishga tushdi! AGMK 3-MB mexanigi AI yordamchisi tayyor 🏭")

    try:
        await dp.start_polling(bot, allowed_updates=["message", "callback_query"])
    finally:
        await userbot.stop()
        await bot.session.close()

if __name__ == "__main__":
    asyncio.run(main())
