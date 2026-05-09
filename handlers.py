"""
Handlers — Bot buyruqlari va xabarlarni qayta ishlash
"""

import asyncio
import logging
import os
import aiohttp
from datetime import datetime
from aiogram import Dispatcher, F
from aiogram.types import Message
from aiogram.filters import Command

from database import Database
from ai_services import AIServices
from userbot import UserBot

log = logging.getLogger(__name__)


def register_handlers(dp: Dispatcher, db: Database, ai: AIServices, userbot: UserBot, owner_id: int):

    def is_owner(msg: Message) -> bool:
        return msg.from_user.id == owner_id

    # ── /start ────────────────────────────────────────────────
    @dp.message(Command("start"))
    async def cmd_start(msg: Message):
        if not is_owner(msg): return
        await msg.answer(
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

    # ── /help ─────────────────────────────────────────────────
    @dp.message(Command("help"))
    async def cmd_help(msg: Message):
        if not is_owner(msg): return
        await msg.answer(
            "📖 *Buyruqlar:*\n\n"
            "💬 `Azizga yoz: ertaga uchrashemiz`\n"
            "💬 `@username ga yoz: salom`\n"
            "💬 `+998901234567 ga yoz: salom`\n"
            "📝 `Eslab qol: shartnoma 15-may`\n"
            "📝 `Zametka: bugun uchrashuv bo'ldi`\n"
            "✅ `Vazifa: hisobot tayyorla`\n"
            "✅ `Vazifa: hisobot tayyorla, muddat 10-may`\n"
            "✔️ `Vazifa 3 bajarildi`\n"
            "📋 /tasks — vazifalar ro'yxati\n"
            "📓 /notes — zametka ro'yxati\n"
            "💱 `Dollar kursi` yoki `1000 dollar necha som`\n"
            "🌤 `Toshkentda ob-havo`\n"
            "📊 /report — haftalik hisobot\n"
            "🧠 /memory — xotira holati\n"
            "🗑 /cleanup — tozalash\n\n"
            "🎤 Ovozli xabar — to'g'ridan yuboring\n"
            "📄 PDF/Rasm — to'g'ridan yuboring"
        )

    @dp.message(Command("tasks"))
    async def cmd_tasks(msg: Message):
        if not is_owner(msg): return
        await show_tasks(msg, db)

    @dp.message(Command("notes"))
    async def cmd_notes(msg: Message):
        if not is_owner(msg): return
        await show_notes(msg, db)

    @dp.message(Command("report"))
    async def cmd_report(msg: Message):
        if not is_owner(msg): return
        await show_report(msg, db)

    @dp.message(Command("memory"))
    async def cmd_memory(msg: Message):
        if not is_owner(msg): return
        stats = await db.get_all_memories_count()
        await msg.answer(
            f"🧠 *Xotira holati:*\n\n"
            f"📦 Jami: {stats['total']}\n"
            f"⭐ Doimiy: {stats['permanent']}\n"
            f"⏰ 7 kunda o'chadi: {stats['expiring_soon']}\n"
            f"📅 Muddat: 60 kun"
        )

    @dp.message(Command("cleanup"))
    async def cmd_cleanup(msg: Message):
        if not is_owner(msg): return
        deleted = await db.cleanup()
        await msg.answer(f"🗑 *Tozalash yakunlandi*\n\n{deleted} ta eski yozuv o'chirildi.")

    # ── Ovozli xabar ──────────────────────────────────────────
    @dp.message(F.voice)
    async def handle_voice(msg: Message):
        if not is_owner(msg): return
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
            response = await process_text(transcribed, db, ai, userbot, owner_id)
            await msg.answer(response)
            await db.save_message(msg.from_user.id, "in", transcribed, "voice")
        except Exception as e:
            await wait.edit_text(f"❌ Xatolik: {e}")

    # ── PDF ───────────────────────────────────────────────────
    @dp.message(F.document)
    async def handle_document(msg: Message):
        if not is_owner(msg): return
        doc = msg.document
        if doc.mime_type == "application/pdf":
            wait = await msg.answer("📄 PDF tahlil qilinmoqda...")
            file = await msg.bot.get_file(doc.file_id)
            pdf_bytes = (await msg.bot.download_file(file.file_path)).read()
            result = await ai.analyze_pdf(pdf_bytes)
            await wait.edit_text(f"📄 *PDF Tahlili:*\n\n{result}")
        else:
            await msg.answer("📎 Faqat PDF fayllarni tahlil qila olaman.")

    # ── Rasm ──────────────────────────────────────────────────
    @dp.message(F.photo)
    async def handle_photo(msg: Message):
        if not is_owner(msg): return
        wait = await msg.answer("🖼 Rasm tahlil qilinmoqda...")
        photo = msg.photo[-1]
        file = await msg.bot.get_file(photo.file_id)
        img_bytes = (await msg.bot.download_file(file.file_path)).read()
        result = await ai.analyze_image(img_bytes)
        await wait.edit_text(f"🖼 *Rasm tahlili:*\n\n{result}")

    # ── Matn xabarlar ─────────────────────────────────────────
    @dp.message(F.text)
    async def handle_text(msg: Message):
        if not is_owner(msg): return

        await db.save_message(msg.from_user.id, "in", msg.text)
        await db.save_conversation("user", msg.text)
        await msg.bot.send_chat_action(msg.chat.id, "typing")

        response = await process_text(msg.text, db, ai, userbot, owner_id)
        await msg.answer(response)

        await db.save_message(msg.from_user.id, "out", response)
        await db.save_conversation("assistant", response)


# ── Kalit so'z asosida tez aniqlash ──────────────────────────
def quick_intent(text: str) -> str:
    t = text.lower().strip()

    # Xabar yuborish
    send_words = ['ga yoz', 'ga xabar yoz', 'ga yozing', 'xabar yubor']
    if any(w in t for w in send_words):
        return "send_message"

    # Zametka
    note_words = ['eslab qol', 'eslab qol:', 'zametka:', 'zametka qil',
                  'yodda tut', 'saqlab qol', 'qeyd qil']
    if any(w in t for w in note_words):
        return "save_note"

    # Vazifa
    task_words = ['vazifa:', 'vazifa qosh', 'vazifa qo\'sh', 'topshiriq:',
                  'todo:', 'task:']
    if any(w in t for w in task_words):
        return "add_task"

    # Vazifa bajarildi
    done_words = ['bajarildi', 'tugadi', 'done', 'yakunlandi']
    if any(w in t for w in done_words):
        return "done_task"

    # Valyuta
    currency_words = ['dollar', 'kurs', 'valyuta', 'som', "so'm", 'euro',
                      'evro', 'rubl', 'usd', 'eur', 'rub']
    if any(w in t for w in currency_words):
        return "currency"

    # Ob-havo
    weather_words = ['ob-havo', 'ob havo', 'havo', 'temperatura',
                     'harorat', 'bugun havo', 'weather']
    if any(w in t for w in weather_words):
        return "weather"

    # Hisobot
    if any(w in t for w in ['hisobot', 'statistika', 'report']):
        return "report"

    return ""  # AI ga yuboriladi


# ── Asosiy qayta ishlash ──────────────────────────────────────
async def process_text(text: str, db: Database,
                       ai: AIServices, userbot: UserBot, owner_id: int) -> str:

    # 1. Tez kalit so'z tekshiruv
    action = quick_intent(text)

    # 2. Agar topilmasa — Groq ga yuborish
    if not action:
        intent = await ai.detect_intent(text)
        action = intent.get("action", "chat")
    else:
        intent = {"action": action}
        # Target va content ajratish
        if action == "send_message":
            parts = text.split("ga yoz", 1)
            if len(parts) == 2:
                intent["target"] = parts[0].strip().lstrip('@').lstrip('+')
                intent["content"] = parts[1].strip().lstrip(':').strip()

        elif action == "save_note":
            for kw in ['eslab qol:', 'eslab qol', 'zametka:', 'zametka qil',
                       'yodda tut', 'saqlab qol']:
                if kw in text.lower():
                    idx = text.lower().index(kw) + len(kw)
                    intent["content"] = text[idx:].strip().lstrip(':').strip()
                    break

        elif action == "add_task":
            for kw in ['vazifa:', 'vazifa qo\'sh', 'topshiriq:', 'todo:']:
                if kw in text.lower():
                    idx = text.lower().index(kw) + len(kw)
                    intent["content"] = text[idx:].strip().lstrip(':').strip()
                    break

        elif action == "done_task":
            import re
            nums = re.findall(r'\d+', text)
            intent["task_id"] = nums[0] if nums else None

    # ── Harakatlar ────────────────────────────────────────────
    if action == "send_message":
        return await action_send_message(intent, userbot)

    elif action == "save_note":
        content = intent.get("content") or text
        return await action_save_note(content, db, ai)

    elif action == "add_task":
        return await action_add_task(intent, text, db)

    elif action == "get_tasks":
        tasks = await db.get_tasks()
        if not tasks:
            return "✅ Hozircha faol vazifalar yo'q."
        lines = ["📋 *Faol vazifalar:*\n"]
        for i, t in enumerate(tasks, 1):
            due = f" — _{t['due'][:10]}_" if t["due"] else ""
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
        city = intent.get("city") or extract_city(text)
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
        memories = await db.get_relevant_memories(text)
        context = "\n".join(f"• {m}" for m in memories) if memories else ""
        history = await db.get_conversation_history()
        return await ai.chat(text, history, context)


# ── Shahar ajratish ───────────────────────────────────────────
def extract_city(text: str) -> str:
    cities = ['toshkent', 'samarqand', 'buxoro', 'namangan', 'andijon',
              'farg\'ona', 'nukus', 'termiz', 'moscow', 'london', 'dubai']
    t = text.lower()
    for city in cities:
        if city in t:
            return city.capitalize()
    return "Tashkent"


# ── Xabar yuborish ────────────────────────────────────────────
async def action_send_message(intent: dict, userbot: UserBot) -> str:
    target  = intent.get("target", "").strip()
    content = intent.get("content", "").strip()

    if not target or not content:
        return (
            "❓ Format:\n"
            "`Azizga yoz: ertaga uchrashemiz`\n"
            "`@username ga yoz: salom`\n"
            "`+998901234567 ga yoz: salom`"
        )

    if not userbot.is_connected:
        return "❌ UserBot ulanmagan. TG_SESSION_STRING ni tekshiring."

    result = await userbot.send_message(target, content)
    if result["ok"]:
        return f"✅ *{result['name']}* ga xabar yuborildi:\n_{content}_"
    else:
        return f"❌ Xabar yuborilmadi: {result['error']}"


# ── Zametka saqlash ───────────────────────────────────────────
async def action_save_note(content: str, db: Database, ai: AIServices) -> str:
    importance   = await ai.score_importance(content)
    is_permanent = importance >= 0.75

    await db.add_note(content, is_pinned=is_permanent)
    await db.save_memory(content, "note", is_permanent, importance)

    flag = "\n⭐ _Muhim — doimiy saqlandi_" if is_permanent else ""
    return f"✅ *Zametka saqlandi!*{flag}\n\n_{content}_"


# ── Vazifa qo'shish ───────────────────────────────────────────
async def action_add_task(intent: dict, text: str, db: Database) -> str:
    title    = intent.get("content") or text
    deadline = intent.get("deadline")

    task_id = await db.add_task(title, text, deadline)
    due_str = f"\n📅 Muddat: {deadline[:10]}" if deadline else ""
    return f"✅ Vazifa #{task_id} qo'shildi:\n*{title}*{due_str}"


# ── Valyuta kursi ─────────────────────────────────────────────
async def action_currency() -> str:
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(
                "https://cbu.uz/uz/arkhiv-kursov-valyut/json/",
                timeout=aiohttp.ClientTimeout(total=10)
            ) as r:
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
        return "❌ WEATHER_API_KEY sozlanmagan. Railway Variables ga qo'shing."

    try:
        url = (f"https://api.openweathermap.org/data/2.5/weather"
               f"?q={city}&appid={api_key}&units=metric&lang=ru")
        async with aiohttp.ClientSession() as session:
            async with session.get(url, timeout=aiohttp.ClientTimeout(total=10)) as r:
                data = await r.json()

        if data.get("cod") != 200:
            return f"❌ {city} shahri topilmadi."

        return (
            f"🌤 *{data['name']} ob-havosi:*\n\n"
            f"🌡 Harorat: {round(data['main']['temp'])}°C "
            f"(sezilishi {round(data['main']['feels_like'])}°C)\n"
            f"☁️ {data['weather'][0]['description']}\n"
            f"💧 Namlik: {data['main']['humidity']}%\n"
            f"💨 Shamol: {data['wind']['speed']} m/s"
        )
    except Exception as e:
        return f"❌ Ob-havo ma'lumotini olishda xatolik: {e}"


# ── Yordamchi ─────────────────────────────────────────────────
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
