"""
Handlers v3.0 — O'tkirbek AI Agent
Barcha funksiyalar: Vizual Defektoskopiya, HSE Audit, Sensor Tahlili,
Digital Twin, Knowledge Base RAG, AutoPilot, AutoReply boshqaruvi
"""

import os, re, logging, aiohttp, tempfile
from datetime import datetime
from aiogram import Dispatcher, F
from aiogram.types import Message, BufferedInputFile
from aiogram.filters import Command

from database      import Database
from ai_services   import AIServices
from userbot       import UserBot
from tts_service   import TTSService
from mechanic_service import MechanicService
from vision_service   import VisionService
from knowledge_base   import KnowledgeBase
from digital_twin     import DigitalTwin

log        = logging.getLogger(__name__)
OWNER_NAME = os.getenv("OWNER_NAME", "O'tkirbek")


def register_handlers(dp: Dispatcher, db: Database, ai: AIServices,
                      userbot: UserBot, owner_id: int, twin=None):

    tts        = TTSService()
    mech       = MechanicService()
    vis        = VisionService()
    kb         = KnowledgeBase()
    digit_twin = DigitalTwin()

    # PersonalTwin — Raqamli Egizak
    personal_twin = twin
    if personal_twin is None:
        try:
            from personal_twin import PersonalTwin as PT
            personal_twin = PT()
        except ImportError:
            personal_twin = None

    # ── Ishga tushganda KB va DigitTwin ni init qilish ───────
    import asyncio
    async def _init_services():
        await kb.init()
        await digit_twin.init()
        if personal_twin:
            await personal_twin.init_db()
    try:
        loop = asyncio.get_event_loop()
        if loop.is_running():
            loop.create_task(_init_services())
        else:
            loop.run_until_complete(_init_services())
    except Exception as e:
        import logging
        logging.getLogger(__name__).warning(f"Init: {e}")

    def is_owner(msg: Message) -> bool:
        return msg.from_user.id == owner_id

    # ════════════════════════════════════════════════════════
    #  BUYRUQLAR
    # ════════════════════════════════════════════════════════

    @dp.message(Command("start"))
    async def cmd_start(msg: Message):
        if not is_owner(msg): return
        await msg.answer(
            f"👋 *Salom, {OWNER_NAME}! Men sizning Raqamli Egizagingizman.*\n\n"
            f"🏭 _AGMK 3-mis boyitish fabrika mexanigi uchun_\n\n"
            f"🧠 *AI Stack:* Groq Llama3 + Gemini 1.5 Flash + ElevenLabs\n\n"
            f"*Nima qila olaman:*\n"
            f"🔬 Uskunadagi nosozliklarni rasmdan aniqlash\n"
            f"🦺 HSE auditi — PPE bor-yo'qligini tekshirish\n"
            f"📊 Sensor ma'lumotlarini tahlil + prognoz\n"
            f"📐 Chertyo'j o'qish (GOST, o'lchamlar, materiallar)\n"
            f"📚 MBF-3 bilim bazasi (Warman, GMD/ABB, flotatsiya)\n"
            f"🤖 AutoPilot — sizning nomingizdan suhbat\n"
            f"📈 Digital Twin — uskunalar holati dashboard\n"
            f"🎤 Ovozli xabar (ElevenLabs TTS)\n\n"
            f"/help — barcha buyruqlar ro'yxati"
        )

    @dp.message(Command("help"))
    async def cmd_help(msg: Message):
        if not is_owner(msg): return
        await msg.answer(
            "📖 *Buyruqlar:*\n\n"
            "🔬 *VIZUAL TAHLIL (rasm yuboring):*\n"
            "`[rasm] defekt` → nosozlik tahlili\n"
            "`[rasm] hse` → xavfsizlik auditi\n"
            "`[rasm] sensor` → sensor skrinshot tahlili\n"
            "`[rasm] chertyo'j` → kengaytirilgan tahlil\n\n"
            "📊 *DIGITAL TWIN:*\n"
            "`/dashboard` — barcha uskunalar holati\n"
            "`/equipment` — uskunalar ro'yxati\n"
            "`Holat: nasos_1, vib=3.2, temp=65` → yangilash\n"
            "`Prognoz: nasos_1` → AI prognoz\n"
            "`Tamirlash: nasos_1, turi=TO-2, ish=muhrlar almashtirildi`\n\n"
            "📚 *BILIM BAZASI:*\n"
            "`KB: warman nasos kaviatsiya` → qidiruv\n"
            "`/kb` — kategoriyalar\n"
            "[PDF] yuborish → bilim bazasiga qo'shish\n\n"
            "🤖 *AUTOPILOT:*\n"
            "`/autopilot_on` — yoqish (hammaga)\n"
            "`/autopilot_whitelist` — faqat ruxsatlilarga\n"
            "`/autopilot_off` — o'chirish\n"
            "`/autopilot_pause 60` — 60 daqiqa to'xtatish\n"
            "`/autopilot_status` — holat\n\n"
            "🔧 *TEXNIK YORDAM:*\n"
            "`Nasos ishlamayapti` / `Kompressor muammo`\n"
            "`Elektr ishi xavfsizligi` / `Yong'in chiqdi`\n"
            "`Gidravlik hisob: sarif=50, diametr=100, uzunlik=200`\n\n"
            "📋 *HUJJATLAR:*\n"
            "`Defekt akti:` / `Ish hisoboti:` / `PPR jadvali:`\n\n"
            "🎤 *OVOZLI XABAR:*\n"
            "`Azizga ovozli yoz: 15 daqiqa kechikaman`\n\n"
            "/tasks /notes /report /memory /cleanup /voices"
        )

    # ── Digital Twin ─────────────────────────────────────────
    @dp.message(Command("dashboard"))
    async def cmd_dashboard(msg: Message):
        if not is_owner(msg): return
        wait = await msg.answer("📊 _Dashboard yuklanmoqda..._")
        result = await digit_twin.get_dashboard()
        await wait.edit_text(result)

    @dp.message(Command("equipment"))
    async def cmd_equipment(msg: Message):
        if not is_owner(msg): return
        await msg.answer(digit_twin.get_equipment_list())

    # ── Knowledge Base ───────────────────────────────────────
    @dp.message(Command("kb"))
    async def cmd_kb(msg: Message):
        if not is_owner(msg): return
        cats = await kb.list_categories()
        lines = ["📚 *MBF-3 Bilim Bazasi*\n"]
        cat_emoji = {"slurry_pump":"🔩","GMD":"⚡","mill":"⚙️",
                      "flotation":"⚗️","conveyor":"🏗","standards":"📌",
                      "predictive":"🔮","digital_twin":"🤖","custom":"📄"}
        for cat, cnt in cats.items():
            e = cat_emoji.get(cat, "📄")
            lines.append(f"{e} {cat}: {cnt} ta hujjat")
        lines.append("\n_Qidirish:_ `KB: warman kaviatsiya`")
        lines.append("_PDF yuborish:_ bilim bazasiga qo'shiladi")
        await msg.answer("\n".join(lines))

    # ── AutoPilot / AutoReply boshqaruvi ─────────────────────
    @dp.message(Command("autopilot_on"))
    async def cmd_ap_on(msg: Message):
        if not is_owner(msg): return
        if userbot.auto_reply:
            userbot.auto_reply.enable()
            userbot.auto_reply.set_mode("on")
            await msg.answer("🟢 *AutoPilot YONDIRILDI*\n_Barcha xabarlarga O'tkirbek nomidan javob beriladi_")
        else:
            await msg.answer("❌ AutoReply moduli ulanmagan.")

    @dp.message(Command("autopilot_whitelist"))
    async def cmd_ap_whitelist(msg: Message):
        if not is_owner(msg): return
        if userbot.auto_reply:
            userbot.auto_reply.enable()
            userbot.auto_reply.set_mode("whitelist")
            wl = userbot.auto_reply.whitelist
            wl_str = ", ".join(wl) if wl else "bo'sh (AUTO_REPLY_WHITELIST .env)"
            await msg.answer(
                f"🟡 *AutoPilot WHITELIST REJIMI*\n\n"
                f"Faqat ruxsat etilgan kontaktlarga javob beriladi.\n"
                f"Whitelist: {wl_str}\n\n"
                f"_Yangi qo'shish:_ `Whitelist qo'sh: @username`"
            )
        else:
            await msg.answer("❌ AutoReply moduli ulanmagan.")

    @dp.message(Command("autopilot_off"))
    async def cmd_ap_off(msg: Message):
        if not is_owner(msg): return
        if userbot.auto_reply:
            userbot.auto_reply.disable()
            await msg.answer("⚫ *AutoPilot O'CHIRILDI*\n_Xabarlarga avtomatik javob berilmaydi_")
        else:
            await msg.answer("❌ AutoReply moduli ulanmagan.")

    @dp.message(Command("autopilot_pause"))
    async def cmd_ap_pause(msg: Message):
        if not is_owner(msg): return
        args = msg.text.split()
        minutes = int(args[1]) if len(args) > 1 and args[1].isdigit() else 60
        if userbot.auto_reply:
            userbot.auto_reply.pause(minutes)
            await msg.answer(f"⏸ *AutoPilot {minutes} daqiqa to'xtatildi*")
        else:
            await msg.answer("❌ AutoReply moduli ulanmagan.")

    @dp.message(Command("autopilot_status"))
    async def cmd_ap_status(msg: Message):
        if not is_owner(msg): return
        if userbot.auto_reply:
            status = userbot.auto_reply.get_status()
            wl = userbot.auto_reply.whitelist
            lines = [f"🤖 *AutoPilot holati:*\n{status}"]
            if wl:
                lines.append(f"\n📋 Whitelist ({len(wl)} ta):")
                lines.extend([f"  • {w}" for w in wl])
            await msg.answer("\n".join(lines))
        else:
            await msg.answer("❌ AutoReply moduli ulanmagan.")

    # ── Standart buyruqlar ───────────────────────────────────
    @dp.message(Command("tasks"))
    async def cmd_tasks(msg: Message):
        if not is_owner(msg): return
        await msg.answer(await get_tasks_text(db))

    @dp.message(Command("notes"))
    async def cmd_notes(msg: Message):
        if not is_owner(msg): return
        await msg.answer(await get_notes_text(db))

    @dp.message(Command("report"))
    async def cmd_report(msg: Message):
        if not is_owner(msg): return
        await msg.answer(await get_report_text(db))

    @dp.message(Command("memory"))
    async def cmd_memory(msg: Message):
        if not is_owner(msg): return
        stats = await db.get_all_memories_count()
        await msg.answer(
            f"🧠 *Xotira holati:*\n\n"
            f"📦 Jami: {stats['total']}\n"
            f"⭐ Doimiy: {stats['permanent']}\n"
            f"⏰ 7 kunda o'chadi: {stats['expiring_soon']}"
        )

    @dp.message(Command("cleanup"))
    async def cmd_cleanup(msg: Message):
        if not is_owner(msg): return
        deleted = await db.cleanup()
        await msg.answer(f"🗑 {deleted} ta eski yozuv o'chirildi.")

    @dp.message(Command("voices"))
    async def cmd_voices(msg: Message):
        if not is_owner(msg): return
        voices = await tts.get_voices()
        if not voices:
            await msg.answer("❌ ElevenLabs ulanmagan.")
            return
        lines = ["🎙 *ElevenLabs ovozlari:*\n"]
        for v in voices[:10]:
            lines.append(f"• `{v['voice_id']}` — {v['name']}")
        await msg.answer("\n".join(lines))

    # ════════════════════════════════════════════════════════
    #  MEDIA HANDLERLAR
    # ════════════════════════════════════════════════════════

    @dp.message(F.voice)
    async def handle_voice(msg: Message):
        if not is_owner(msg): return
        wait = await msg.answer("🎤 _Ovoz tahlil qilinmoqda..._")
        try:
            file  = await msg.bot.get_file(msg.voice.file_id)
            audio = (await msg.bot.download_file(file.file_path)).read()
            text  = await ai.transcribe_voice(audio)
            if not text:
                await wait.edit_text("❌ Ovozni tushunib bo'lmadi.")
                return
            await wait.edit_text(f"🎤 _Eshitildi:_ {text}\n\n⏳ _Qayta ishlanmoqda..._")
            resp = await process_text(text, db, ai, userbot, owner_id, tts, mech, vis, kb, digit_twin, personal_twin)
            await msg.answer(resp)
            await db.save_message(msg.from_user.id, "in", text, "voice")
        except Exception as e:
            await wait.edit_text(f"❌ Xatolik: {e}")

    @dp.message(F.document)
    async def handle_document(msg: Message):
        if not is_owner(msg): return
        if msg.document.mime_type != "application/pdf":
            await msg.answer("📎 Faqat PDF qabul qilinadi.")
            return
        wait  = await msg.answer("📄 _PDF qayta ishlanmoqda..._")
        file  = await msg.bot.get_file(msg.document.file_id)
        pdf_b = (await msg.bot.download_file(file.file_path)).read()

        caption = msg.caption or ""

        # KB ga qo'shish yoki oddiy tahlil
        if any(w in caption.lower() for w in ['kb', 'bilim', 'saqlash', 'qo\'sh', 'база']):
            text_content = await ai.analyze_pdf(pdf_b)
            doc_title = msg.document.file_name or "Noma'lum PDF"
            doc_id = await kb.add_document(
                title=doc_title,
                content=text_content[:3000],
                category="custom",
                tags=caption,
                source="user_upload"
            )
            await wait.edit_text(
                f"📚 *Bilim bazasiga qo'shildi!*\n\n"
                f"📄 Nom: {doc_title}\n"
                f"🔢 ID: {doc_id}\n"
                f"💡 Endi bu hujjat bo'yicha savol bera olasiz."
            )
        else:
            result = await ai.analyze_pdf(pdf_b)
            await wait.edit_text(f"📄 *PDF Tahlili:*\n\n{result[:3500]}")

    @dp.message(F.photo)
    async def handle_photo(msg: Message):
        if not is_owner(msg): return
        caption = (msg.caption or "").lower().strip()
        wait    = await msg.answer("🖼 _Tahlil qilinmoqda..._")

        photo = msg.photo[-1]
        file  = await msg.bot.get_file(photo.file_id)
        img   = (await msg.bot.download_file(file.file_path)).read()

        # Tahlil turini aniqlash
        if any(w in caption for w in ['defekt', 'nosozlik', 'tekshir', 'inspect', 'визуал']):
            eq = re.search(r'(?:uskuna|qurilma)[=:\s]+(\S+)', caption)
            eq_name = eq.group(1) if eq else ""
            result = await vis.defect_analysis(img, eq_name, msg.caption or "")
            await wait.edit_text(result[:4000])

        elif any(w in caption for w in ['hse', 'xavfsizlik', 'ppe', 'kiyim', 'helmet', 'kaska']):
            zone = re.search(r'(?:zona|zone|joy)[=:\s]+(.+)', caption)
            zone_name = zone.group(1) if zone else "Umumiy ish zonasi"
            result = await vis.hse_audit(img, zone_name)
            await wait.edit_text(result[:4000])

        elif any(w in caption for w in ['sensor', 'datchik', 'monitor', 'scada', 'skrinshot']):
            eq = re.search(r'(?:uskuna|eq)[=:\s]+(\S+)', caption)
            eq_name = eq.group(1) if eq else ""
            result = await vis.sensor_analysis("", eq_name, img)
            await wait.edit_text(result[:4000])

        elif any(w in caption for w in ['chertyo', 'sxema', 'chizma', 'drawing', 'plan', 'чертёж']):
            result = await vis.drawing_analysis(img, msg.caption or "")
            await wait.edit_text(result[:4000])

        else:
            # Har qanday sanoat rasmi uchun aqlli tahlil
            result = await ai.analyze_image(img, msg.caption or "")
            await wait.edit_text(f"🖼 *Rasm tahlili:*\n\n{result[:3500]}")

    @dp.message(Command("twin_status"))
    async def cmd_twin_status(msg: Message):
        if not is_owner(msg): return
        if personal_twin:
            stats = await personal_twin.get_stats()
            ready = "✅ Tayyor" if stats["ready"] else f"⏳ O'rganmoqda ({stats['samples']}/10)"
            await msg.answer(
                f"🤖 *Raqamli Egizak holati:*\n\n"
                f"📝 Namunalar: {stats['samples']} ta\n"
                f"📚 Bilimlar: {stats['knowledge']} ta\n"
                f"🔄 Yangilangan: {stats['updated']}\n"
                f"🟢 Holat: {ready}"
            )
        else:
            await msg.answer("❌ PersonalTwin moduli yuklanmagan.")

    @dp.message(Command("twin_add"))
    async def cmd_twin_add(msg: Message):
        if not is_owner(msg): return
        if not personal_twin:
            await msg.answer("❌ PersonalTwin moduli yuklanmagan.")
            return
        rest = msg.text.split(maxsplit=1)[1] if len(msg.text.split()) > 1 else ""
        if ":" in rest:
            topic, val = rest.split(":", 1)
        else:
            topic, val = "general", rest
        await personal_twin.add_knowledge(topic.strip(), val.strip())
        await msg.answer(f"✅ Bilim bazasiga qo'shildi:\n_{val.strip()}_")

    @dp.message(F.text)
    async def handle_text(msg: Message):
        if not is_owner(msg): return
        await db.save_message(msg.from_user.id, "in", msg.text)
        await db.save_conversation("user", msg.text)
        await msg.bot.send_chat_action(msg.chat.id, "typing")

        # PersonalTwin — suhbatdan o'rganish
        if personal_twin:
            await personal_twin.learn_from_message(msg.text)

        resp = await process_text(
            msg.text, db, ai, userbot, owner_id, tts, mech, vis, kb, digit_twin, personal_twin
        )
        await msg.answer(resp[:4000])
        await db.save_message(msg.from_user.id, "out", resp)
        await db.save_conversation("assistant", resp)


