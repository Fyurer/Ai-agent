"""
Handlers v3.0 — Õtkirbek AI Agent
Barcha funksiyalar: Vizual Defektoskopiya, HSE Audit, Sensor Tahlili,
Digital Twin, Knowledge Base RAG, AutoPilot, AutoReply boshqaruvi
"""

import os, re, logging, aiohttp, tempfile, json, uuid
from datetime import datetime
from aiogram import Dispatcher, F
from aiogram.types import (Message, BufferedInputFile,
                           InlineKeyboardMarkup, InlineKeyboardButton,
                           CallbackQuery)
from aiogram.filters import Command

# ── Ovoz buyruqlari vaqtinchalik xotirasi (callback_data 64b limit) ──
_VOICE_CMD_STORE: dict = {}   # {uid: {"action":..,"data":..,"text":..}}

from database      import Database
from ai_services   import AIServices
from userbot       import UserBot
from tts_service   import TTSService
from mechanic_service import MechanicService
from vision_service   import VisionService
from knowledge_base   import KnowledgeBase
from digital_twin     import DigitalTwin
from auto_learner     import AutoLearner

log        = logging.getLogger(__name__)
OWNER_NAME = os.getenv("OWNER_NAME", "Õtkirbek")


def register_handlers(dp: Dispatcher, db: Database, ai: AIServices,
                      userbot: UserBot, owner_id: int, twin=None, learner=None):

    tts        = TTSService()
    mech       = MechanicService()
    vis        = VisionService()
    kb         = KnowledgeBase()
    digit_twin = DigitalTwin()

    # PersonalTwin — Raqamli Egizak
    personal_twin = twin

    # AutoLearner
    auto_learner = learner
    if auto_learner is None:
        try:
            auto_learner = AutoLearner(kb=kb)
        except Exception as _ale:
            auto_learner = None
            log.warning(f'AutoLearner init xatosi: {_ale}')
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
        try:
            await digit_twin.init()
        except Exception as e:
            import logging
            logging.getLogger(__name__).warning(f"DigitalTwin init xatosi: {e}")
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
            f"👋 *Salom, {OWNER_NAME}! Men sizning shaxsiy AI yordamchingizman.*\n\n"
            f"💻 _Professional dasturchi va texnologiya mutaxassisi uchun_\n\n"
            f"🧠 *AI Stack:* Groq Llama3 + Gemini Flash + ElevenLabs\n\n"
            f"*Nima qila olaman:*\n"
            f"💻 Kod yozish — Python, JS, SQL, Bash va boshqalar\n"
            f"🐛 Xato tuzatish — debug, error tahlil, tuzatilgan kod\n"
            f"🤖 Bot va API integratsiya — Telegram, aiogram, REST\n"
            f"🐳 DevOps — Docker, Railway, CI/CD, server sozlash\n"
            f"🔬 Rasm tahlili — defekt, HSE, sensor, chizma\n"
            f"📊 Digital Twin — uskunalar holati dashboard\n"
            f"🎤 Ovozli xabar va AutoPilot\n"
            f"📚 Bilim bazasi (RAG qidiruv)\n\n"
            f"/help — barcha buyruqlar ro'yxati"
        )

    @dp.message(Command("help"))
    async def cmd_help(msg: Message):
        if not is_owner(msg): return
        await msg.answer(
            "📖 *Buyruqlar:*\n\n"
            "💻 *KOD VA TEXNOLOGIYA (asosiy):*\n"
            "`Python kodi yoz: ...` → to'liq ishlaydigan kod\n"
            "`Xatoni tuzat: [kod]` → debug + tuzatma\n"
            "`API qanday ulash: ...` → qadamba-qadam\n"
            "`Docker Compose yoz: ...` → tayyor config\n"
            "`SQL query: ...` → optimallashtirilgan so'rov\n"
            "`Bash script: ...` → avtomatlashtirish\n\n"
            "🔬 *VIZUAL TAHLIL (rasm yuboring):*\n"
            "`[rasm] defekt` → nosozlik tahlili\n"
            "`[rasm] hse` → xavfsizlik auditi\n"
            "`[rasm] sensor` → sensor skrinshot tahlili\n"
            "`[rasm] chertyo'j` → kengaytirilgan tahlil\n\n"
            "📊 *DIGITAL TWIN:*\n"
            "`/dashboard` — barcha uskunalar holati\n"
            "`/equipment` — uskunalar ro'yxati\n\n"
            "📋 *VAZIFALAR:*\n"
            "`/tasks` — ro'yxat\n"
            "`/task_add Sarlavha, soat 14:30`\n"
            "`Vazifa <N> bajarildi`\n\n"
            "📚 *BILIM BAZASI:*\n"
            "`KB: <savol>` → RAG qidiruv\n"
            "[PDF] yuborish → bazaga qo'shish\n\n"
            "🤖 *AUTOPILOT:*\n"
            "`/autopilot_on` / `/autopilot_off` / `/autopilot_status`\n\n"
            "/notes /report /memory"
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
            await msg.answer("🟢 *AutoPilot YONDIRILDI*\n_Barcha xabarlarga Õtkirbek nomidan javob beriladi_")
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

    @dp.message(Command("task_add"))
    async def cmd_task_add(msg: Message):
        """
        /task_add Nasosni tekshirish, soat 14:30
        /task_add Hisobot yozish, ertaga 09:00
        /task_add Yig'ilish, 25.07.2025 10:00
        """
        if not is_owner(msg): return
        parts = msg.text.split(maxsplit=1)
        if len(parts) < 2 or not parts[1].strip():
            await msg.answer(
                "📋 *Vazifa qo'shish formati:*\n\n"
                "`/task_add Sarlavha, soat 14:30`\n"
                "`/task_add Sarlavha, ertaga 09:00`\n"
                "`/task_add Sarlavha, 25.07.2025 10:00`\n"
                "`/task_add Sarlavha, 2 soatdan keyin`\n"
                "`/task_add Sarlavha` ← vaqtsiz"
            )
            return
        raw  = parts[1].strip()
        # Vergul bilan ajratilgan vaqt
        if "," in raw:
            idx  = raw.index(",")
            title = raw[:idx].strip()
            due   = raw[idx+1:].strip()
        else:
            title = raw
            due   = None
        result = await action_add_task({"content": title, "deadline": due}, db)
        await msg.answer(result)

    @dp.message(Command("notes"))
    async def cmd_notes(msg: Message):
        if not is_owner(msg): return
        await msg.answer(await get_notes_text(db))

    # ── Ehtiyot qismlar kalkulyatori ─────────────────────────
    @dp.message(Command("spare_parts"))
    async def cmd_spare_parts(msg: Message):
        """
        /spare_parts nasos 5000
        /spare_parts kompressor 2000 og'ir
        """
        if not is_owner(msg): return
        parts = msg.text.split(maxsplit=3)
        if len(parts) < 3:
            await msg.answer(
                "🔩 *Ehtiyot qismlar kalkulyatori*\n\n"
                "Format: `/spare_parts <uskuna> <ish_soati> [intensivlik]`\n\n"
                "Misol:\n"
                "`/spare_parts nasos 5000`\n"
                "`/spare_parts kompressor 2000 og'ir`\n"
                "`/spare_parts tegirmon 8000 yumshoq`\n\n"
                "_Intensivlik: yumshoq | o'rtacha | og'ir_"
            )
            return
        equip     = parts[1]
        runtime   = float(parts[2]) if parts[2].isdigit() else 0
        intensity = parts[3] if len(parts) > 3 else "o'rtacha"
        result    = mech.spare_parts_calc(equip, runtime, intensity)
        await msg.answer(result)

    # ── Zayavka generatori ───────────────────────────────────
    @dp.message(Command("zayavka"))
    async def cmd_zayavka(msg: Message):
        """
        /zayavka nasosga 3 ta salnk kerak
        /zayavka Warman nasos: 2 dona impeller
        """
        if not is_owner(msg): return
        parts = msg.text.split(maxsplit=1)
        if len(parts) < 2:
            await msg.answer(
                "📋 *Zayavka generatori*\n\n"
                "Format: `/zayavka <tavsif>`\n\n"
                "Misol:\n"
                "`/zayavka nasosga 3 ta salnk kerak`\n"
                "`/zayavka kompressor filtri 2 dona, TO-500`\n"
                "`/zayavka Warman 6/4 uchun 1 impeller`"
            )
            return
        desc   = parts[1]
        # Uskuna nomini ajratish
        eq_m   = re.search(r'(nasos|kompressor|tegirmon|konveyer|flotatsiya|warman|[\w]+)\s+(?:uchun|ga|da)', desc, re.I)
        eq     = eq_m.group(1) if eq_m else ""
        result = mech.generate_zayavka(desc, equip_name=eq)
        await msg.answer(result)

    # ── QR-kod ─────────────────────────────────────────────
    @dp.message(Command("qr"))
    async def cmd_qr_lookup(msg: Message):
        """
        /qr nasos_1
        /qr ID=EQ-2024-0042
        """
        if not is_owner(msg): return
        parts = msg.text.split(maxsplit=1)
        if len(parts) < 2:
            await msg.answer(
                "📱 *QR-kod qidirish*\n\n"
                "Format: `/qr <qr_matn_yoki_id>`\n\n"
                "Misol:\n"
                "`/qr nasos_1`\n"
                "`/qr ID=EQ-2024-0042`\n\n"
                "_Yoki telefonda QR skanerlangan matnni yuboring_"
            )
            return
        qr_data = parts[1].strip()
        # Digital Twin dan tarix olish
        try:
            history = await digit_twin.get_maintenance_history(qr_data)
        except Exception:
            history = None
        result = mech.lookup_equipment_by_qr(qr_data, db_records=history)
        await msg.answer(result)

    # ── Avariya simulyatori ──────────────────────────────────
    @dp.message(Command("avaria"))
    async def cmd_avaria(msg: Message):
        """
        /avaria tegirmonning moylanish tizimi ishdan chiqsa
        /avaria flotatsiya kompressori to'xtasa
        """
        if not is_owner(msg): return
        parts = msg.text.split(maxsplit=1)
        if len(parts) < 2:
            await msg.answer(
                "🚨 *Avariya ssenariysi simulyatori*\n\n"
                "Format: `/avaria <stsenariy>`\n\n"
                "Misol:\n"
                "`/avaria tegirmonning moylanish tizimi ishdan chiqsa`\n"
                "`/avaria flotatsiya nasosi to'xtasa`\n"
                "`/avaria konveyer lentasi uzilsa`"
            )
            return
        scenario = parts[1].strip()
        wait     = await msg.answer("⚙️ _Stsenariy tahlil qilinmoqda..._")
        result   = await mech.simulate_accident(scenario)
        await wait.edit_text(result[:4000])

    # ── Texnik tarjima ───────────────────────────────────────
    @dp.message(Command("tarjima"))
    @dp.message(Command("translate"))
    async def cmd_translate(msg: Message):
        """
        /tarjima [matn] — ingliz/rus → o'zbek
        /tarjima ru [matn] — ingliz → rus
        """
        if not is_owner(msg): return
        parts = msg.text.split(maxsplit=1)
        if len(parts) < 2:
            await msg.answer(
                "🌐 *Texnik tarjima*\n\n"
                "Format: `/tarjima <matn>`\n\n"
                "Misol:\n"
                "`/tarjima The pump shaft seal is worn`\n"
                "`/tarjima ru Replace the bearing assembly`\n\n"
                "_ABB, Metso, Warman, Sulzer hujjatlari uchun_"
            )
            return
        text = parts[1].strip()

        # Tilni aniqlash
        target = "uzbek"
        if text.lower().startswith("ru "):
            target = "russian"
            text   = text[3:].strip()

        # Ishlab chiqaruvchini aniqlash
        mfr = ""
        for brand in ["ABB", "Metso", "Warman", "Sulzer", "SKF", "Siemens", "Flender"]:
            if brand.lower() in text.lower():
                mfr = brand
                break

        wait   = await msg.answer("🌐 _Tarjima qilinmoqda..._")
        result = await mech.translate_technical(text, target_lang=target, manufacturer=mfr)
        await wait.edit_text(result[:4000])

    # ── Trend tahlili ────────────────────────────────────────
    @dp.message(Command("trend"))
    async def cmd_trend(msg: Message):
        """
        /trend nasos_1 vibration 2.1,2.4,2.8,3.1,3.5
        /trend tegirmon_1 temperature 65,68,71,74,78
        """
        if not is_owner(msg): return
        parts = msg.text.split()
        if len(parts) < 4:
            await msg.answer(
                "📊 *Trend tahlili*\n\n"
                "Format: `/trend <id> <parametr> <qiymatlar>`\n\n"
                "Misol:\n"
                "`/trend nasos_1 vibration 2.1,2.4,2.8,3.1,3.5`\n"
                "`/trend tegirmon temperature 65,68,71,74,78`\n"
                "`/trend kompressor pressure 6.5,6.3,6.0,5.8,5.5`\n\n"
                "_Parametrlar: vibration | temperature | pressure | current_"
            )
            return
        equip_id  = parts[1]
        param     = parts[2].lower()
        try:
            vals  = [float(x) for x in parts[3].split(",")]
            now_ts = datetime.now().timestamp()
            data   = [(now_ts - (len(vals)-i-1)*3600, v) for i, v in enumerate(vals)]
        except ValueError:
            await msg.answer("❌ Qiymatlar vergul bilan: `2.1,2.4,2.8`")
            return
        result = mech.analyze_trend(equip_id, param, data)
        await msg.answer(result)

    # ── Energiya monitoringi ─────────────────────────────────
    @dp.message(Command("energy"))
    async def cmd_energy(msg: Message):
        """
        /energy nasos_1 nasos 82.5
        /energy tegirmon_1 tegirmon 520 24
        """
        if not is_owner(msg): return
        parts = msg.text.split()
        if len(parts) < 4:
            await msg.answer(
                "⚡ *Energiya sarfi monitoringi*\n\n"
                "Format: `/energy <id> <tur> <kw> [soat]`\n\n"
                "Misol:\n"
                "`/energy nasos_1 nasos 82.5`\n"
                "`/energy tegirmon_1 tegirmon 520 8`\n"
                "`/energy kompressor_1 kompressor 58 24`"
            )
            return
        equip_id = parts[1]
        eq_type  = parts[2]
        try:
            kw      = float(parts[3])
            runtime = float(parts[4]) if len(parts) > 4 else 24
        except ValueError:
            await msg.answer("❌ kW qiymati son bo'lishi kerak")
            return
        result = mech.energy_monitor(equip_id, eq_type, kw, runtime)
        await msg.answer(result)

    # ── Samaradorlik metrikalari ─────────────────────────────
    @dp.message(Command("metrics"))
    async def cmd_metrics(msg: Message):
        if not is_owner(msg): return
        # DB dan statistika olish
        stats_raw = await db.get_weekly_stats()
        tasks_all = await db.get_tasks("done")
        tasks_pnd = await db.get_tasks("pending")
        incidents = await db.get_incidents(limit=50)

        # Nosozlik turlarini guruhlash
        failures: dict = {}
        for inc in incidents:
            t = inc.get("type", "Noma'lum")[:30]
            failures[t] = failures.get(t, 0) + 1

        stats = {
            "solved":           len(tasks_all),
            "total":            len(tasks_all) + len(tasks_pnd),
            "avg_response_min": 45,   # taxminiy — DB da yo'q
            "uptime_pct":       95.0, # taxminiy
            "failures":         failures,
        }
        result = mech.performance_metrics(stats)
        await msg.answer(result)

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
    #  AUTOLEARNER BUYRUQLARI
    # ════════════════════════════════════════════════════════

    @dp.message(Command("learn_sources"))
    async def cmd_learn_sources(msg: Message):
        if not is_owner(msg): return
        if not auto_learner:
            await msg.answer("❌ AutoLearner yuklanmagan.")
            return
        await msg.answer(await auto_learner.get_stats())

    @dp.message(Command("learn_sync"))
    async def cmd_learn_sync(msg: Message):
        if not is_owner(msg): return
        if not auto_learner:
            await msg.answer("❌ AutoLearner yuklanmagan.")
            return
        wait = await msg.answer("🔄 _Sinxronlanmoqda..._")
        res  = await auto_learner.sync_all(force=True)
        txt  = (
            f"✅ *AutoLearner natija:*\n\n"
            f"📦 Tekshirildi: {res['total']} ta\n"
            f"📄 Qo\'shildi: {res['added']} ta\n"
            f"❌ Xato: {res['errors']} ta"
        )
        if res["details"]:
            txt += "\n\n*Tafsilot:*"
            for d in res["details"]:
                icon = "✅" if d["ok"] else "❌"
                txt += f"\n{icon} {d['label']}: {d.get('added',0)} ta"
        await wait.edit_text(txt)

    # ════════════════════════════════════════════════════════
    #  MEDIA HANDLERLAR
    # ════════════════════════════════════════════════════════

    # ── Ovoz xabari buyruqlarini tasdiqlovchi yordamchi ──────
    def _voice_action_label(action: str, data: dict) -> tuple[str, str]:
        """
        Buyruq nomi va tavsifi. (emoji_label, tavsif)
        """
        labels = {
            "send_message":   ("💬 Xabar yuborish",
                               f"📤 {data.get('target','')} ga: «{data.get('content','')[:80]}»"),
            "voice_send":     ("🎤 Ovozli xabar",
                               f"📤 {data.get('target','')} ga ovozli: «{data.get('content','')[:80]}»"),
            "save_note":      ("💾 Zametka saqlash",
                               f"📝 «{data.get('content','')[:100]}»"),
            "add_task":       ("✅ Vazifa qo'shish",
                               f"📋 «{data.get('content','')[:80]}»" +
                               (f" | 📅 {data.get('deadline')}" if data.get('deadline') else "")),
            "done_task":      ("✔️ Vazifa yopish",
                               f"Vazifa #{data.get('task_id','')} bajarildi deb belgilanadi"),
            "weather":        ("🌤 Ob-havo",
                               f"📍 {data.get('city','Olmaliq')} ob-havosi ko'rsatiladi"),
            "currency":       ("💱 Valyuta kursi",     "Hozirgi kurs ko'rsatiladi"),
            "kb_search":      ("📚 Bilim bazasi",
                               f"🔍 «{data.get('query','')[:80]}» qidiriladi"),
            "equipment_info": ("🔧 Qurilma ma'lumoti",
                               f"📖 {data.get('equipment','')} haqida ma'lumot"),
            "safety_check":   ("🦺 Xavfsizlik",        "Xavfsizlik cheklisti ko'rsatiladi"),
            "incident":       ("🚨 Hodisa",             "Hodisa yo'riqnomasi ko'rsatiladi"),
            "hydraulic_calc": ("📐 Gidravlik hisob",   "Hisob bajariladi"),
            "pneumatic_calc": ("💨 Pnevmatik hisob",   "Hisob bajariladi"),
            "bearing_calc":   ("⚙️ Podshipnik resurs", "Hisob bajariladi"),
            "defect_act":     ("📄 Defekt akti",        "Hujjat yaratiladi"),
            "work_report":    ("📊 Ish hisoboti",       "Hujjat yaratiladi"),
            "service_letter": ("✉️ Xizmat xati",        "Hujjat yaratiladi"),
            "ppr_schedule":   ("🗓 PPR jadvali",        "Jadval yaratiladi"),
            "twin_update":    ("🤖 Digital Twin",
                               f"📡 {data.get('equipment_id','')} holati yangilanadi"),
            "twin_predict":   ("🔮 Prognoz",
                               f"📈 {data.get('equipment_id','')} uchun prognoz"),
            "twin_maintenance":("🛠 Ta'mirlash logi",  "Loga yoziladi"),
            "contacts":       ("👥 Kontaktlar",         "Kontaktlar ro'yxati ko'rsatiladi"),
            "report":         ("📈 Hisobot",            "Kunlik hisobot ko'rsatiladi"),
            "memory":         ("🧠 Xotira holati",      "Xotira statistikasi ko'rsatiladi"),
        }
        return labels.get(action, ("⚡ Buyruq", f"Amal: {action}"))

    # ── Ovozli xabar handler ──────────────────────────────────
    @dp.message(F.voice)
    async def handle_voice(msg: Message):
        if not is_owner(msg): return
        wait = await msg.answer("🎤 _Ovoz tahlil qilinmoqda..._")
        try:
            file  = await msg.bot.get_file(msg.voice.file_id)
            audio = (await msg.bot.download_file(file.file_path)).read()

            result = await ai.transcribe_voice(audio)
            if isinstance(result, tuple):
                text, should_save = result
            else:
                text, should_save = result, False

            if not text:
                await wait.edit_text("❌ Ovozni tushunib bo'lmadi.")
                return

            await db.save_message(msg.from_user.id, "in", text, "voice")

            # Buyruqni aniqlash
            action, data = quick_intent(text)
            if action is None:
                intent = await ai.detect_intent(text)
                action = intent.get("action", "chat")
                data   = intent

            # Saqlash so'zi bor — avtomatik saqlash
            if should_save:
                imp  = await ai.score_importance(text)
                perm = imp >= 0.6
                await db.add_note(text, is_pinned=perm)
                await db.save_memory(text, "voice_note", perm, imp)
                flag = " ⭐" if perm else ""
                await wait.edit_text(
                    f"🎤 *Eshitildi:*\n_{text}_\n\n💾 *Eslab qolindi!*{flag}"
                )
                return

            # Buyruq — tasdiq so'rash
            CONFIRM_ACTIONS = {
                "send_message", "voice_send", "add_task", "done_task",
                "save_note", "defect_act", "work_report", "service_letter",
                "ppr_schedule", "twin_update", "twin_maintenance",
                "learn_add", "learn_remove", "whitelist_add"
            }

            INFO_ACTIONS = {
                "weather", "currency", "kb_search", "equipment_info",
                "safety_check", "incident", "hydraulic_calc", "pneumatic_calc",
                "bearing_calc", "twin_predict", "contacts", "report", "memory",
                "get_tasks", "get_notes", "learn_sources"
            }

            if action in CONFIRM_ACTIONS:
                label, desc = _voice_action_label(action, data)
                # Xotirada saqlash, callback ga faqat qisqa uid
                uid = str(uuid.uuid4())[:8]
                _VOICE_CMD_STORE[uid] = {"action": action, "data": data, "text": text}
                confirm_kb = InlineKeyboardMarkup(inline_keyboard=[[
                    InlineKeyboardButton(text="✅ Bajar",      callback_data=f"vcmd_yes|{uid}"),
                    InlineKeyboardButton(text="❌ Kerak emas", callback_data=f"vcmd_no|{uid}")
                ]])
                await wait.edit_text(
                    f"🎤 *Eshitildi:*\n_{text}_\n\n"
                    f"🔍 *Buyruq:* {label}\n"
                    f"📋 {desc}\n\n"
                    f"_Bajarayinmi?_",
                    reply_markup=confirm_kb
                )

            elif action in INFO_ACTIONS or action == "chat":
                # Ma'lumot so'rov — tasdiqlashsiz bajar
                await wait.edit_text(f"🎤 *Eshitildi:*\n_{text}_\n\n⏳ _Ishlanmoqda..._")
                resp = await process_text(
                    text, db, ai, userbot, owner_id, tts, mech, vis, kb, digit_twin, personal_twin
                )
                await wait.edit_text(f"🎤 *Eshitildi:*\n_{text}_")
                await msg.answer(resp)

            else:
                # Noma'lum — inline keyboard bilan so'ra
                save_kb = InlineKeyboardMarkup(inline_keyboard=[[
                    InlineKeyboardButton(
                        text="💾 Eslab qol",
                        callback_data=f"voice_save|{text[:200]}"
                    ),
                    InlineKeyboardButton(
                        text="✖️ Kerak emas",
                        callback_data="voice_skip"
                    )
                ]])
                await wait.edit_text(
                    f"🎤 *Eshitildi:*\n_{text}_",
                    reply_markup=save_kb
                )

        except Exception as e:
            log.error(f"Voice handler xatosi: {e}")
            await wait.edit_text(f"❌ Xatolik: {e}")

    # ── Buyruq tasdiqlandi ────────────────────────────────────
    @dp.callback_query(F.data.startswith("vcmd_yes|"))
    async def cb_voice_confirm(call: CallbackQuery):
        await call.answer("✅ Bajarilmoqda...")
        try:
            uid     = call.data.split("|", 1)[1]
            payload = _VOICE_CMD_STORE.pop(uid, None)
            if not payload:
                await call.message.answer("❌ Buyruq muddati o'tdi, qayta yuboring.")
                return
            text = payload.get("text", "")
            resp = await process_text(
                text, db, ai, userbot, owner_id, tts, mech, vis, kb, digit_twin, personal_twin
            )
            # Tugmalarni o'chir
            orig = call.message.text or ""
            await call.message.edit_text(
                orig.split("\n\n_Bajarayinmi?_")[0] + "\n\n✅ *Bajarildi!*"
            )
            await call.message.answer(resp)
        except Exception as e:
            await call.message.answer(f"❌ Xatolik: {e}")

    @dp.callback_query(F.data.startswith("vcmd_no|"))
    async def cb_voice_cancel(call: CallbackQuery):
        uid = call.data.split("|", 1)[1]
        _VOICE_CMD_STORE.pop(uid, None)
        await call.answer("❌ Bekor qilindi")
        orig = call.message.text or ""
        await call.message.edit_text(
            orig.split("\n\n🔍")[0] + "\n\n_❌ Bekor qilindi_"
        )

    # ── Ovoz — eslab qolish callbacklari ─────────────────────
    @dp.callback_query(F.data.startswith("voice_save|"))
    async def cb_voice_save(call: CallbackQuery):
        content = call.data.split("|", 1)[1]
        imp  = await ai.score_importance(content)
        perm = imp >= 0.6
        await db.add_note(content, is_pinned=perm)
        await db.save_memory(content, "voice_note", perm, imp)
        flag = " ⭐" if perm else ""
        await call.message.edit_text(
            f"💾 *Eslab qolindi!*{flag}\n\n_{content}_"
        )
        await call.answer("✅ Saqlandi!")

    @dp.callback_query(F.data == "voice_skip")
    async def cb_voice_skip(call: CallbackQuery):
        await call.message.edit_reply_markup(reply_markup=None)
        await call.answer("✖️ O'tkazib yuborildi")

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

    # Vazifa — vaqt va sana formatlarini to'liq qo'llab-quvvatlash
    m = re.match(r'^(?:vazifa|topshiriq|todo|task)[:\s]+(.+)', t, re.I)
    if m:
        content = m.group(1).strip()
        due     = None
        # Vergul orqali ajratilgan muddat: "vazifa: ish, soat 14:30"
        dm = re.search(
            r',\s*(?:muddat|soat|ertaga|\d{1,2}[.:]\d{2}|'
            r'\d{1,2}\.\d{1,2}\.?\d*|'
            r'\d+\s*(?:soat|daqiqa))',
            content, re.I
        )
        if dm:
            due     = content[dm.start() + 1:].strip()  # verguldan keyingi qism
            content = content[:dm.start()].strip()
        return ("add_task", {"content": content, "deadline": due})

    # Vazifa bajarildi
    m = re.search(r'vazifa\s+(\d+)\s+bajarildi', tl)
    if m: return ("done_task", {"task_id": m.group(1)})

    # Zayavka / ariza
    m = re.match(r'^(?:zayavka|ariza|buyurtma|kerak)[:\s]+(.+)', tl)
    if m: return ("zayavka", {"desc": m.group(1).strip()})

    # Ehtiyot qismlar
    m = re.match(r'^(?:ehtiyot|spare|resurs)[:\s]+(\w+)\s+([\d.]+)', tl)
    if m: return ("spare_parts", {"equip": m.group(1), "runtime": float(m.group(2))})

    # Avariya simulyatori
    m = re.match(r'^(?:agar|avaria|stsenariy)[:\s]+(.+)', tl)
    if m: return ("avaria", {"scenario": m.group(1).strip()})

    # Texnik tarjima
    m = re.match(r'^(?:tarjima|translate)[:\s]+(.+)', tl)
    if m: return ("translate", {"text": m.group(1).strip()})

    # Trend
    m = re.match(r'^trend[:\s]+(\w+)\s+(\w+)\s+([\d.,]+)', tl)
    if m: return ("trend", {"equip": m.group(1), "param": m.group(2), "vals": m.group(3)})

    # Energiya
    m = re.match(r'^(?:energiya|energy|quvvat)[:\s]+(\w+)\s+([\d.]+)', tl)
    if m: return ("energy", {"equip": m.group(1), "kw": float(m.group(2))})

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

    # ── Kod va texnologiya so'rovlari (CHAT ga yo'naltirilsin) ──
    # Bu blok boshqa intent'lardan OLDIN tekshiriladi
    code_keywords = [
        'kod', 'code', 'python', 'javascript', 'js', 'typescript', 'sql',
        'bash', 'script', 'funksiya', 'function', 'class', 'import',
        'xato', 'error', 'exception', 'bug', 'debug', 'tuzat', 'fix',
        'api', 'bot', 'telegram', 'aiogram', 'django', 'fastapi',
        'docker', 'git', 'railway', 'deploy', 'server', 'linux',
        'database', 'db', 'query', 'select', 'insert', 'update',
        'loop', 'sikl', 'array', 'list', 'dict', 'json', 'async',
        'install', 'pip', 'npm', 'requirements', 'library', 'kutubxona',
        'qanday yoziladi', 'qanday ishlaydi', 'misol', 'namuna', 'yoz',
        'ko\'rsatma', 'tushuntir', 'nima bu', 'nima uchun',
    ]
    if any(kw in tl for kw in code_keywords):
        return (None, {})   # AI chat ga o'tkazilsin

    # Qurilma muammolari — FAQAT aniq sanoat uskunalari uchun
    problem_words = ['ishlamay','nosoz','buzil','toxta','vibrats','sizib','tiqil']
    if any(pw in tl for pw in problem_words):
        for eq in ['nasos','kompressor','konveyer','tegirmon','flotatsiya']:
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

    # AutoLearner — manba qo'shish
    m = re.match(r'^manba\s+qosh[\s:]+([a-z]+)\s+(https?://\S+)(?:\s+(\S+))?', tl)
    if m:
        return ("learn_add", {"type": m.group(1), "url": m.group(2),
                               "category": m.group(3) or "auto"})

    # AutoLearner — manba o'chirish
    m = re.match(r'^manba\s+(?:ochir|del|remove)[\s:]+(\d+)', tl)
    if m:
        return ("learn_remove", {"source_id": int(m.group(1))})

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
        target      = data.get("target") or data.get("to") or ""
        content_msg = data.get("content") or data.get("message") or ""
        # target aniq ism bo'lmasa — oddiy AI suhbat
        if str(target).lower() in ("null", "none", "", "0", "unknown", "noma'lum") or not target:
            memories = await db.get_relevant_memories(text)
            context  = "\n".join(f"• {m}" for m in memories) if memories else ""
            history  = await db.get_conversation_history()
            return await ai.chat(text, history, context)
        if not content_msg:
            return "❓ Nima yozishni aytmadingiz. Format:\n`Azizga yoz: ertaga uchrashemiz`"
        return await action_send_message(target, content_msg, userbot)

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
    elif action == "zayavka":
        desc = data.get("desc", text)
        eq_m = re.search(r'(nasos|kompressor|tegirmon|konveyer|flotatsiya|warman)', desc, re.I)
        eq   = eq_m.group(1) if eq_m else ""
        return mech.generate_zayavka(desc, equip_name=eq)

    elif action == "spare_parts":
        return mech.spare_parts_calc(
            data.get("equip", "nasos"),
            float(data.get("runtime", 0)),
            data.get("intensity", "o'rtacha")
        )

    elif action == "avaria":
        return await mech.simulate_accident(data.get("scenario", text))

    elif action == "translate":
        return await mech.translate_technical(data.get("text", text))

    elif action == "trend":
        try:
            vals  = [float(x) for x in data.get("vals", "").split(",")]
            now_ts = datetime.now().timestamp()
            points = [(now_ts - (len(vals)-i-1)*3600, v) for i, v in enumerate(vals)]
            return mech.analyze_trend(data.get("equip", ""), data.get("param", "vibration"), points)
        except Exception as e:
            return f"❌ Trend xatosi: {e}"

    elif action == "energy":
        return mech.energy_monitor(
            data.get("equip", ""), data.get("equip", "nasos"),
            float(data.get("kw", 0))
        )

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

    elif action == "learn_add":
        if not auto_learner:
            return "❌ AutoLearner yuklanmagan."
        res = await auto_learner.add_source(
            data.get("type","web"), data.get("url",""), data.get("category","auto")
        )
        if res["ok"]:
            return (f"✅ *Manba qo\'shildi!*\n\n"
                    f"🔗 {res['type'].upper()}: {res['url']}\n"
                    f"📂 Kategoriya: {res['category']}\n\n"
                    f"`/learn_sync` — hozir sinxronlash")
        return f"❌ Xato: {res['error']}"

    elif action == "learn_remove":
        if not auto_learner:
            return "❌ AutoLearner yuklanmagan."
        sid = data.get("source_id")
        if sid:
            await auto_learner.remove_source(sid)
            return f"✅ Manba #{sid} o\'chirildi."
        return "❓ Manba ID kerak."

    elif action == "learn_sync":
        if not auto_learner:
            return "❌ AutoLearner yuklanmagan."
        res = await auto_learner.sync_all(force=True)
        return (f"✅ Sinxronlandi: {res['added']} ta qo\'shildi, "
                f"{res['errors']} ta xato.")

    elif action == "ppr_schedule":
        return await mech.generate_ppr_schedule(data.get("equipment",["nasos"]))

    else:
        # ════════════════════════════════════════════════════
        #  YANGI AQLLI JAVOB TIZIMI v2.0
        #  1. Xotira + tarix olish
        #  2. Semantic RAG — vector qidiruv (FTS + TF-IDF)
        #  3. Prompt Chaining — 3 bosqich (intent→javob→filtr)
        #  4. PersonalTwin fallback
        # ════════════════════════════════════════════════════

        # ── 1. Kontekst yig'ish ──────────────────────────────
        memories = await db.get_relevant_memories(text)
        mem_ctx  = "\n".join(f"• {m}" for m in memories) if memories else ""
        history  = await db.get_conversation_history()

        # ── 2. Semantic RAG — parallel qidiruv ───────────────
        #  a) FTS5 (an'anaviy) + b) Semantic vector
        combined_context = mem_ctx

        # a) FTS qidiruv (KB.get_rag_context — tezkor)
        fts_ctx = await kb.get_rag_context(text)

        # b) Semantic vector qidiruv (AIServices.semantic_rag)
        #    KB docs ni bir marta yuklash (lazy init)
        try:
            from knowledge_base import MBF3_KNOWLEDGE
            sem_ctx = await ai.semantic_search(text, MBF3_KNOWLEDGE)
        except Exception as _rag_err:
            log.warning(f"Semantic RAG xatosi: {_rag_err}")
            sem_ctx = ""

        # Ikki RAG natijasini birlashtirish (duplicate bo'lmaslik uchun)
        rag_parts = []
        if fts_ctx:
            rag_parts.append(fts_ctx)
        if sem_ctx and sem_ctx not in fts_ctx:
            rag_parts.append(sem_ctx)

        if rag_parts:
            rag_block = "\n\n---\n\n".join(rag_parts)
            combined_context = (
                (mem_ctx + "\n\n" if mem_ctx else "") +
                "📚 Texnik bilim bazasi:\n" + rag_block
            )

        # ── 3. Prompt Chaining — 3 bosqich ───────────────────
        try:
            # chat_v2 ichida: intent → generate → filter
            answer = await ai.chat_v2(text, history, combined_context)
            if answer and len(answer) > 3:
                return answer
        except Exception as _chain_err:
            log.warning(f"Prompt chain xatosi: {_chain_err}")
            # Xato bo'lsa oddiy chat ga tushish
            answer = await ai.chat(text, history, combined_context)
            if answer:
                return answer

        # ── 4. PersonalTwin fallback ─────────────────────────
        if personal_twin:
            try:
                stats = await personal_twin.get_stats()
                if stats.get("ready", False):
                    reply = await personal_twin.generate_reply(text, "")
                    if reply and len(reply) > 5:
                        return reply
            except Exception as _pt_err:
                log.warning(f"PersonalTwin xatosi: {_pt_err}")

        # ── 5. So'nggi fallback ──────────────────────────────
        return await ai.chat(text, history, mem_ctx)


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
    # null, none, yoki bo'sh target bo'lsa yuborma
    if not target or not content:
        return "❓ Format:\n`Azizga yoz: ertaga uchrashemiz`"
    if str(target).lower() in ("null", "none", "", "unknown"):
        return "❓ Kimga yozish kerak? Format:\n`Azizga yoz: ertaga uchrashemiz`"
    if len(str(target)) < 2:
        return "❓ Ism juda qisqa. Format:\n`Azizga yoz: ertaga uchrashemiz`"
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
    """
    Vazifa qo'shish. Vaqt formatlari:
      "soat 14:30"          → bugun 14:30 Toshkent
      "ertaga 09:00"        → ertaga 09:00
      "25.07.2025 14:30"    → aniq sana va vaqt
      "25.07.2025"          → faqat sana (00:00)
      "muddat 3 soat"       → 3 soatdan keyin
    """
    from zoneinfo import ZoneInfo
    from datetime import datetime, timedelta, timezone
    TZ = ZoneInfo("Asia/Tashkent")

    title = data.get("content", "")
    raw   = data.get("deadline", "") or ""
    due_dt = None

    if raw:
        now = datetime.now(TZ)
        r   = raw.strip().lower()

        # "soat 14:30" yoki "14:30"
        m = re.search(r'(?:soat\s+)?(\d{1,2}):(\d{2})', r)
        if m:
            h, mn = int(m.group(1)), int(m.group(2))
            due_dt = now.replace(hour=h, minute=mn, second=0, microsecond=0)
            if due_dt < now:   # o'tib ketgan bo'lsa — ertaga
                due_dt += timedelta(days=1)

        # "ertaga 09:00"
        elif r.startswith("ertaga"):
            tm = re.search(r'(\d{1,2}):(\d{2})', r)
            base = now + timedelta(days=1)
            if tm:
                due_dt = base.replace(hour=int(tm.group(1)), minute=int(tm.group(2)),
                                      second=0, microsecond=0)
            else:
                due_dt = base.replace(hour=9, minute=0, second=0, microsecond=0)

        # "25.07.2025 14:30" yoki "25.07 14:30"
        elif re.match(r'\d{1,2}\.\d{1,2}', r):
            for fmt in ("%d.%m.%Y %H:%M", "%d.%m.%Y", "%d.%m %H:%M", "%d.%m"):
                try:
                    parsed = datetime.strptime(raw.strip()[:16], fmt)
                    if "%Y" not in fmt:
                        parsed = parsed.replace(year=now.year)
                    due_dt = parsed.replace(tzinfo=TZ)
                    break
                except ValueError:
                    continue

        # "3 soatdan keyin" / "muddat 3 soat"
        elif m2 := re.search(r'(\d+)\s*soat', r):
            due_dt = now + timedelta(hours=int(m2.group(1)))

        # "30 daqiqadan keyin"
        elif m2 := re.search(r'(\d+)\s*daqiqa', r):
            due_dt = now + timedelta(minutes=int(m2.group(1)))

    due_str = due_dt.strftime("%Y-%m-%d %H:%M") if due_dt else None
    tid     = await db.add_task(title, title, due_str)

    if due_str and due_dt:
        from zoneinfo import ZoneInfo
        TZ2 = ZoneInfo("Asia/Tashkent")
        fmt_show = due_dt.strftime("%d.%m.%Y %H:%M")
        return (
            f"✅ *Vazifa #{tid} qo'shildi!*\n\n"
            f"📋 {title}\n"
            f"⏰ _{fmt_show} (Toshkent)_\n\n"
            f"_Eslatma vaqti kelganda avtomatik yuboriladi_"
        )
    return f"✅ *Vazifa #{tid} qo'shildi:*\n📋 {title}"


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
    from zoneinfo import ZoneInfo
    from datetime import datetime
    TZ = ZoneInfo("Asia/Tashkent")

    tasks = await db.get_tasks()
    if not tasks:
        return (
            "✅ *Faol vazifalar yo'q.*\n\n"
            "_Vazifa qo'shish:_\n"
            "`Vazifa: sarlavha, soat 14:30`\n"
            "`Vazifa: sarlavha, 25.07.2025 09:00`"
        )

    now = datetime.now(TZ)
    lines = ["📋 *Vazifalar:*\n"]

    for i, t in enumerate(tasks, 1):
        due_str = t.get("due", "")
        if due_str:
            try:
                fmt = "%Y-%m-%d %H:%M:%S" if len(due_str) > 16 else "%Y-%m-%d %H:%M"
                due_dt = datetime.strptime(due_str[:19], fmt).replace(tzinfo=TZ)
                diff   = (due_dt - now).total_seconds() / 60

                # Vaqt formati
                if due_dt.date() == now.date():
                    time_label = f"bugun {due_dt.strftime('%H:%M')}"
                elif due_dt.date().toordinal() - now.date().toordinal() == 1:
                    time_label = f"ertaga {due_dt.strftime('%H:%M')}"
                else:
                    time_label = due_dt.strftime("%d.%m %H:%M")

                # Holat belgisi
                if diff < 0:
                    badge = "🔴"   # o'tib ketgan
                elif diff <= 60:
                    badge = "🟠"   # 1 soat qoldi
                elif diff <= 1440:
                    badge = "🟡"   # 1 kun qoldi
                else:
                    badge = "⚪"   # uzoq

                due_display = f" {badge} _{time_label}_"
            except ValueError:
                due_display = f" — _{due_str[:10]}_"
        else:
            due_display = ""

        lines.append(f"{i}. {t['title']}{due_display}")

    lines.append(
        "\n_Bajarildi:_ `Vazifa <N> bajarildi`\n"
        "_Yangi:_ `Vazifa: sarlavha, soat 15:00`"
    )
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
