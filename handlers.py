"""
Handlers — Bot buyruqlari va xabarlarni qayta ishlash
"""

import asyncio
import logging
import aiohttp
from datetime import datetime
from aiogram import Dispatcher, F
from aiogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton, CallbackQuery
from aiogram.filters import Command

from database import Database
from ai_services import AIServices
from userbot import UserBot

log = logging.getLogger(__name__)


def register_handlers(dp: Dispatcher, db: Database, ai: AIServices, userbot: UserBot, owner_id: int):

    # ── Faqat owner filtri ────────────────────────────────────
    def is_owner(msg: Message) -> bool:
        return msg.from_user.id == owner_id

    # ── /start ────────────────────────────────────────────────
    @dp.message(Command("start"))
    async def cmd_start(msg: Message):
        if not is_owner(msg):
            return  # Begonalarga javob yo'q — jim turadi

        text = (
            "👋 *Salom! Men sizning AI Agentingizman.*\n\n"
            "🧠 Groq Llama 3 + Gemini 1.5 Flash\n\n"
            "*Nima qila olaman:*\n"
            "✉️ Nomingizdan xabar yuborish\n"
            "🎤 Ovozli xabarni tushunish\n"
            "📄 PDF va rasm tahlil\n"
            "📝 Zametka saqlash\n"
            "✅ Vazifa boshqaruvi\n"
            "💱 Valyuta kursi\n"
            "🌤 Ob-havo\n"
            "🧠 60 kunlik aqlli xotira\n\n"
            "/help — barcha buyruqlar"
        )
        await msg.answer(text)

    # ── /help ─────────────────────────────────────────────────
    @dp.message(Command("help"))
    async def cmd_help(msg: Message):
        if not is_owner(msg):
            return

        text = (
            "📖 *Buyruqlar:*\n\n"
            "💬 `Azizga yoz: ertaga uchrashemiz`\n"
            "📝 `Eslab qol: shartnoma 15-may`\n"
            "✅ `Vazifa: hisobot tayyorla, 10-may`\n"
            "✔️ `Vazifa 3 bajarildi`\n"
            "📋 /tasks — vazifalar ro'yxati\n"
            "📓 /notes — zametka ro'yxati\n"
            "💱 `1000 dollar necha so'm`\n"
            "🌤 `Toshkentda ob-havo`\n"
            "📊 /report — haftalik hisobot\n"
            "🧠 /memory — xotira holati\n"
            "🗑 /cleanup — eski ma'lumotlarni tozalash\n\n"
            "🎤 *Ovozli xabar* — to'g'ridan yuboring\n"
            "📄 *PDF/Rasm* — to'g'ridan yuboring"
        )
        await msg.answer(text)

    # ── /tasks ────────────────────────────────────────────────
    @dp.message(Command("tasks"))
    async def cmd_tasks(msg: Message):
        if not is_owner(msg):
            return
        await show_tasks(msg, db)

    # ── /notes ────────────────────────────────────────────────
    @dp.message(Command("notes"))
    async def cmd_notes(msg: Message):
        if not is_owner(msg):
            return
        await show_notes(msg, db)

    # ── /report ───────────────────────────────────────────────
    @dp.message(Command("report"))
    async def cmd_report(msg: Message):
        if not is_owner(msg):
            return
        await show_report(msg, db)

    # ── /memory ───────────────────────────────────────────────
    @dp.message(Command("memory"))
    async def cmd_memory(msg: Message):
        if not is_owner(msg):
            return
        stats = await db.get_all_memories_count()
        text = (
            f"🧠 *Xotira holati:*\n\n"
            f"📦 Jami: {stats['total']}\n"
            f"⭐ Doimiy: {stats['permanent']}\n"
            f"⏰ 7 kunda o'chadi: {stats['expiring_soon']}\n"
            f"📅 Muddat: 60 kun"
        )
        await msg.answer(text)

    # ── /cleanup ──────────────────────────────────────────────
    @dp.message(Command("cleanup"))
    async def cmd_cleanup(msg: Message):
        if not is_owner(msg):
            return
        deleted = await db.cleanup()
        await msg.answer(f"🗑 *Tozalash yakunlandi*\n\n{deleted} ta eski yozuv o'chirildi.")

    # ── Ovozli xabar ──────────────────────────────────────────
    @dp.message(F.voice)
    async def handle_voice(msg: Message):
        if not is_owner(msg):
            return

        wait = await msg.answer("🎤 Ovoz tahlil qilinmoqda...")
        try:
            file = await msg.bot.get_file(msg.voice.file_id)
            audio = await msg.bot.download_file(file.file_path)
            audio_bytes = audio.read()

            transcribed = await ai.transcribe_voice(audio_bytes)
            if not transcribed:
                await wait.edit_text("❌ Ovozni tushunib bo'lmadi. Qaytadan yuboring.")
                return

            await wait.edit_text(f"🎤 *Eshitildi:*\n_{transcribed}_\n\nJavob tayyorlanmoqda...")
            response = await process_text(transcribed, msg, db, ai, userbot, owner_id)
            await msg.answer(response)
            await db.save_message(msg.from_user.id, "in", transcribed, "voice")

        except Exception as e:
            await wait.edit_text(f"❌ Xatolik: {e}")

    # ── PDF ───────────────────────────────────────────────────
    @dp.message(F.document)
    async def handle_document(msg: Message):
        if not is_owner(msg):
            return

        doc = msg.document
        if doc.mime_type == "application/pdf":
            wait = await msg.answer("📄 PDF tahlil qilinmoqda...")
            file = await msg.bot.get_file(doc.file_id)
            pdf_bytes = (await msg.bot.download_file(file.file_path)).read()
            result = await ai.analyze_pdf(pdf_bytes)
            await wait.edit_text(f"📄 *PDF Tahlili:*\n\n{result}")
        else:
            await msg.answer("📎 Bu fayl turini tahlil qila olmayman. PDF yuboring.")

    # ── Rasm ──────────────────────────────────────────────────
    @dp.message(F.photo)
    async def handle_photo(msg: Message):
        if not is_owner(msg):
            return

        wait = await msg.answer("🖼 Rasm tahlil qilinmoqda...")
        photo = msg.photo[-1]
        file = await msg.bot.get_file(photo.file_id)
        img_bytes = (await msg.bot.download_file(file.file_path)).read()
        result = await ai.analyze_image(img_bytes)
        await wait.edit_text(f"🖼 *Rasm tahlili:*\n\n{result}")

    # ── Matn xabarlar ─────────────────────────────────────────
    @dp.message(F.text)
    async def handle_text(msg: Message):
        if not is_owner(msg):
            return  # Jim turadi

        await db.save_message(msg.from_user.id, "in", msg.text)
        await db.save_conversation("user", msg.text)

        # Yozmoqda... ko'rsatish
        await msg.bot.send_chat_action(msg.chat.id, "typing")

        response = await process_text(msg.text, msg, db, ai, userbot, owner_id)
        await msg.answer(response)

        await db.save_message(msg.from_user.id, "out", response)
        await db.save_conversation("assistant", response)