# ════════════════════════════════════════════════════════════
#  INTENT ANIQLASH
# ════════════════════════════════════════════════════════════

def quick_intent(text: str) -> tuple:
    t, tl = text.strip(), text.strip().lower()

    # Ovozli xabar
    m = re.search(r'^(.+?)\s+ga\s+ovoz(?:li)?\s+(?:yoz|yubor)\s*[:\s]\s*(.+)$', t, re.I)
    if m: return ("voice_send", {"target": m.group(1).strip(), "content": m.group(2).strip()})

    # Matnli xabar
    m = re.search(r'^(.+?)\s+ga\s+yoz(?:ing)?\s*[:\s]\s*(.+)$', t, re.I)
    if m: return ("send_message", {"target": m.group(1).strip(), "content": m.group(2).strip()})

    # Whitelist boshqaruv
    m = re.search(r'whitelist\s+(?:qo\'sh|add)[:\s]+(.+)', tl)
    if m: return ("whitelist_add", {"contact": m.group(1).strip()})

    # Digital Twin — holat yangilash
    m = re.search(r'^holat:\s*(\w+)(.*)', tl)
    if m:
        params = {"equipment_id": m.group(1)}
        rest = m.group(2)
        for pat, key in [(r'vib[=:\s]+([\d.]+)', 'vibration'),
                          (r'temp[=:\s]+([\d.]+)', 'temperature'),
                          (r'bosim[=:\s]+([\d.]+)', 'pressure'),
                          (r'runtime[=:\s]+([\d.]+)', 'runtime_h'),
                          (r'status[=:\s]+(\w+)', 'status')]:
            pm = re.search(pat, rest, re.I)
            if pm:
                params[key] = float(pm.group(1)) if key != 'status' else pm.group(1)
        note_m = re.search(r'(?:izoh|nota)[=:\s]+(.+)', rest, re.I)
        if note_m: params['notes'] = note_m.group(1)
        return ("twin_update", params)

    # Digital Twin — prognoz
    if re.match(r'^prognoz:\s*\w+', tl):
        eq = re.search(r'prognoz:\s*(\w+)', tl)
        return ("twin_predict", {"equipment_id": eq.group(1) if eq else ""})

    # Digital Twin — ta'mirlash logi
    m = re.search(r'^tamirlash:\s*(\w+)', tl)
    if m:
        params = {"equipment_id": m.group(1)}
        for pat, key in [(r'turi[=:\s]+([^,\n]+)', 'work_type'),
                          (r'ish[=:\s]+([^,\n]+)', 'description'),
                          (r'qism[=:\s]+([^,\n]+)', 'parts_used'),
                          (r'vaqt[=:\s]+([\d.]+)', 'duration_h')]:
            pm = re.search(pat, tl, re.I)
            if pm: params[key] = pm.group(1).strip()
        return ("twin_maintenance", params)

    # KB qidiruv
    m = re.search(r'^(?:kb|bilim|база)[:\s]+(.+)', tl)
    if m: return ("kb_search", {"query": m.group(1).strip()})

    # Zametka
    m = re.match(r'^(?:eslab qol|zametka|yodda tut|saqlab qol|qeyd)[:\s]+(.+)', t, re.I)
    if m: return ("save_note", {"content": m.group(1).strip()})

    # Vazifa
    m = re.match(r'^(?:vazifa|topshiriq|todo|task)[:\s]+(.+)', t, re.I)
    if m:
        content = m.group(1).strip()
        due = None
        dm = re.search(r',\s*muddat\s+(.+)$', content, re.I)
        if dm:
            due = dm.group(1).strip()
            content = content[:dm.start()].strip()
        return ("add_task", {"content": content, "deadline": due})

    # Vazifa bajarildi
    m = re.search(r'vazifa\s+(\d+)\s+bajarildi', tl)
    if m: return ("done_task", {"task_id": m.group(1)})

    # Valyuta
    if any(w in tl for w in ['dollar','kurs','valyuta','evro','rubl','usd','eur','rub']):
        am = re.search(r'(\d[\d\s,.]*)[\s]*(dollar|usd|euro|evro|rubl|rub)', tl)
        return ("currency", {"amount": am.group(1) if am else None,
                              "currency": am.group(2) if am else None})

    # Ob-havo
    if any(w in tl for w in ["ob-havo","ob havo","havo","погода","temperatura"]):
        cm = re.search(r'(\w+)\s+(?:da|dagi)?\s*(?:ob-havo|havo)', tl)
        return ("weather", {"city": cm.group(1) if cm else "Olmaliq"})

    # Hisob-kitoblar
    if any(w in tl for w in ['gidravlik hisob','hydraulic','truba hisob']):
        params = {}
        for pat, key in [(r'sarif[=:\s]+([\d.]+)','flow'),(r'diametr?[=:\s]+([\d.]+)','dia'),(r'uzunlik[=:\s]+([\d.]+)','length')]:
            pm = re.search(pat, tl)
            if pm: params[key] = float(pm.group(1))
        return ("hydraulic_calc", params)

    if any(w in tl for w in ['pnevmatik hisob','kompressor quvvat','havo hisob']):
        params = {}
        for pat, key in [(r'hajm[=:\s]+([\d.]+)','vol'),(r'bosim[=:\s]+([\d.]+)','pressure'),(r'vaqt[=:\s]+([\d.]+)','time')]:
            pm = re.search(pat, tl)
            if pm: params[key] = float(pm.group(1))
        return ("pneumatic_calc", params)

    if any(w in tl for w in ['podshipnik resurs','bearing calc']):
        params = {}
        for pat, key in [(r'\bc[=:\s]+([\d.]+)','C'),(r'\bp[=:\s]+([\d.]+)','P'),(r'\bn[=:\s]+([\d.]+)','n')]:
            pm = re.search(pat, tl)
            if pm: params[key] = float(pm.group(1))
        return ("bearing_calc", params)

    # Qurilma muammolari
    for eq in ['nasos','kompressor','konveyер','tegirmon','flotatsiya']:
        if eq in tl:
            return ("equipment_info", {"equipment": eq})

    # Xavfsizlik
    if any(w in tl for w in ['xavfsizlik','checklist','ruxsatnoma','xavfli ish']):
        return ("safety_check", {"work_type": t})

    # Hodisa
    if any(w in tl for w in ["hodisa","baxtsiz","yong'in","jarohat","avaria","avariya"]):
        return ("incident", {"incident_type": t})

    # Hujjatlar
    if any(w in tl for w in ['defekt akt','defekt akti','nuqson dalolatnoma']):
        return ("defect_act", {"raw": t})
    if any(w in tl for w in ['ish hisoboti','kunlik hisobot','smena hisoboti']):
        return ("work_report", {"raw": t})
    if any(w in tl for w in ['xizmat xati','xat yoz']):
        return ("service_letter", {"raw": t})
    if any(w in tl for w in ['ppr','profilaktik',"ta'mirlash jadvali"]):
        equip = re.findall(r'nasos|kompressor|konveyер|tegirmon|flotatsiya', tl)
        return ("ppr_schedule", {"equipment": equip or ["nasos","kompressor"]})

    # Hisobot va xotira
    if '/report' in tl: return ("report", {})
    if '/memory' in tl or 'xotira holati' in tl: return ("memory", {})

    return (None, {})


