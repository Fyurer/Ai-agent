"""
bot.py — YANGILANGAN VERSIYA
Yangi modullar qo'shildi:
- visual_inspector.py
- autopilot.py
- knowledge_base.py
- new_handlers.py
"""

import asyncio
import logging
import os
from dotenv import load_dotenv
from aiogram import Bot, Dispatcher
from aiogram.enums import ParseMode
from aiogram.client.default import DefaultBotProperties

from database import Database
from ai_services import AIServices
from userbot import UserBot
from handlers import register_handlers

# ✅ YANGI IMPORT
from new_handlers import register_new_handlers

load_dotenv()
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(name)s | %(message)s"
)
log = logging.getLogger(__name__)


async def main():
    TOKEN    = os.getenv("BOT_TOKEN")
    OWNER_ID = int(os.getenv("OWNER_ID", "0"))

    bot = Bot(token=TOKEN, default=DefaultBotProperties(parse_mode=ParseMode.MARKDOWN))
    dp  = Dispatcher()
    db  = Database()
    ai  = AIServices()

    await db.init()

    # Userbot (Telethon)
    userbot = UserBot(
        api_id=os.getenv("TG_API_ID"),
        api_hash=os.getenv("TG_API_HASH"),
        session_string=os.getenv("TG_SESSION_STRING")
    )
    await userbot.start()

    # ── Handlerlarni ro'yxatga olish ───────────────────────────
    # Eski handlerlar
    register_handlers(dp, db, ai, userbot, OWNER_ID)

    # ✅ Yangi handlerlar (vizual, autopilot, knowledge base)
    autopilot = register_new_handlers(dp, db, ai, userbot, OWNER_ID)

    log.info("✅ Bot ishga tushdi | Barcha yangi funksiyalar faol")
    log.info("🆕 Yangi: AutoPilot | Vizual Defektoskopiya | MBF-3 KB | Sensor Tahlil")

    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())
