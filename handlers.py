"""
Handlers — Bot buyruqlari va xabarlarni qayta ishlash
Mexanik O'tkirbek uchun to'liq funksiyalar + ElevenLabs TTS
"""

import os
import re
import logging
import aiohttp
import tempfile
from datetime import datetime
from aiogram import Dispatcher, F
from aiogram.types import Message, BufferedInputFile
from aiogram.filters import Command

from database import Database
from ai_services import AIServices
from userbot import UserBot
from tts_service import TTSService
from mechanic_service import MechanicService

log = logging.getLogger(__name__)

OWNER_NAME = os.getenv("OWNER_NAME", "O'tkirbek")


def register_handlers(dp: Dispatcher, db: Database, ai: AIServices,
                      userbot: UserBot, owner_id: int):

    tts = TTSService()
    mech = MechanicService()

    def is_owner(msg: Message) -> bool:
        return msg.from_user.id == owner_id

    # ── /start ────────────────────────────────────────────────
    @dp.message(Command("start"))
    async def cmd_start(msg: Message):
        if not is_owner(msg): return
        await msg.answer(
            f"👋 *Salom, {OWNER_NAME}! Men sizning AI Agentingizman.*\n\n"
            "🏭 _AGMK 3-mis boyitish fabrika mexanigi uchun_\n\n"
            "🤖 Groq Llama 3 + Gemini 1.5 Flash + ElevenLabs TTS\n\n"
            "*Asosiy imkoniyatlar:*\n"
            "🔧 Texnik yordam va chertyo'j tahlili\n"
            "🦺 Xavfsizlik checklisti va hodisa yo'riqnomasi\n"
            "📊 Defekt akti, hisobot, xizmat xati\n"
            "📐 Gidravlik/pnevmatik hisob-kitob\n"
            "🎤 Ovoz → Matn va Matn → Ovoz (ElevenLabs)\n"
            "✉️ Nomingizdan xabar + ovozli xabar yuborish\n"
            "📝 Zametka, Vazifa, Xotira\n\n"
            "/help — barcha buyruqlar"
        )

    # ── /help ─────────────────────────────────────────────────
    @dp.message(Command("help"))
    async def cmd_help(msg: Message):
        if not is_owner(msg): return
        await msg.answer(
            "📖 *Buyruqlar ro'yxati:*\n\n"
            "🔧 *TEXNIK YORDAM:*\n"
            "`Nasos ishlamayapti` → muammo tahlili\n"
            "`Kompressor tekshirish tartibi` → checklist\n"
            "`Konveyerdagi muammo` → sabab + yechim\n\n"
            "🦺 *XAVFSIZLIK:*\n"
            "`Elektr ishi oldidan xavfsizlik` → checklist\n"
            "`Balandlikda ishlash xavfsizligi`\n"
            "`Baxtsiz hodisa bo'ldi` → ko'rsatma\n"
            "`Yong'in chiqdi` → avariya ko'rsatmasi\n\n"
            "📐 *HISOB-KITOB:*\n"
            "`Gidravlik hisob: sarif=50, diametr=100, uzunlik=200`\n"
            "`Pnevmatik hisob: hajm=10, bosim=8, vaqt=5`\n"
            "`Podshipnik resursi: C=50, P=20, n=1500`\n\n"
            "📋 *HUJJATLAR:*\n"
            "`Defekt akti: nasos №3 muhrlar yeyilgan`\n"
            "`Ish hisoboti: bugungi smenada...`\n"
            "`Xizmat xati: kimga=sexboshlig'i, mavzu=...`\n"
            "`PPR jadvali: nasos, kompressor, konveyер`\n\n"
            "🎤 *OVOZLI XABAR YUBORISH (ElevenLabs):*\n"
            "`Azizga ovozli yoz: kechikmoqdaman`\n"
            "`Shodiга ovoz: yig'ilishga 10 daqiqada keling`\n\n"
            "✉️ *MATNLI XABAR:*\n"
            "`Azizga yoz: ertaga uchrashemiz`\n"
            "`@username ga yoz: salom`\n\n"
            "📝 *ESLATMALAR:*\n"
            "`Eslab qol: shartnoma 15-may`\n"
            "`Vazifa: hisobot tayyorla, muddat 10-may`\n"
            "`Vazifa 3 bajarildi`\n\n"
            "💱 `Dollar kursi` | 🌤 `Toshkentda ob-havo`\n"
            "/tasks /notes /report /memory /cleanup\n"
            "/voices — ElevenLabs ovozlari"
        )

    # ── Buyruqlar ─────────────────────────────────────────────
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

    @dp.message(Command("voices"))
    async def cmd_voices(msg: Message):
        if not is_owner(msg): return
        wait = await msg.answer("🎙 _ElevenLabs ovozlari yuklanmoqda..._")
        voices = await tts.get_voices()
        if not voices:
            await wait.edit_text("❌ ElevenLabs ulanmagan. ELEVENLABS_API_KEY tekshiring.")
            return
        lines = ["🎙 *Mavjud ovozlar:*\n"]
        for v in voices[:10]:
            lines.append(f"• `{v['voice_id']}` — {v['name']}")
        lines.append("\n_Ovoz ID ni .env ga ELEVENLABS_VOICE_ID sifatida qo'shing_")
        await wait.edit_text("\n".join(lines))

    # ── Ovozli xabar (kiruvchi) ────────────────────────────────
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

            await wait.edit_text(f"🎤 *Eshitildi:*\n_{transcribed}_\n\n⏳ _Qayta ishlanmoqda..._")
            response = await process_text(transcribed, db, ai, userbot, owner_id, tts, mech)
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

    # ── Rasm / Chertyo'j ──────────────────────────────────────
    @dp.message(F.photo)
    async def handle_photo(msg: Message):
        if not is_owner(msg): return
        caption = msg.caption or ""
        wait  = await msg.answer("🖼 _Rasm tahlil qilinmoqda..._")
        photo = msg.photo[-1]
        file  = await msg.bot.get_file(photo.file_id)
        img   = (await msg.bot.download_file(file.file_path)).read()

        # Chertyo'j yoki oddiy rasm
        is_drawing = any(w in caption.lower() for w in
                         ['chertyo', 'sxema', 'chizma', 'drawing', 'scheme', 'план', 'чертёж'])
        result = await ai.analyze_image(img, caption if caption else "")
        prefix = "📐 *Chertyo'j Tahlili:*" if is_drawing else "🖼 *Rasm tahlili:*"
        await wait.edit_text(f"{prefix}\n\n{result}")

    # ── Matn ──────────────────────────────────────────────────
    @dp.message(F.text)
    async def handle_text(msg: Message):
        if not is_owner(msg): return

        await db.save_message(msg.from_user.id, "in", msg.text)
        await db.save_conversation("user", msg.text)
        await msg.bot.send_chat_action(msg.chat.id, "typing")

        response = await process_text(msg.text, db, ai, userbot, owner_id, tts, mech)
        await msg.answer(response)

        await db.save_message(msg.from_user.id, "out", response)
        await db.save_conversation("assistant", response)