# ════════════════════════════════════════════════════════════
#  ASOSIY QAYTA ISHLASH
# ════════════════════════════════════════════════════════════

async def process_text(text: str, db: Database, ai: AIServices,
                       userbot: UserBot, owner_id: int,
                       tts: TTSService, mech: MechanicService,
                       vis: VisionService, kb: KnowledgeBase,
                       dt: DigitalTwin,
                       personal_twin=None) -> str:

    action, data = quick_intent(text)
    if action is None:
        intent = await ai.detect_intent(text)
        action = intent.get("action", "chat")
        data   = intent

    # ── Ovozli xabar ────────────────────────────────────────
    if action == "voice_send":
        return await action_send_voice_message(
            data.get("target",""), data.get("content",""), userbot, ai, tts)

    elif action == "send_message":
        return await action_send_message(data.get("target",""), data.get("content",""), userbot)

    elif action == "contacts":
        return await action_get_contacts(userbot)

    # ── Whitelist ────────────────────────────────────────────
    elif action == "whitelist_add":
        if userbot.auto_reply:
            userbot.auto_reply.add_to_whitelist(data.get("contact",""))
            return f"✅ Whitelist ga qo'shildi: `{data.get('contact')}`"
        return "❌ AutoReply ulanmagan."

    # ── Digital Twin ─────────────────────────────────────────
    elif action == "twin_update":
        eq_id = data.pop("equipment_id", "")
        return await dt.update_state(eq_id, **data)

    elif action == "twin_predict":
        return await dt.get_ai_prediction(data.get("equipment_id",""))

    elif action == "twin_maintenance":
        eq_id = data.pop("equipment_id", "")
        return await dt.add_maintenance_log(
            eq_id,
            work_type  = data.get("work_type","Ta'mirlash"),
            description= data.get("description",""),
            parts_used = data.get("parts_used",""),
            duration_h = float(data.get("duration_h",0)) if data.get("duration_h") else None
        )

    # ── Knowledge Base ────────────────────────────────────────
    elif action == "kb_search":
        query = data.get("query", text)
        result = await kb.answer_with_rag(query)
        return result or "❓ Bilim bazasida ma'lumot topilmadi."

    # ── Zametka/Vazifa ────────────────────────────────────────
    elif action == "save_note":
        return await action_save_note(data.get("content") or text, db, ai)

    elif action == "add_task":
        return await action_add_task(data, db)

    elif action == "get_tasks":
        return await get_tasks_text(db)

    elif action == "done_task":
        tid = data.get("task_id")
        if tid:
            await db.complete_task(int(tid))
            return f"✅ Vazifa #{tid} bajarildi!"
        return "❓ Qaysi vazifa?"

    elif action == "get_notes":
        return await get_notes_text(db)

    elif action == "currency":
        return await action_currency(data.get("amount"), data.get("currency"))

    elif action == "weather":
        return await action_weather(data.get("city","Olmaliq"))

    elif action == "report":
        return await get_report_text(db)

    elif action == "memory":
        stats = await db.get_all_memories_count()
        return (f"🧠 *Xotira:* Jami:{stats['total']} | "
                f"Doimiy:{stats['permanent']} | Eskirmoqda:{stats['expiring_soon']}")

    # ── Mexanik funksiyalar ───────────────────────────────────
    elif action == "equipment_info":
        return mech.get_equipment_info(data.get("equipment","nasos"))

    elif action == "safety_check":
        return mech.get_safety_checklist(data.get("work_type") or text)

    elif action == "incident":
        return mech.get_incident_guide(data.get("incident_type") or text)

    elif action == "hydraulic_calc":
        return mech.hydraulic_calc(data.get("flow",50), data.get("dia",100), data.get("length",100))

    elif action == "pneumatic_calc":
        return mech.pneumatic_calc(data.get("vol",10), data.get("pressure",8), data.get("time",5))

    elif action == "bearing_calc":
        return mech.bearing_calc(data.get("C",50), data.get("P",20), data.get("n",1500))

    elif action == "defect_act":
        return mech.build_defect_act(parse_doc_params(data.get("raw",""),"defect"))

    elif action == "work_report":
        return mech.build_work_report(parse_doc_params(data.get("raw",""),"report"))

    elif action == "service_letter":
        return mech.build_service_letter(parse_doc_params(data.get("raw",""),"letter"))

    elif action == "ppr_schedule":
        return await mech.generate_ppr_schedule(data.get("equipment",["nasos"]))

    else:
        # ── RAG + AI suhbat ─────────────────────────────────
        # Avval KB dan qidirish
        kb_answer = await kb.answer_with_rag(text)
        if kb_answer:
            return kb_answer

        # PersonalTwin bilan javob (siz kabi gapiradi)
        if personal_twin:
            memories = await db.get_relevant_memories(text)
            context  = "\n".join(f"• {m}" for m in memories) if memories else ""
            history  = await db.get_conversation_history()
            # PersonalTwin uslubda javob
            reply = await personal_twin.generate_reply(text, "")
            if reply:
                return reply

        # Oddiy AI chat (fallback)
        memories = await db.get_relevant_memories(text)
        context  = "\n".join(f"• {m}" for m in memories) if memories else ""
        history  = await db.get_conversation_history()
        return await ai.chat(text, history, context)


