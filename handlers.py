"""
Handlers — Bot buyruqlari va xabarlarni qayta ishlash
"""

import os
import re
import logging
import aiohttp
from datetime import datetime
from aiogram import Dispatcher, F
from aiogram.types import Message
from aiogram.filters import Command

from database import Database
from ai_services import AIServices
from userbot import UserBot

log = logging.getLogger(__name__)


def register_handlers(dp: Dispatcher, db: Database, ai: AIServices,
                      userbot: UserBot, owner_id: int):

    def is_owner(msg: Message) -> bool:
        return msg.from_user.id == owner_id

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

    @dp.message(Command("help"))
    async def cmd_help(msg: Message):
        if not is_owner(msg): return
        await msg.answer(
            "📖 *Buyruqlar:*\n\n"
            "💬 `Azizga yoz: ertaga uchrashemiz`\n"
            "💬 `Shodigа yoz: salom` _(emoji bilan ham ishlaydi)_\n"
            "💬 `@username ga yoz: salom`\n"
            "💬 `+998901234567 ga yoz: salom`\n"
            "📋 `Kontaktlar` — kontaktlar ro'yxati\n\n"
            "📝 `Eslab qol: shartnoma 15-may`\n"
            "📝 `Zametka: bugun muhim gap`\n"
            "✅ `Vazifa: hisobot tayyorla`\n"
            "✅ `Vazifa: hisobot, muddat 10-may`\n"
            "✔️ `Vazifa 3 bajarildi`\n"
            "📋 /tasks — vazifalar\n"
            "📓 /notes — zametka\n\n"
            "💱 `Dollar kursi`\n"
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
        wait = await msg.answer("🎤 _Ovoz tahlil qilinmoqda..._")
        try:
            file = await msg.bot.get_file(msg.voice.file_id)
            bio  = await msg.bot.download_file(file.file_path)
            audio_bytes = bio.read()

            transcribed = await ai.transcribe_voice(audio_bytes)
            if not transcribed:
                await wait.edit_text("❌ Ovozni tushunib bo'lmadi. Qaytadan yuboring.")
                return

            await wait.edit_text(f"🎤 *Eshitildi:*\n_{transcribed}_")
            response = await process_text(transcribed, db, ai, userbot, owner_id)
            await msg.answer(response)
            await db.save_message(msg.from_user.id, "in", transcribed, "voice")

        except Exception as e:
            await wait.edit_text(f"❌ Xatolik: {e}")

    # ── PDF ───────────────────────────────────────────────────
    @dp.message(F.document)
    async def handle_document(msg: Message):
        if not is_owner(msg): return
        if msg.document.mime_type == "application/pdf":
            wait = await msg.answer("📄 _PDF tahlil qilinmoqda..._")
            file = await msg.bot.get_file(msg.document.file_id)
            pdf  = (await msg.bot.download_file(file.file_path)).read()
            result = await ai.analyze_pdf(pdf)
            await wait.edit_text(f"📄 *PDF Tahlili:*\n\n{result}")
        else:
            await msg.answer("📎 Faqat PDF fayllarni tahlil qila olaman.")

    # ── Rasm ──────────────────────────────────────────────────
    @dp.message(F.photo)
    async def handle_photo(msg: Message):
        if not is_owner(msg): return
        wait  = await msg.answer("🖼 _Rasm tahlil qilinmoqda..._")
        photo = msg.photo[-1]
        file  = await msg.bot.get_file(photo.file_id)
        img   = (await msg.bot.download_file(file.file_path)).read()
        result = await ai.analyze_image(img)
        await wait.edit_text(f"🖼 *Rasm tahlili:*\n\n{result}")

    # ── Matn ──────────────────────────────────────────────────
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
def quick_intent(text: str) -> tuple:
    """(action, extracted_data) qaytaradi"""
    t = text.strip()
    tl = t.lower()

    # ── Xabar yuborish: "Azizga yoz: matn" ───────────────────
    # "ga yoz" yoki "ga yozing" pattern
    send_match = re.search(r'^(.+?)\s+ga\s+yoz(?:ing)?\s*[:\s]\s*(.+)$', t, re.IGNORECASE)
    if send_match:
        target  = send_match.group(1).strip()
        content = send_match.group(2).strip()
        return ("send_message", {"target": target, "content": content})

    # ── Kontaktlar ro'yxati ───────────────────────────────────
    if any(w in tl for w in ['kontaktlar', 'kontakt royxat', 'kimlar bor']):
        return ("contacts", {})

    # ── Zametka ───────────────────────────────────────────────
    note_match = re.match(
        r'^(?:eslab qol|zametka|yodda tut|saqlab qol|qeyd)[:\s]+(.+)$',
        t, re.IGNORECASE
    )
    if note_match:
        return ("save_note", {"content": note_match.group(1).strip()})

    # ── Vazifa ───────────────────────────────────────────────
    task_match = re.match(
        r'^(?:vazifa|topshiriq|todo|task)[:\s]+(.+)$',
        t, re.IGNORECASE
    )
    if task_match:
        content = task_match.group(1).strip()
        # Muddat qidirish
        deadline = None
        due_match = re.search(r',\s*muddat\s+(.+)$', content, re.IGNORECASE)
        if due_match:
            deadline = due_match.group(1).strip()
            content  = content[:due_match.start()].strip()
        return ("add_task", {"content": content, "deadline": deadline})

    # ── Vazifa bajarildi ──────────────────────────────────────
    done_match = re.search(r'vazifa\s+(\d+)\s+bajarildi', tl)
    if done_match:
        return ("done_task", {"task_id": done_match.group(1)})

    # ── Valyuta ───────────────────────────────────────────────
    if any(w in tl for w in ['dollar', 'kurs', 'valyuta', "so'm", 'som',
                               'evro', 'euro', 'rubl', 'usd', 'eur', 'rub']):
        # Miqdor qidirish
        amount_match = re.search(r'(\d[\d\s,.]*)[\s]*(dollar|usd|euro|evro|rubl|rub)', tl)
        amount = amount_match.group(1).replace(' ', '').replace(',', '') if amount_match else None
        currency = amount_match.group(2) if amount_match else None
        return ("currency", {"amount": amount, "currency": currency})

    # ── Ob-havo ───────────────────────────────────────────────
    if any(w in tl for w in ['ob-havo', 'ob havo', 'havo', 'harorat', 'weather']):
        city = extract_city(t)
        return ("weather", {"city": city})

    # ── Hisobot ───────────────────────────────────────────────
    if any(w in tl for w in ['hisobot', 'statistika', 'haftalik']):
        return ("report", {})

    return ("", {})


def extract_city(text: str) -> str:
    cities = {
        'toshkent': 'Tashkent', 'samarqand': 'Samarkand',
        'buxoro': 'Bukhara', 'namangan': 'Namangan',
        'andijon': 'Andijan', "farg'ona": 'Fergana',
        'nukus': 'Nukus', 'termiz': 'Termez',
        'moscow': 'Moscow', 'moskva': 'Moscow',
        'london': 'London', 'dubai': 'Dubai',
        'istanbul': 'Istanbul'
    }
    tl = text.lower()
    for key, val in cities.items():
        if key in tl:
            return val
    return "Tashkent"


# ── Asosiy qayta ishlash ──────────────────────────────────────
async def process_text(text: str, db: Database,
                       ai: AIServices, userbot: UserBot, owner_id: int) -> str:

    action, data = quick_intent(text)

    # Agar topilmasa — Groq ga yuborish
    if not action:
        intent = await ai.detect_intent(text)
        action = intent.get("action", "chat")
        data   = intent

    if action == "send_message":
        target  = data.get("target", "")
        content = data.get("content", "")
        return await action_send_message(target, content, userbot)

    elif action == "contacts":
        return await action_get_contacts(userbot)

    elif action == "save_note":
        content = data.get("content") or text
        return await action_save_note(content, db, ai)

    elif action == "add_task":
        return await action_add_task(data, db)

    elif action == "get_tasks":
        return await get_tasks_text(db)

    elif action == "done_task":
        task_id = data.get("task_id")
        if task_id:
            await db.complete_task(int(task_id))
            return f"✅ Vazifa #{task_id} bajarildi deb belgilandi!"
        return "❓ Qaysi vazifa raqami? Masalan: `Vazifa 3 bajarildi`"

    elif action == "get_notes":
        return await get_notes_text(db)

    elif action == "currency":
        return await action_currency(
            data.get("amount"), data.get("currency")
        )

    elif action == "weather":
        return await action_weather(data.get("city") or "Tashkent")

    elif action == "report":
        return await get_report_text(db)

    elif action == "memory":
        stats = await db.get_all_memories_count()
        return (
            f"🧠 *Xotira holati:*\n\n"
            f"📦 Jami: {stats['total']}\n"
            f"⭐ Doimiy: {stats['permanent']}\n"
            f"⏰ 7 kunda o'chadi: {stats['expiring_soon']}"
        )

    else:
        # Oddiy suhbat — kontekst + tarix bilan
        memories = await db.get_relevant_memories(text)
        context  = "\n".join(f"• {m}" for m in memories) if memories else ""
        history  = await db.get_conversation_history()
        return await ai.chat(text, history, context)


# ── Harakatlar ────────────────────────────────────────────────

async def action_send_message(target: str, content: str, userbot: UserBot) -> str:
    if not target or not content:
        return (
            "❓ Format:\n"
            "`Azizga yoz: ertaga uchrashemiz`\n"
            "`Shodigа yoz: salom`\n"
            "`@username ga yoz: salom`\n"
            "`+998901234567 ga yoz: salom`"
        )
    if not userbot.is_connected:
        return "❌ UserBot ulanmagan. TG_SESSION_STRING ni tekshiring."

    result = await userbot.send_message(target, content)
    if result["ok"]:
        return f"✅ *{result['name']}* ga xabar yuborildi:\n_{content}_"
    return f"❌ Xabar yuborilmadi: {result['error']}"


async def action_get_contacts(userbot: UserBot) -> str:
    if not userbot.is_connected:
        return "❌ UserBot ulanmagan."
    contacts = await userbot.get_contacts_list()
    if not contacts:
        return "📋 Kontaktlar topilmadi."
    lines = ["📋 *Kontaktlaringiz:*\n"]
    for i, c in enumerate(contacts[:30], 1):
        uname = f" (@{c['username']})" if c['username'] else ""
        lines.append(f"{i}. {c['name']}{uname}")
    if len(contacts) > 30:
        lines.append(f"\n_... va yana {len(contacts)-30} ta_")
    return "\n".join(lines)


async def action_save_note(content: str, db: Database, ai: AIServices) -> str:
    importance   = await ai.score_importance(content)
    is_permanent = importance >= 0.75
    await db.add_note(content, is_pinned=is_permanent)
    await db.save_memory(content, "note", is_permanent, importance)
    flag = "\n⭐ _Muhim — doimiy saqlandi_" if is_permanent else ""
    return f"✅ *Zametka saqlandi!*{flag}\n\n_{content}_"


async def action_add_task(data: dict, db: Database) -> str:
    title    = data.get("content", "")
    deadline = data.get("deadline")
    task_id  = await db.add_task(title, title, deadline)
    due_str  = f"\n📅 Muddat: {deadline}" if deadline else ""
    return f"✅ Vazifa #{task_id} qo'shildi:\n*{title}*{due_str}"


async def action_currency(amount=None, currency_type=None) -> str:
    try:
        async with aiohttp.ClientSession() as s:
            async with s.get(
                "https://cbu.uz/uz/arkhiv-kursov-valyut/json/",
                timeout=aiohttp.ClientTimeout(total=10)
            ) as r:
                data = await r.json(content_type=None)

        rates = {d["Ccy"]: float(d["Rate"]) for d in data}
        result = (
            f"💱 *Valyuta Kurslari (CBU)*\n"
            f"_{datetime.now().strftime('%d.%m.%Y')}_\n\n"
            f"🇺🇸 USD: {rates.get('USD', 0):,.0f} so'm\n"
            f"🇪🇺 EUR: {rates.get('EUR', 0):,.0f} so'm\n"
            f"🇷🇺 RUB: {rates.get('RUB', 0):.2f} so'm\n"
            f"🇨🇳 CNY: {rates.get('CNY', 0):,.0f} so'm"
        )

        # Hisoblash
        if amount and currency_type:
            amt = float(amount)
            ccy_map = {
                'dollar': 'USD', 'usd': 'USD',
                'euro': 'EUR', 'evro': 'EUR',
                'rubl': 'RUB', 'rub': 'RUB'
            }
            ccy = ccy_map.get(currency_type.lower())
            if ccy and ccy in rates:
                total = amt * rates[ccy]
                result += f"\n\n💰 {amt:,.0f} {ccy} = *{total:,.0f} so'm*"

        return result
    except Exception as e:
        return f"❌ Kurs olishda xatolik: {e}"


async def action_weather(city: str) -> str:
    api_key = os.getenv("WEATHER_API_KEY", "")
    if not api_key:
        return "❌ WEATHER_API_KEY sozlanmagan."
    try:
        url = (f"https://api.openweathermap.org/data/2.5/weather"
               f"?q={city}&appid={api_key}&units=metric&lang=ru")
        async with aiohttp.ClientSession() as s:
            async with s.get(url, timeout=aiohttp.ClientTimeout(total=10)) as r:
                data = await r.json()
        if data.get("cod") != 200:
            return f"❌ {city} shahri topilmadi."
        return (
            f"🌤 *{data['name']} ob-havosi:*\n\n"
            f"🌡 {round(data['main']['temp'])}°C "
            f"(sezilishi {round(data['main']['feels_like'])}°C)\n"
            f"☁️ {data['weather'][0]['description']}\n"
            f"💧 Namlik: {data['main']['humidity']}%\n"
            f"💨 Shamol: {data['wind']['speed']} m/s"
        )
    except Exception as e:
        return f"❌ Ob-havo xatosi: {e}"


async def get_tasks_text(db: Database) -> str:
    tasks = await db.get_tasks()
    if not tasks:
        return "✅ Hozircha faol vazifalar yo'q."
    lines = ["📋 *Faol vazifalar:*\n"]
    for i, t in enumerate(tasks, 1):
        due = f" — _{t['due'][:10]}_" if t["due"] else ""
        lines.append(f"{i}. {t['title']}{due}")
    return "\n".join(lines)


async def get_notes_text(db: Database) -> str:
    notes = await db.get_notes()
    if not notes:
        return "📝 Hozircha zametka yo'q."
    lines = ["📝 *Zametkalar:*\n"]
    for i, n in enumerate(notes, 1):
        pin   = "⭐ " if n["pinned"] else ""
        short = n["content"][:80] + ("..." if len(n["content"]) > 80 else "")
        lines.append(f"{i}. {pin}{short}")
    return "\n".join(lines)


async def get_report_text(db: Database) -> str:
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


async def show_tasks(msg: Message, db: Database):
    await msg.answer(await get_tasks_text(db))

async def show_notes(msg: Message, db: Database):
    await msg.answer(await get_notes_text(db))

async def show_report(msg: Message, db: Database):
    await msg.answer(await get_report_text(db))