# ── Intent tez aniqlash ───────────────────────────────────────
def quick_intent(text: str) -> tuple:
    t  = text.strip()
    tl = t.lower()

    # ── Ovozli xabar yuborish: "Azizga ovozli yoz: ..." ──────
    voice_send = re.search(
        r'^(.+?)\s+ga\s+ovoz(?:li)?\s+(?:yoz|yubor)(?:ing)?\s*[:\s]\s*(.+)$',
        t, re.IGNORECASE
    )
    if voice_send:
        return ("voice_send", {
            "target": voice_send.group(1).strip(),
            "content": voice_send.group(2).strip()
        })

    # ── Oddiy xabar yuborish ──────────────────────────────────
    send_match = re.search(
        r'^(.+?)\s+ga\s+yoz(?:ing)?\s*[:\s]\s*(.+)$', t, re.IGNORECASE
    )
    if send_match:
        return ("send_message", {
            "target": send_match.group(1).strip(),
            "content": send_match.group(2).strip()
        })

    # ── Kontaktlar ────────────────────────────────────────────
    if any(w in tl for w in ['kontaktlar', 'kontakt royxat', 'kimlar bor']):
        return ("contacts", {})

    # ── Zametka ───────────────────────────────────────────────
    note_m = re.match(
        r'^(?:eslab qol|zametka|yodda tut|saqlab qol|qeyd)[:\s]+(.+)$', t, re.IGNORECASE
    )
    if note_m:
        return ("save_note", {"content": note_m.group(1).strip()})

    # ── Vazifa ───────────────────────────────────────────────
    task_m = re.match(
        r'^(?:vazifa|topshiriq|todo|task)[:\s]+(.+)$', t, re.IGNORECASE
    )
    if task_m:
        content  = task_m.group(1).strip()
        deadline = None
        due_m = re.search(r',\s*muddat\s+(.+)$', content, re.IGNORECASE)
        if due_m:
            deadline = due_m.group(1).strip()
            content  = content[:due_m.start()].strip()
        return ("add_task", {"content": content, "deadline": deadline})

    # ── Vazifa bajarildi ──────────────────────────────────────
    done_m = re.search(r'vazifa\s+(\d+)\s+bajarildi', tl)
    if done_m:
        return ("done_task", {"task_id": done_m.group(1)})

    # ── Valyuta ───────────────────────────────────────────────
    if any(w in tl for w in ['dollar', 'kurs', 'valyuta', "so'm", 'som',
                               'evro', 'euro', 'rubl', 'usd', 'eur', 'rub']):
        amt_m = re.search(r'(\d[\d\s,.]*)[\s]*(dollar|usd|euro|evro|rubl|rub)', tl)
        amount = amt_m.group(1).replace(' ', '').replace(',', '.') if amt_m else None
        ctype  = amt_m.group(2) if amt_m else None
        return ("currency", {"amount": amount, "currency": ctype})

    # ── Ob-havo ───────────────────────────────────────────────
    if any(w in tl for w in ["ob-havo", "ob havo", "havo", "погода", "temperatura"]):
        city_m = re.search(r'(?:da|da|дa)\s+(?:ob-havo|havo)', tl)
        city = re.sub(r'\s+(?:da|дa)\s+.*', '', tl).strip() if city_m else "Olmaliq"
        return ("weather", {"city": city or "Olmaliq"})

    # ── Gidravlik hisob ───────────────────────────────────────
    if any(w in tl for w in ['gidravlik hisob', 'hydraulic', 'bosim yo\'q', 'truba hisob']):
        params = {}
        for pat, key in [(r'sarif[=:\s]+(\d+[\d.]*)', 'flow'),
                          (r'diametr?[=:\s]+(\d+[\d.]*)', 'dia'),
                          (r'uzunlik[=:\s]+(\d+[\d.]*)', 'length')]:
            m = re.search(pat, tl)
            if m: params[key] = float(m.group(1))
        return ("hydraulic_calc", params)

    # ── Pnevmatik hisob ───────────────────────────────────────
    if any(w in tl for w in ['pnevmatik hisob', 'kompressor quvvat', 'havo hisob']):
        params = {}
        for pat, key in [(r'hajm[=:\s]+(\d+[\d.]*)', 'vol'),
                          (r'bosim[=:\s]+(\d+[\d.]*)', 'pressure'),
                          (r'vaqt[=:\s]+(\d+[\d.]*)', 'time')]:
            m = re.search(pat, tl)
            if m: params[key] = float(m.group(1))
        return ("pneumatic_calc", params)

    # ── Podshipnik hisob ──────────────────────────────────────
    if any(w in tl for w in ['podshipnik resurs', 'bearing', 'podshipnik hisob']):
        params = {}
        for pat, key in [(r'c[=:\s]+(\d+[\d.]*)', 'C'),
                          (r'p[=:\s]+(\d+[\d.]*)', 'P'),
                          (r'n[=:\s]+(\d+[\d.]*)', 'n')]:
            m = re.search(pat, tl)
            if m: params[key] = float(m.group(1))
        return ("bearing_calc", params)

    # ── Qurilma muammolari ────────────────────────────────────
    equipment_words = ['nasos', 'kompressor', 'konveyер', 'tegirmon', 'flotatsiya',
                        'насос', 'компрессор', 'конвейер', 'мельниц']
    for eq in equipment_words:
        if eq in tl:
            return ("equipment_info", {"equipment": eq})

    # ── Xavfsizlik ───────────────────────────────────────────
    if any(w in tl for w in ['xavfsizlik', 'checklist', 'ruxsatnoma', 'xavfli ish',
                               'нарят', 'narad', 'допуск']):
        return ("safety_check", {"work_type": t})

    # ── Hodisa ───────────────────────────────────────────────
    if any(w in tl for w in ['hodisa', 'baxtsiz', 'yong\'in', "kimyo to'kildi",
                               'jarohat', 'qon', 'avaria', 'avariya']):
        return ("incident", {"incident_type": t})

    # ── Defekt akti ───────────────────────────────────────────
    if any(w in tl for w in ['defekt akt', 'defekt akti', 'nuqson dalolatnoma']):
        return ("defect_act", {"raw": t})

    # ── Ish hisoboti ──────────────────────────────────────────
    if any(w in tl for w in ['ish hisoboti', 'kunlik hisobot', 'smena hisoboti']):
        return ("work_report", {"raw": t})

    # ── Xizmat xati ───────────────────────────────────────────
    if any(w in tl for w in ['xizmat xati', 'xat yoz', 'служебная записка']):
        return ("service_letter", {"raw": t})

    # ── PPR jadvali ───────────────────────────────────────────
    if any(w in tl for w in ['ppr', 'profilaktik', 'ta\'mirlash jadvali', 'ТО ']):
        equip = re.findall(r'nasos|kompressor|konveyер|tegirmon|flotatsiya', tl)
        return ("ppr_schedule", {"equipment": equip or ["nasos", "kompressor"]})

    # ── Hisobot ───────────────────────────────────────────────
    if any(w in tl for w in ['haftalik hisobot', '/report']):
        return ("report", {})

    # ── Xotira ───────────────────────────────────────────────
    if '/memory' in tl or 'xotira holati' in tl:
        return ("memory", {})

    return (None, {})