# ════════════════════════════════════════════════════════════
#  YORDAMCHI FUNKSIYALAR
# ════════════════════════════════════════════════════════════

def parse_doc_params(raw: str, doc_type: str) -> dict:
    params = {}
    for key in ['qurilma','joy','nuqson','tamirlash','ehtiyot','muddat','nomer',
                'kimga','mavzu','matn','tel','smena','bajarildi','muammo','sarf','keyingi','davom']:
        m = re.search(rf'{key}[=:\s]+([^,\n]+)', raw, re.I)
        if m: params[key] = m.group(1).strip()
    if not params:
        if doc_type == "defect": params["nuqson"] = raw
        elif doc_type == "report": params["bajarildi"] = raw
        elif doc_type == "letter": params["matn"] = raw
    return params


async def action_send_voice_message(target, content, userbot, ai, tts):
    if not target or not content:
        return "❓ Format:\n`Azizga ovozli yoz: kechikmoqdaman`"
    if not userbot.is_connected:
        return "❌ UserBot ulanmagan."
    proxy = await ai.build_voice_proxy_text(content, OWNER_NAME)
    audio = await tts.text_to_speech(proxy)
    if not audio:
        res = await userbot.send_message(target, f"[Ovozli xabar] {proxy}")
        if res["ok"]: return f"⚠️ TTS ishlamadi, matnli xabar yuborildi: *{res['name']}*"
        return f"❌ Yuborilmadi: {res['error']}"
    with tempfile.NamedTemporaryFile(suffix=".mp3", delete=False) as f:
        f.write(audio); tmp = f.name
    try:
        res = await userbot.send_voice(target, tmp)
        os.unlink(tmp)
        if res["ok"]:
            return (f"🎤 *{res['name']}* ga ovozli xabar yuborildi!\n"
                    f"_Matn:_ {proxy[:100]}{'...' if len(proxy)>100 else ''}")
        return f"❌ Yuborilmadi: {res.get('error','')}"
    except Exception as e:
        return f"❌ Ovozli xabar xatosi: {e}"


