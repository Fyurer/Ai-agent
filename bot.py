#!/usr/bin/env python3
"""
AI Agent Bot v4.2 — AGMK 3-MBF Mexanik Õtkirbek
OpenRouter + Groq + Railway
Toshkent vaqti (UTC+5), Briefing 12:00, daqiqalik eslatmalar
"""

import asyncio
import logging
import os
import sys
from datetime import datetime
from zoneinfo import ZoneInfo

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

try:
    from evolution_handlers import register_evolution_handlers
    EVOLUTION_ENABLED = True
except ImportError:
    EVOLUTION_ENABLED = False

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

# ── Toshkent vaqt mintaqasi ────────────────────────────────────
TZ = ZoneInfo("Asia/Tashkent")   # UTC+5


def now_tashkent() -> datetime:
    """Hozirgi Toshkent vaqtini qaytaradi"""
    return datetime.now(TZ)


def check_env():
    for k, v in {"BOT_TOKEN": BOT_TOKEN, "GROQ_API_KEY": os.getenv("GROQ_API_KEY", "")}.items():
        if not v:
            log.warning(f"⚠️ {k} yo'q!")
    or_key = os.getenv("OPENROUTER_API_KEY", "")
    log.info(f"  {'✅' if or_key else '❌'} OpenRouter API: {'sozlangan' if or_key else 'YOQ — PDF/rasm/tarjima ishlamaydi'}")
    log.info(f"  {'✅' if os.getenv('TG_SESSION_STRING') else '⚠️'} UserBot session")
    log.info(f"  {'✅' if os.getenv('WEATHER_API_KEY') else '—'} Ob-havo API")
    log.info(f"  {'✅' if EVOLUTION_ENABLED else '—'} Self-Evolution Engine")
    log.info(f"  ✅ Vaqt mintaqasi: Toshkent (UTC+5)")


# ── Kunlik Briefing — soat 12:00 Toshkent ─────────────────────
async def send_daily_briefing(bot: Bot, db: Database, ai: AIServices):
    """Har kuni soat 12:00 da (Toshkent) briefing yuborish"""
    briefing_sent_date = None   # bir kunda faqat bir marta yuborish

    while True:
        try:
            now = now_tashkent()

            # Soat 12:00 va bugun hali yuborilmagan bo'lsa
            if now.hour == 12 and now.minute == 0 and briefing_sent_date != now.date():
                briefing_sent_date = now.date()

                tasks     = await db.get_tasks("pending")
                pending   = len(tasks)
                urgent    = [
                    t for t in tasks
                    if t["due"] and t["due"][:10] == now.strftime("%Y-%m-%d")
                ]
                reminders = await db.get_pending_reminders()

                # Bugunning hafta kuni o'zbek tilida
                weekdays = {
                    0: "Dushanba", 1: "Seshanba", 2: "Chorshanba",
                    3: "Payshanba", 4: "Juma", 5: "Shanba", 6: "Yakshanba"
                }
                weekday = weekdays[now.weekday()]

                briefing = (
                    f"☀️ *Xayrli kun, {OWNER_NAME}!*\n"
                    f"📅 _{now.strftime('%d.%m.%Y')}, {weekday}_ — 🕛 12:00 Toshkent\n\n"
                )

                if urgent:
                    briefing += f"🔴 *Bugun muddati tugaydigan vazifalar:*\n"
                    for t in urgent[:5]:
                        briefing += f"  • {t['title']}\n"
                    briefing += "\n"

                if pending:
                    briefing += f"📋 Faol vazifalar: *{pending}* ta\n"

                if reminders:
                    briefing += f"\n🔔 *Eslatmalar ({len(reminders)} ta):*\n"
                    for r in reminders[:3]:
                        short = r["text"][:60] + ("..." if len(r["text"]) > 60 else "")
                        briefing += f"  • _{short}_\n"

                briefing += f"\n💡 Samarali ish kuni tilayman! /help — buyruqlar"

                await bot.send_message(OWNER_ID, briefing)
                log.info(f"✅ Kunlik briefing yuborildi ({now.strftime('%d.%m.%Y 12:00')})")

                # 65 soniya kutish — bir xil daqiqada qayta ishlamaslik uchun
                await asyncio.sleep(65)
                continue

        except Exception as e:
            log.error(f"Briefing xatosi: {e}")

        await asyncio.sleep(20)   # 20 soniyada bir tekshirish