# ── Asosiy xabar qayta ishlash ────────────────────────────────
async def process_text(text: str, db: Database, ai: AIServices,
                       userbot: UserBot, owner_id: int,
                       tts: TTSService, mech: MechanicService) -> str:
    action, data = quick_intent(text)

    if action is None:
        intent = await ai.detect_intent(text)
        action = intent.get("action", "chat")
        data   = intent

    # ── Xabar yuborish ────────────────────────────────────────
    if action == "send_message":
        return await action_send_message(data.get("target",""), data.get("content",""), userbot)

    # ── OVOZLI XABAR YUBORISH (ElevenLabs) ───────────────────
    elif action == "voice_send":
        return await action_send_voice_message(
            data.get("target",""), data.get("content",""), userbot, ai, tts
        )

    elif action == "contacts":
        return await action_get_contacts(userbot)

    elif action == "save_note":
        return await action_save_note(data.get("content") or text, db, ai)

    elif action == "add_task":
        return await action_add_task(data, db)

    elif action == "get_tasks":
        return await get_tasks_text(db)

    elif action == "done_task":
        task_id = data.get("task_id")
        if task_id:
            await db.complete_task(int(task_id))
            return f"✅ Vazifa #{task_id} bajarildi deb belgilandi!"
        return "❓ Qaysi vazifa? Masalan: `Vazifa 3 bajarildi`"

    elif action == "get_notes":
        return await get_notes_text(db)

    elif action == "currency":
        return await action_currency(data.get("amount"), data.get("currency"))

    elif action == "weather":
        return await action_weather(data.get("city") or "Olmaliq")

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

    # ── Mexanik maxsus funksiyalar ────────────────────────────
    elif action == "equipment_info":
        equip = data.get("equipment") or data.get("content", "nasos")
        return mech.get_equipment_info(equip)

    elif action == "safety_check":
        work = data.get("work_type") or text
        return mech.get_safety_checklist(work)

    elif action == "incident":
        return mech.get_incident_guide(data.get("incident_type") or text)

    elif action == "hydraulic_calc":
        flow   = data.get("flow", 50.0)
        dia    = data.get("dia", 100.0)
        length = data.get("length", 100.0)
        return mech.hydraulic_calc(flow, dia, length)

    elif action == "pneumatic_calc":
        vol      = data.get("vol", 10.0)
        pressure = data.get("pressure", 8.0)
        time_min = data.get("time", 5.0)
        return mech.pneumatic_calc(vol, pressure, time_min)

    elif action == "bearing_calc":
        C = data.get("C", 50.0)
        P = data.get("P", 20.0)
        n = data.get("n", 1500.0)
        return mech.bearing_calc(C, P, n)

    elif action == "defect_act":
        params = parse_document_params(data.get("raw",""), "defect")
        return mech.build_defect_act(params)

    elif action == "work_report":
        params = parse_document_params(data.get("raw",""), "report")
        return mech.build_work_report(params)

    elif action == "service_letter":
        params = parse_document_params(data.get("raw",""), "letter")
        return mech.build_service_letter(params)

    elif action == "ppr_schedule":
        equip = data.get("equipment", ["nasos", "kompressor"])
        return await mech.generate_ppr_schedule(equip)

    else:
        # Texnik savol yoki oddiy chat
        memories = await db.get_relevant_memories(text)
        context  = "\n".join(f"• {m}" for m in memories) if memories else ""
        history  = await db.get_conversation_history()
        return await ai.chat(text, history, context)