async def action_send_message(target, content, userbot):
    if not target or not content:
        return "❓ Format:\n`Azizga yoz: ertaga uchrashemiz`"
    if not userbot.is_connected:
        return "❌ UserBot ulanmagan."
    res = await userbot.send_message(target, content)
    return (f"✅ *{res['name']}* ga xabar yuborildi:\n_{content}_"
            if res["ok"] else f"❌ Yuborilmadi: {res['error']}")


async def action_get_contacts(userbot):
    if not userbot.is_connected: return "❌ UserBot ulanmagan."
    contacts = await userbot.get_contacts_list()
    if not contacts: return "📋 Kontaktlar topilmadi."
    lines = ["📋 *Kontaktlaringiz:*\n"]
    for i, c in enumerate(contacts[:30], 1):
        u = f" (@{c['username']})" if c['username'] else ""
        lines.append(f"{i}. {c['name']}{u}")
    if len(contacts) > 30: lines.append(f"\n_+{len(contacts)-30} ta_")
    return "\n".join(lines)


async def action_save_note(content, db, ai):
    imp  = await ai.score_importance(content)
    perm = imp >= 0.75
    await db.add_note(content, is_pinned=perm)
    await db.save_memory(content, "note", perm, imp)
    flag = "\n⭐ _Muhim — doimiy saqlandi_" if perm else ""
    return f"✅ *Zametka saqlandi!*{flag}\n\n_{content}_"


