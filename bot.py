#!/usr/bin/env python3
"""
AI Agent Bot v4.0 — AGMK 3-MBF Mexanik Õtkirbek
OpenRouter + Groq + Railway
"""

import asyncio
import logging
import os
import sys
from datetime import datetime

from dotenv import load_dotenv
load_dotenv()

from aiogram import Bot, Dispatcher
from aiogram.enums import ParseMode
from aiogram.client.default import DefaultBotProperties

from database    import Database
from userbot     import UserBot
from ai_services import AIServices
from handlers    import register_handlers

try:
    from personal_twin import PersonalTwin
except ImportError:
    PersonalTwin = None

try:
    from auto_learner import AutoLearner
except ImportError:
    AutoLearner = None

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
OWNER_NAME  = os.getenv("OWNER_NAME", "Õtkirbek")


def check_env():
    for k, v in {"BOT_TOKEN": BOT_TOKEN, "GROQ_API_KEY": os.getenv("GROQ_API_KEY","")}.items():
        if not v:
            log.warning(f"⚠️ {k} yo'q!")
    or_key = os.getenv("OPENROUTER_API_KEY", "")
    log.info(f"  {'✅' if or_key else '❌'} OpenRouter API: {'sozlangan' if or_key else 'YOQ — PDF/rasm/tarjima ishlamaydi'}")
    log.info(f"  {'✅' if os.getenv('TG_SESSION_STRING') else '⚠️'} UserBot session")
    log.info(f"  {'✅' if os.getenv('WEATHER_API_KEY') else '—'} Ob-havo API")


# ── Kunlik Briefing ────────────────────────────────────────────
async def send_daily_briefing(bot: Bot, db: Database, ai: AIServices):
    """Har kuni ertalab soat 7:00 da briefing yuborish"""
    while True:
        now = datetime.now()
        # Ertalab 7:00 da ishlaydi
        if now.hour == 7 and now.minute == 0:
            try:
                # Bugungi vazifalar
                tasks   = await db.get_tasks("pending")
                pending = len(tasks)
                urgent  = [t for t in tasks if t["due"] and t["due"][:10] == now.strftime("%Y-%m-%d")]

                # Eslatmalar
                reminders = await db.get_pending_reminders()

                briefing = (
                    f"☀️ *Xayrli tong, {OWNER_NAME}!*\n"
                    f"📅 _{now.strftime('%d %B %Y, %A')}_\n\n"
                )

                if urgent:
                    briefing += f"🔴 *Bugun muddati tugaydigan vazifalar:*\n"
                    for t in urgent[:3]:
                        briefing += f"  • {t['title']}\n"
                    briefing += "\n"

                if pending:
                    briefing += f"📋 Jami faol vazifalar: *{pending}* ta\n"

                if reminders:
                    briefing += f"\n🔔 *Eslatmalar ({len(reminders)} ta):*\n"
                    for r in reminders[:3]:
                        short = r["text"][:60] + ("..." if len(r["text"]) > 60 else "")
                        briefing += f"  • _{short}_\n"

                briefing += f"\n💡 Samarali ish kuni tilayman! /help — buyruqlar"

                await bot.send_message(OWNER_ID, briefing)
                log.info("✅ Kunlik briefing yuborildi")

                # Bir marta yuborish uchun 61 soniya kutish
                await asyncio.sleep(61)
            except Exception as e:
                log.error(f"Briefing xatosi: {e}")

        await asyncio.sleep(30)


# ── Eslatma tekshiruvi ─────────────────────────────────────────
async def check_task_reminders(bot: Bot, db: Database):
    """Har 10 daqiqada vazifa muddatlarini tekshirish"""
    while True:
        try:
            reminders = await db.get_upcoming_reminders()
            for r in reminders:
                await bot.send_message(
                    OWNER_ID,
                    f"⏰ *Eslatma!*\n\n*{r['title']}*\n📅 Muddat: {r['due'][:16]}\n_Muddat yaqinlashmoqda!_"
                )
                await db.mark_reminder_sent(r["id"])
        except Exception as e:
            log.error(f"Reminder check xatosi: {e}")
        await asyncio.sleep(600)  # 10 daqiqa


async def auto_learn_loop(learner):
    """Har LEARN_INTERVAL_H soatda manbalarni sinxronlashtirish"""
    import os
    interval_h = int(os.getenv("LEARN_INTERVAL_H", "24"))
    await asyncio.sleep(60)  # Botni ishga tushirishdan keyin 1 daqiqa kutish
    while True:
        try:
            res = await learner.sync_all()
            if res["added"] > 0:
                log.info(f"✅ AutoLearner: {res['added']} ta yangi bilim qo'shildi")
        except Exception as e:
            log.error(f"AutoLearner loop xatosi: {e}")
        await asyncio.sleep(interval_h * 3600)


async def main():
    log.info("🚀 AI Agent v4.0 (AGMK MBF-3) ishga tushmoqda...")
    check_env()

    db = Database()
    await db.init()
    log.info("✅ Database tayyor")

    twin = None
    if PersonalTwin:
        twin = PersonalTwin()
        await twin.init_db()
        log.info("✅ PersonalTwin tayyor")

    learner = None
    if AutoLearner:
        learner = AutoLearner(kb=None)   # kb handlers ichida o'rnatiladi
        await learner.init_db()
        log.info("✅ AutoLearner tayyor")

    ai = AIServices()

    bot = Bot(
        token=BOT_TOKEN,
        default=DefaultBotProperties(parse_mode=ParseMode.MARKDOWN)
    )

    userbot = UserBot(TG_API_ID, TG_API_HASH, TG_PHONE)
    await userbot.start(bot_instance=bot, personal_twin=twin)

    dp = Dispatcher()
    register_handlers(dp, db, ai, userbot, OWNER_ID, twin=twin, learner=learner)

    log.info("🤖 Bot ishga tushdi! AGMK 3-MBF mexanik AI yordamchisi tayyor 🏭")

    # Fon vazifalari
    asyncio.create_task(send_daily_briefing(bot, db, ai))
    asyncio.create_task(check_task_reminders(bot, db))
    if learner:
        asyncio.create_task(auto_learn_loop(learner))

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