# ── Ovozli xabar yuborish (ElevenLabs + Userbot) ─────────────
async def action_send_voice_message(
    target: str, content: str,
    userbot: UserBot, ai: AIServices, tts: TTSService
) -> str:
    if not target or not content:
        return (
            "❓ Format:\n"
            "`Azizga ovozli yoz: kechikmoqdaman`\n"
            "`Shodiга ovoz: yig'ilish kechikadi`"
        )
    if not userbot.is_connected:
        return "❌ UserBot ulanmagan. TG_SESSION_STRING tekshiring."

    # 1. Vositachi matnini tuzish (AI yordamida)
    proxy_text = await ai.build_voice_proxy_text(content, os.getenv("OWNER_NAME", "O'tkirbek"))

    # 2. Matn → Ovoz (ElevenLabs)
    audio_bytes = await tts.text_to_speech(proxy_text)
    if not audio_bytes:
        # TTS ishlamasa — matnli xabar yuboramiz
        result = await userbot.send_message(target, f"[Ovozli xabar] {proxy_text}")
        if result["ok"]:
            return (
                f"⚠️ ElevenLabs ishlamadi, matnli xabar yuborildi:\n"
                f"*{result['name']}* ga:\n_{proxy_text}_"
            )
        return f"❌ Xabar yuborilmadi: {result['error']}"

    # 3. Ovoz faylini vaqtinchalik saqlash
    with tempfile.NamedTemporaryFile(suffix=".mp3", delete=False) as f:
        f.write(audio_bytes)
        tmp_path = f.name

    # 4. Userbot orqali ovozli xabar yuborish
    try:
        result = await userbot.send_voice(target, tmp_path)
        import os as _os
        _os.unlink(tmp_path)

        if result["ok"]:
            return (
                f"🎤 *{result['name']}* ga ovozli xabar yuborildi!\n\n"
                f"📝 _Matn:_ {proxy_text[:100]}{'...' if len(proxy_text)>100 else ''}"
            )
        return f"❌ Ovozli xabar yuborilmadi: {result.get('error','')}"
    except Exception as e:
        return f"❌ Ovozli xabar xatosi: {e}"