async def action_add_task(data, db):
    title = data.get("content","")
    due   = data.get("deadline")
    tid   = await db.add_task(title, title, due)
    return f"✅ Vazifa #{tid}:\n*{title}*" + (f"\n📅 {due}" if due else "")


async def action_currency(amount=None, ctype=None):
    try:
        async with aiohttp.ClientSession() as s:
            async with s.get("https://cbu.uz/uz/arkhiv-kursov-valyut/json/",
                              timeout=aiohttp.ClientTimeout(total=10)) as r:
                data = await r.json(content_type=None)
        rates = {d["Ccy"]: float(d["Rate"]) for d in data}
        res = (f"💱 *Valyuta (CBU)* _{datetime.now().strftime('%d.%m.%Y')}_\n\n"
               f"🇺🇸 USD: {rates.get('USD',0):,.0f} so'm\n"
               f"🇪🇺 EUR: {rates.get('EUR',0):,.0f} so'm\n"
               f"🇷🇺 RUB: {rates.get('RUB',0):.2f} so'm")
        if amount and ctype:
            ccy = {'dollar':'USD','usd':'USD','euro':'EUR','evro':'EUR','rubl':'RUB','rub':'RUB'}.get(str(ctype).lower())
            if ccy:
                total = float(str(amount).replace(',','.').replace(' ','')) * rates.get(ccy,0)
                res += f"\n\n💰 = *{total:,.0f} so'm*"
        return res
    except Exception as e:
        return f"❌ Kurs xatosi: {e}"