# ── Matn qayta ishlash (asosiy mantiq) ───────────────────────
async def process_text(text: str, msg: Message, db: Database,
                       ai: AIServices, userbot: UserBot, owner_id: int) -> str:

    intent = await ai.detect_intent(text)
    action = intent.get("action", "chat")

    if action == "send_message":
        return await action_send_message(intent, userbot)

    elif action == "save_note":
        return await action_save_note(text, db, ai)

    elif action == "add_task":
        return await action_add_task(intent, text, db)

    elif action == "get_tasks":
        tasks = await db.get_tasks()
        if not tasks:
            return "✅ Hozircha faol vazifalar yo'q."
        lines = ["📋 *Faol vazifalar:*\n"]
        for i, t in enumerate(tasks, 1):
            due = f" — {t['due'][:10]}" if t["due"] else ""
            lines.append(f"{i}. {t['title']}{due}")
        return "\n".join(lines)

    elif action == "done_task":
        task_id = intent.get("task_id")
        if task_id:
            await db.complete_task(int(task_id))
            return f"✅ Vazifa #{task_id} bajarildi deb belgilandi!"
        return "❓ Qaysi vazifa? Masalan: `Vazifa 3 bajarildi`"

    elif action == "get_notes":
        notes = await db.get_notes()
        if not notes:
            return "📝 Hozircha zametka yo'q."
        lines = ["📝 *Zametkalar:*\n"]
        for i, n in enumerate(notes, 1):
            pin = "⭐ " if n["pinned"] else ""
            short = n["content"][:80] + ("..." if len(n["content"]) > 80 else "")
            lines.append(f"{i}. {pin}{short}")
        return "\n".join(lines)

    elif action == "currency":
        return await action_currency()

    elif action == "weather":
        city = intent.get("city") or "Tashkent"
        return await action_weather(city)

    elif action == "report":
        stats = await db.get_weekly_stats()
        return (
            f"📊 *Haftalik Hisobot*\n"
            f"_{datetime.now().strftime('%d.%m.%Y')}_\n\n"
            f"💬 Xabarlar: {stats['messages']}\n"
            f"📝 Zametka: {stats['notes']}\n"
            f"✅ Bajarilgan: {stats['done']}\n"
            f"⏳ Kutilayotgan: {stats['pending']}\n"
            f"🧠 Xotiraga saqlangan: {stats['memories']}"
        )

    elif action == "memory":
        stats = await db.get_all_memories_count()
        return (
            f"🧠 *Xotira holati:*\n\n"
            f"📦 Jami: {stats['total']}\n"
            f"⭐ Doimiy: {stats['permanent']}\n"
            f"⏰ 7 kunda o'chadi: {stats['expiring_soon']}"
        )

    else:
        # Oddiy suhbat — kontekst bilan
        memories = await db.get_relevant_memories(text)
        context = "\n".join(f"• {m}" for m in memories) if memories else ""
        history = await db.get_conversation_history()
        return await ai.chat(text, history, context)