# ── Hujjat parametrlarini ajratib olish ──────────────────────
def parse_document_params(raw: str, doc_type: str) -> dict:
    """Matndan hujjat parametrlarini parse qilish"""
    params = {}
    # "qurilma:...", "joy:...", "nuqson:..." kabi pattern
    for key in ['qurilma', 'joy', 'nuqson', 'tamirlash', 'ehtiyot',
                'muddat', 'nomer', 'kimga', 'mavzu', 'matn', 'tel',
                'smena', 'bajarildi', 'muammo', 'sarf', 'keyingi', 'davom']:
        m = re.search(rf'{key}[=:\s]+([^,\n]+)', raw, re.IGNORECASE)
        if m:
            params[key] = m.group(1).strip()

    # Agar hech narsa topolmasa — xom matnni ishlatish
    if not params:
        if doc_type == "defect":
            params["nuqson"] = raw
        elif doc_type == "report":
            params["bajarildi"] = raw
        elif doc_type == "letter":
            params["matn"] = raw

    return params


# ── Qolgan harakatlar ─────────────────────────────────────────
async def action_send_message(target: str, content: str, userbot: UserBot) -> str:
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
        if amount and currency_type:
            amt = float(str(amount).replace(',', '.').replace(' ', ''))
            ccy_map = {'dollar': 'USD', 'usd': 'USD',
                       'euro': 'EUR',  'evro': 'EUR',
                       'rubl': 'RUB',  'rub': 'RUB'}
            ccy = ccy_map.get(str(currency_type).lower())
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