async def action_weather(city):
    key = os.getenv("WEATHER_API_KEY","")
    if not key: return "❌ WEATHER_API_KEY yo'q."
    try:
        async with aiohttp.ClientSession() as s:
            async with s.get(
                f"https://api.openweathermap.org/data/2.5/weather?q={city}&appid={key}&units=metric&lang=ru",
                timeout=aiohttp.ClientTimeout(total=10)
            ) as r:
                d = await r.json()
        if d.get("cod") != 200: return f"❌ {city} topilmadi."
        return (f"🌤 *{d['name']}:* {round(d['main']['temp'])}°C\n"
                f"☁️ {d['weather'][0]['description']}\n"
                f"💧 {d['main']['humidity']}% | 💨 {d['wind']['speed']} m/s")
    except Exception as e:
        return f"❌ Ob-havo xatosi: {e}"


async def get_tasks_text(db):
    tasks = await db.get_tasks()
    if not tasks: return "✅ Faol vazifalar yo'q."
    lines = ["📋 *Vazifalar:*\n"]
    for i, t in enumerate(tasks, 1):
        due = f" — _{t['due'][:10]}_" if t["due"] else ""
        lines.append(f"{i}. {t['title']}{due}")
    return "\n".join(lines)


async def get_notes_text(db):
    notes = await db.get_notes()
    if not notes: return "📝 Zametka yo'q."
    lines = ["📝 *Zametkalar:*\n"]
    for i, n in enumerate(notes, 1):
        pin   = "⭐ " if n["pinned"] else ""
        short = n["content"][:80] + ("..." if len(n["content"]) > 80 else "")
        lines.append(f"{i}. {pin}{short}")
    return "\n".join(lines)


async def get_report_text(db):
    stats = await db.get_weekly_stats()
    return (f"📊 *Haftalik Hisobot* _{datetime.now().strftime('%d.%m.%Y')}_\n\n"
            f"💬 {stats['messages']} xabar | 📝 {stats['notes']} zametka\n"
            f"✅ {stats['done']} bajarildi | ⏳ {stats['pending']} kutmoqda")
