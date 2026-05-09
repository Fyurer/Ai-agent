#!/usr/bin/env python3
"""
AI Agent Bot — AGMK 3-mis boyitish fabrika mexanigi
Railway platformasi uchun optimallashtirilgan
"""

import asyncio
import logging
import os
import sys

from dotenv import load_dotenv
load_dotenv()

from aiogram import Bot, Dispatcher
from aiogram.enums import ParseMode
from aiogram.client.default import DefaultBotProperties

from database import Database
from userbot import UserBot
from ai_services import AIServices
from handlers import register_handlers

# ── Logging ───────────────────────────────────────────────────
log_handlers = [logging.StreamHandler(sys.stdout)]
try:
    log_handlers.append(logging.FileHandler("bot.log", encoding="utf-8"))
except Exception:
    pass

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s — %(message)s",
    handlers=log_handlers
)
log = logging.getLogger(__name__)

BOT_TOKEN   = os.getenv("BOT_TOKEN", "")
OWNER_ID    = int(os.getenv("OWNER_CHAT_ID", "0"))
TG_API_ID   = int(os.getenv("TG_API_ID", "0"))
TG_API_HASH = os.getenv("TG_API_HASH", "")
TG_PHONE    = os.getenv("TG_PHONE", "")


def check_env():
    missing = [k for k, v in {
        "BOT_TOKEN": BOT_TOKEN,
        "OWNER_CHAT_ID": str(OWNER_ID),
        "TG_API_ID": str(TG_API_ID),
        "TG_API_HASH": TG_API_HASH,
        "GROQ_API_KEY": os.getenv("GROQ_API_KEY", ""),
    }.items() if not v or v == "0"]
    if missing:
        log.warning(f"⚠️ ENV yetishmayapti: {', '.join(missing)}")
    else:
        log.info("✅ Asosiy ENV o'zgaruvchilari ok")
    for k, label in {
        "GEMINI_API_KEY": "Gemini",
        "ELEVENLABS_API_KEY": "ElevenLabs TTS",
        "WEATHER_API_KEY": "Ob-havo",
        "TG_SESSION_STRING": "Railway session",
        "AUTO_REPLY_MODE": "AutoReply rejimi",
    }.items():
        val = os.getenv(k, "")
        log.info(f"  {'✅' if val else '—'} {label}: {val[:8]+'...' if val and len(val)>8 else val or 'yoq'}")


async def main():
    log.info("🚀 AI Agent (AGMK Mexanik) ishga tushmoqda...")
    check_env()

    db = Database()
    await db.init()
    log.info("✅ Database tayyor")

    ai = AIServices()

    # Bot ni avval yaratamiz (AutoReply xabarnomasi uchun kerak)
    bot = Bot(
        token=BOT_TOKEN,
        default=DefaultBotProperties(parse_mode=ParseMode.MARKDOWN)
    )

    # UserBot + AutoReply
    userbot = UserBot(TG_API_ID, TG_API_HASH, TG_PHONE)
    await userbot.start(bot_instance=bot)

    dp = Dispatcher()
    register_handlers(dp, db, ai, userbot, OWNER_ID)

    log.info("🤖 Bot ishga tushdi! AGMK 3-MB mexanik AI yordamchisi tayyor 🏭")

    try:
        await dp.start_polling(
            bot,
            allowed_updates=["message", "callback_query"],
            drop_pending_updates=True
        )
    finally:
        await userbot.stop()
        await bot.session.close()


if __name__ == "__main__":
    asyncio.run(main())