# ── Aniq daqiqali eslatma tekshiruvi ──────────────────────────
async def check_task_reminders(bot: Bot, db: Database):
    """
    Har 30 soniyada vazifa muddatlarini tekshiradi.
    Toshkent vaqti bilan to'g'ri solishtiradi.
    """
    while True:
        try:
            reminders = await db.get_upcoming_reminders()
            for r in reminders:
                due_str = r.get("due", "")
                if not due_str:
                    continue

                # due_at ni Toshkent vaqtiga o'girish
                try:
                    # Database da saqlanadigan format: "YYYY-MM-DD HH:MM" yoki "YYYY-MM-DD HH:MM:SS"
                    fmt = "%Y-%m-%d %H:%M:%S" if len(due_str) > 16 else "%Y-%m-%d %H:%M"
                    due_dt = datetime.strptime(due_str[:19], fmt).replace(tzinfo=TZ)
                except ValueError:
                    # Faqat sana bo'lsa (YYYY-MM-DD)
                    due_dt = datetime.strptime(due_str[:10], "%Y-%m-%d").replace(
                        hour=0, minute=0, tzinfo=TZ
                    )

                now = now_tashkent()
                diff_min = (due_dt - now).total_seconds() / 60

                # Vaqti kelgan (0 dan -1 daqiqagacha) yoki 15 daqiqa qolganda
                if -1 <= diff_min <= 0:
                    # Vaqti keldi — darhol eslatma
                    time_str = due_dt.strftime("%d.%m.%Y %H:%M")
                    await bot.send_message(
                        OWNER_ID,
                        f"⏰ *Vaqti keldi!*\n\n"
                        f"📋 *{r['title']}*\n"
                        f"🕐 _{time_str} (Toshkent)_"
                    )
                    await db.mark_reminder_sent(r["id"])
                    log.info(f"⏰ Eslatma yuborildi: {r['title']}")

                elif 14 <= diff_min <= 15:
                    # 15 daqiqa qolganda ogohlantirish
                    time_str = due_dt.strftime("%H:%M")
                    await bot.send_message(
                        OWNER_ID,
                        f"🔔 *15 daqiqa qoldi!*\n\n"
                        f"📋 *{r['title']}*\n"
                        f"🕐 _{time_str} da_ (Toshkent)"
                    )
                    log.info(f"🔔 15 daqiqa ogohlantirish: {r['title']}")

        except Exception as e:
            log.error(f"Reminder check xatosi: {e}")

        await asyncio.sleep(30)   # Har 30 soniyada tekshirish


# ── AutoLearner loop ───────────────────────────────────────────
async def auto_learn_loop(learner):
    interval_h = int(os.getenv("LEARN_INTERVAL_H", "24"))
    await asyncio.sleep(60)
    while True:
        try:
            res = await learner.sync_all()
            if res["added"] > 0:
                log.info(f"✅ AutoLearner: {res['added']} ta yangi bilim qo'shildi")
        except Exception as e:
            log.error(f"AutoLearner loop xatosi: {e}")
        await asyncio.sleep(interval_h * 3600)


async def main():
    log.info("🚀 AI Agent v4.2 (AGMK MBF-3, Toshkent UTC+5) ishga tushmoqda...")
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
        learner = AutoLearner(kb=None)
        await learner.init_db()
        log.info("✅ AutoLearner tayyor")

    ai = AIServices()

    bot = Bot(
        token=BOT_TOKEN,
        default=DefaultBotProperties(parse_mode=ParseMode.MARKDOWN)
    )

    userbot = UserBot(TG_API_ID, TG_API_HASH, TG_PHONE)
    await userbot.start(bot_instance=bot)

    dp = Dispatcher()
    register_handlers(dp, db, ai, userbot, OWNER_ID, twin=twin, learner=learner)

    if EVOLUTION_ENABLED:
        register_evolution_handlers(dp, OWNER_ID)
        log.info("🧬 Self-Evolution Engine ulandi!")

    # Toshkent vaqtini log ga chiqarish
    now = now_tashkent()
    log.info(f"🕐 Hozirgi Toshkent vaqti: {now.strftime('%d.%m.%Y %H:%M:%S')} (UTC+5)")
    log.info("🤖 Bot tayyor! AGMK 3-MBF mexanik AI yordamchisi 🏭")
    log.info("📅 Kunlik briefing: har kuni 12:00 Toshkent vaqtida")
    log.info("⏰ Eslatmalar: har 30 soniyada tekshiriladi")

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