# ── Xabar yuborish ────────────────────────────────────────────
async def action_send_message(intent: dict, userbot: UserBot) -> str:
    target  = intent.get("target", "")
    content = intent.get("content", "")

    if not target or not content:
        return "❓ Kimga va nima yozish? Masalan: `Azizga yoz: ertaga uchrashemiz`"

    if not userbot.is_connected:
        return "❌ UserBot ulanmagan. TG_SESSION_STRING ni tekshiring."

    result = await userbot.send_message(target, content)
    if result["ok"]:
        return f"✅ *{result['name']}* ga xabar yuborildi:\n_{content}_"
    else:
        return f"❌ Xabar yuborilmadi: {result['error']}"


# ── Zametka saqlash ───────────────────────────────────────────
async def action_save_note(text: str, db: Database, ai: AIServices) -> str:
    importance  = await ai.score_importance(text)
    is_permanent = importance >= 0.75

    await db.add_note(text, is_pinned=is_permanent)
    await db.save_memory(text, "note", is_permanent, importance)

    flag = "⭐ _(muhim — doimiy saqlandi)_" if is_permanent else ""
    return f"✅ Zametka saqlandi {flag}\n_{text}_"


# ── Vazifa qo'shish ───────────────────────────────────────────
async def action_add_task(intent: dict, text: str, db: Database) -> str:
    title    = intent.get("content") or text
    deadline = intent.get("deadline")

    task_id = await db.add_task(title, text, deadline)
    due_str = f"\n📅 Muddat: {deadline[:10]}" if deadline else ""
    return f"✅ Vazifa #{task_id} qo'shildi: *{title}*{due_str}"


# ── Valyuta kursi ─────────────────────────────────────────────
async def action_currency() -> str:
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get("https://cbu.uz/uz/arkhiv-kursov-valyut/json/") as r:
                data = await r.json(content_type=None)

        rates = {d["Ccy"]: float(d["Rate"]) for d in data}
        return (
            f"💱 *Valyuta Kurslari (CBU)*\n"
            f"_{datetime.now().strftime('%d.%m.%Y')}_\n\n"
            f"🇺🇸 USD: {rates.get('USD', 0):,.0f} so'm\n"
            f"🇪🇺 EUR: {rates.get('EUR', 0):,.0f} so'm\n"
            f"🇷🇺 RUB: {rates.get('RUB', 0):.2f} so'm\n"
            f"🇨🇳 CNY: {rates.get('CNY', 0):,.0f} so'm"
        )
    except Exception as e:
        return f"❌ Kurs ma'lumotini olishda xatolik: {e}"


# ── Ob-havo ───────────────────────────────────────────────────
async def action_weather(city: str) -> str:
    api_key = os.getenv("WEATHER_API_KEY", "")
    if not api_key:
        return "❌ WEATHER_API_KEY sozlanmagan."

    try:
        import os
        url = f"https://api.openweathermap.org/data/2.5/weather?q={city}&appid={api_key}&units=metric&lang=ru"
        async with aiohttp.ClientSession() as session:
            async with session.get(url) as r:
                data = await r.json()

        temp   = round(data["main"]["temp"])
        feels  = round(data["main"]["feels_like"])
        desc   = data["weather"][0]["description"]
        humid  = data["main"]["humidity"]
        wind   = data["wind"]["speed"]
        name   = data["name"]

        return (
            f"🌤 *{name} ob-havosi:*\n\n"
            f"🌡 Harorat: {temp}°C (sezilishi {feels}°C)\n"
            f"☁️ {desc}\n"
            f"💧 Namlik: {humid}%\n"
            f"💨 Shamol: {wind} m/s"
        )
    except Exception as e:
        return f"❌ Ob-havo ma'lumotini olishda xatolik: {e}"


# ── Yordamchi funksiyalar ─────────────────────────────────────
async def show_tasks(msg: Message, db: Database):
    tasks = await db.get_tasks()
    if not tasks:
        await msg.answer("✅ Hozircha faol vazifalar yo'q.")
        return
    lines = ["📋 *Faol vazifalar:*\n"]
    for i, t in enumerate(tasks, 1):
        due = f" — _{t['due'][:10]}_" if t["due"] else ""
        lines.append(f"{i}. {t['title']}{due}")
    await msg.answer("\n".join(lines))


async def show_notes(msg: Message, db: Database):
    notes = await db.get_notes()
    if not notes:
        await msg.answer("📝 Hozircha zametka yo'q.")
        return
    lines = ["📝 *Zametkalar:*\n"]
    for i, n in enumerate(notes, 1):
        pin   = "⭐ " if n["pinned"] else ""
        short = n["content"][:80] + ("..." if len(n["content"]) > 80 else "")
        lines.append(f"{i}. {pin}{short}")
    await msg.answer("\n".join(lines))


async def show_report(msg: Message, db: Database):
    stats = await db.get_weekly_stats()
    await msg.answer(
        f"📊 *Haftalik Hisobot*\n"
        f"_{datetime.now().strftime('%d.%m.%Y')}_\n\n"
        f"💬 Xabarlar: {stats['messages']}\n"
        f"📝 Zametka: {stats['notes']}\n"
        f"✅ Bajarilgan: {stats['done']}\n"
        f"⏳ Kutilayotgan: {stats['pending']}\n"
        f"🧠 Xotiraga saqlangan: {stats['memories']}"
    )
