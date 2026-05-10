"""
Handlers v4.0 — O'tkirbek AI Agent
Barcha funksiyalar: Vizual Defektoskopiya, HSE Audit, Sensor Tahlili,
Digital Twin, Knowledge Base RAG, AutoPilot, AutoReply boshqaruvi,
Smena topshirish, PTW, Incident Logger, Eslatmalar
"""

import os
import re
import logging
import asyncio
import aiohttp
import tempfile
from datetime import datetime, timedelta
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
from analytics_service import AnalyticsService
from briefing_service import BriefingService
from spare_parts_service import SparePartsService
from shift_handover import ShiftHandover
from group_notifier import GroupNotifier
from ptw_assistant import PTWAssistant
from incident_logger import IncidentLogger

log = logging.getLogger(__name__)
OWNER_NAME = os.getenv("OWNER_NAME", "O'tkirbek")
GROUP_CHAT_ID = os.getenv("GROUP_CHAT_ID", "")


def register_handlers(dp: Dispatcher, db: Database, ai: AIServices,
                      userbot: UserBot, owner_id: int, twin=None):
    """Barcha handlerlarni ro'yxatdan o'tkazish"""

    # ── Servislarni ishga tushirish ───────────────────────────────
    tts = TTSService()
    mech = MechanicService()
    vis = VisionService()
    kb = KnowledgeBase()
    digit_twin = DigitalTwin()
    analytics = AnalyticsService()
    briefing = BriefingService()
    spare_parts = SparePartsService()
    shift_handover = ShiftHandover()
    group_notifier = GroupNotifier()
    ptw_assistant = PTWAssistant()
    incident_logger = IncidentLogger()

    # PersonalTwin — Raqamli Egizak
    personal_twin = twin
    if personal_twin is None:
        try:
            from personal_twin import PersonalTwin as PT
            personal_twin = PT()
        except ImportError:
            personal_twin = None

    # ── Servislarni init qilish ─────────────────────────────────
    async def _init_services():
        await kb.init()
        await digit_twin.init()
        await group_notifier.init_db()
        await ptw_assistant.init_db()
        await incident_logger.init_db()
        if personal_twin:
            await personal_twin.init_db()

    try:
        loop = asyncio.get_event_loop()
        if loop.is_running():
            loop.create_task(_init_services())
        else:
            loop.run_until_complete(_init_services())
    except Exception as e:
        log.warning(f"Init xatosi: {e}")

    def is_owner(msg: Message) -> bool:
        return msg.from_user.id == owner_id

    # ════════════════════════════════════════════════════════════
    #  ASOSIY BUYRUQLAR
    # ════════════════════════════════════════════════════════════

    @dp.message(Command("start"))
    async def cmd_start(msg: Message):
        if not is_owner(msg): return
        await msg.answer(
            f"👋 *Salom, {OWNER_NAME}! Men sizning Raqamli Egizagingizman.*\n\n"
            f"🏭 _AGMK 3-mis boyitish fabrika mexanigi uchun_\n\n"
            f"🧠 *AI Stack:* Groq Llama3 + OpenRouter + ElevenLabs\n\n"
            f"*Nima qila olaman:*\n"
            f"🔬 Uskunadagi nosozliklarni rasmdan aniqlash\n"
            f"🦺 HSE auditi — PPE bor-yo'qligini tekshirish\n"
            f"📊 Sensor ma'lumotlarini tahlil + prognoz\n"
            f"📐 Chertyo'j o'qish (GOST, o'lchamlar, materiallar)\n"
            f"📚 MBF-3 bilim bazasi (Warman, GMD/ABB, flotatsiya)\n"
            f"🤖 AutoPilot — sizning nomingizdan suhbat\n"
            f"📈 Digital Twin — uskunalar holati dashboard\n"
            f"🎤 Ovozli xabar (ElevenLabs TTS)\n"
            f"📋 Smena topshirish protokoli\n"
            f"🦺 Permit-to-Work (PTW) yordamchi\n"
            f"🔒 LOTO protseduralari\n"
            f"📝 Hodisalar jurnali\n"
            f"⏰ Eslatmalar va xotira\n\n"
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
            "📊 *ANALITIKA:*\n"
            "`/trend nasos_1 vibration` — trend tahlili\n"
            "`/predict nasos_1` — ishdan chiqish ehtimoli\n"
            "`/stats 7` — ish samaradorligi statistikasi\n"
            "`/energy nasos_1 85` — energiya monitoringi\n\n"
            "📋 *SMENA TOPSHIRISH:*\n"
            "`/handover_start` — smena topshirishni boshlash\n"
            "`/handover_history` — topshirish tarixi\n\n"
            "🦺 *PTW va XAVFSIZLIK:*\n"
            "`/ptw_start elektr 2-qavat` — PTW boshlash\n"
            "`/loto` — LOTO protsedurasi\n"
            "`/loto checklist` — LOTO checklist\n\n"
            "📝 *HODISALAR:*\n"
            "`/incident nasos PP-612 to'xtadi` — hodisa qayd qilish\n"
            "`/incidents` — hodisalar ro'yxati\n"
            "`/incidents stats` — statistika\n"
            "`/incident_action 123 Chora matni` — chora qo'shish\n\n"
            "⏰ *ESLATMALAR:*\n"
            "`/reminder 21:00 da nasosni tekshir` — eslatma qo'shish\n"
            "`/daily_events` — kunlik voqealar hisoboti\n\n"
            "🔧 *EHTIYOT QISMLAR:*\n"
            "`/part podshipnik_6310 16` — resurs hisobi\n"
            "`/request nasos salnik 3` — ariza generatori\n\n"
            "🌅 *KUNLIK BRIEFING:*\n"
            "`/briefing` — kunlik hisobot\n"
            "`/briefing -v` — ovozli hisobot\n\n"
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
            "📋 *HUJJATLAR:*\n"
            "`Defekt akti:` / `Ish hisoboti:` / `PPR jadvali:`\n\n"
            "🎤 *OVOZLI XABAR:*\n"
            "`Azizga ovozli yoz: 15 daqiqa kechikaman`"
        )

    # ════════════════════════════════════════════════════════════
    #  DIGITAL TWIN BUYRUQLARI
    # ════════════════════════════════════════════════════════════

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

    # ════════════════════════════════════════════════════════════
    #  ANALITIKA BUYRUQLARI
    # ════════════════════════════════════════════════════════════

    @dp.message(Command("trend"))
    async def cmd_trend(msg: Message):
        if not is_owner(msg): return
        args = msg.text.split()
        if len(args) < 3:
            await msg.answer(
                "📈 *Trend tahlili*\n\n"
                "Ishlatish:\n"
                "`/trend nasos_1 vibration`\n"
                "`/trend tegirmon_1 temperature`\n"
                "`/trend kompressor_1 pressure`"
            )
            return
        equipment = args[1]
        sensor_type = args[2]
        wait = await msg.answer(f"📊 _Trend tahlili: {equipment} - {sensor_type}_")
        result = await analytics.get_sensor_trend(equipment, sensor_type)
        if "error" in result:
            await wait.edit_text(f"❌ {result['error']}")
        else:
            response = (
                f"📈 *Trend Tahlili*\n"
                f"⚙️ {equipment}\n"
                f"📊 Parametr: {sensor_type}\n\n"
                f"📉 Trend: {result['trend']}\n"
                f"📐 Nishablik: {result['slope']}\n"
                f"💎 Oxirgi qiymat: {result['last_value']}\n"
                f"🔄 O'zgarish: {result['change_rate']}%\n\n"
                f"💡 {result['advice']}"
            )
            await wait.edit_text(response)

    @dp.message(Command("predict"))
    async def cmd_predict(msg: Message):
        if not is_owner(msg): return
        args = msg.text.split()
        if len(args) < 2:
            await msg.answer("Ishlatish: `/predict nasos_1`")
            return
        equipment = args[1]
        wait = await msg.answer(f"🔮 _Prognoz: {equipment}_")
        result = await analytics.predict_failure_probability(equipment)
        response = f"🔮 *Ishdan chiqish ehtimoli — {equipment}*\n\n"
        response += f"🎲 Ehtimol: {result['probability']}\n"
        if result['estimated_days']:
            response += f"⏱ Taxminiy muddat: {result['estimated_days']} kun\n"
        response += f"\n💡 {result['advice']}"
        if result['critical_params']:
            response += f"\n\n⚠️ *Kritik parametrlar:*\n"
            for p in result['critical_params']:
                response += f"  • {p}\n"
        await wait.edit_text(response)

    @dp.message(Command("stats"))
    async def cmd_stats(msg: Message):
        if not is_owner(msg): return
        args = msg.text.split()
        days = int(args[1]) if len(args) > 1 and args[1].isdigit() else 7
        wait = await msg.answer(f"📊 _Statistika yig'ilmoqda ({days} kun)..._")
        metrics = await analytics.get_performance_metrics(days)
        response = (
            f"📊 *Ish Samaradorligi — {days} kun*\n\n"
            f"📨 Jami muammolar: {metrics['total_issues']}\n"
            f"✅ Hal qilingan: {metrics['solved']}\n"
            f"📈 Yechim darajasi: {metrics['resolution_rate']}%\n\n"
            f"🔝 *Eng ko'p uchraydigan:*\n"
        )
        for p in metrics['top_problems'][:5]:
            response += f"  • {p['problem']}: {p['count']} marta\n"
        await wait.edit_text(response)

    @dp.message(Command("energy"))
    async def cmd_energy(msg: Message):
        if not is_owner(msg): return
        args = msg.text.split()
        if len(args) < 3:
            await msg.answer("Ishlatish: `/energy nasos_1 85` (85 kW joriy quvvat)")
            return
        equipment = args[1]
        current_power = float(args[2])
        result = await analytics.get_energy_anomaly(equipment, current_power)
        response = (
            f"⚡ *Energiya sarfi tahlili*\n"
            f"⚙️ {equipment}\n\n"
            f"📊 Joriy quvvat: {result['current_kw']} kW\n"
            f"📋 Nominal: {result['nominal_kw']} kW\n"
            f"📉 Normadan: {result['deviation_percent']}%\n"
            f"🚦 Holat: {result['anomaly']}\n\n"
            f"💡 {result['advice']}"
        )
        await msg.answer(response)

    # ════════════════════════════════════════════════════════════
    #  EHTIYOT QISMLAR
    # ════════════════════════════════════════════════════════════

    @dp.message(Command("part"))
    async def cmd_part(msg: Message):
        if not is_owner(msg): return
        args = msg.text.split()
        if len(args) < 2:
            await msg.answer(
                "🔧 *Ehtiyot qismlar kalkulyatori*\n\n"
                "Ishlatish:\n"
                "`/part podshipnik_6310 16` — 16 soat/sutka bilan hisoblash\n"
                "`/part muhr_nasos` — faqat ma'lumot\n\n"
                "Mavjud qismlar:\n"
                "• podshipnik_6310, podshipnik_6312\n"
                "• salnik_45x62x8, muhr_nasos\n"
                "• lenta_konveyer, rolik_konveyer\n"
                "• filtr_hp, liner_tegirmon"
            )
            return
        part_name = args[1]
        daily_hours = float(args[2]) if len(args) > 2 and args[2].replace('.', '').isdigit() else 0
        result = spare_parts.calculate_remaining_life(part_name, daily_hours, 0)
        if not result["found"]:
            await msg.answer(f"❌ {result['message']}")
            return
        response = (
            f"🔧 *Ehtiyot qism resursi*\n\n"
            f"📦 Nomi: {result['part_name']}\n"
            f"🔢 Kodi: {result['part_code']}\n"
            f"⏱ Umumiy resurs: {result['total_life_hours']} soat\n"
            f"📊 Qolgan: {result['remaining_hours']} soat\n"
        )
        if result['remaining_days']:
            response += f"📅 Kunlarda: ~{result['remaining_days']} kun\n"
        response += f"\n⚡ Holat: {result['status']}\n"
        response += f"💡 {result['advice']}"
        await msg.answer(response)

    @dp.message(Command("request"))
    async def cmd_request(msg: Message):
        if not is_owner(msg): return
        args = msg.text.split()
        if len(args) < 4:
            await msg.answer(
                "📋 *Ariza generatori*\n\n"
                "Ishlatish:\n"
                "`/request nasos_1 podshipnik_6310 2`\n"
                "Ariza avtomatik tayyorlanadi"
            )
            return
        equipment = args[1]
        part_name = args[2]
        quantity = int(args[3])
        reason = " ".join(args[4:]) if len(args) > 4 else ""
        request_text = spare_parts.generate_request(equipment, part_name, quantity, reason)
        await msg.answer(request_text)

    # ════════════════════════════════════════════════════════════
    #  KUNLIK BRIEFING
    # ════════════════════════════════════════════════════════════

    @dp.message(Command("briefing"))
    async def cmd_briefing(msg: Message):
        if not is_owner(msg): return
        args = msg.text.split()
        as_voice = "-v" in args or "--voice" in args
        wait = await msg.answer("📊 _Briefing tayyorlanmoqda..._")
        if as_voice:
            audio = await briefing.generate_audio_briefing()
            if audio:
                await wait.delete()
                await msg.answer_voice(BufferedInputFile(audio, filename="briefing.mp3"))
            else:
                text = await briefing.generate_daily_briefing()
                await wait.edit_text(text)
        else:
            text = await briefing.generate_daily_briefing()
            await wait.edit_text(text)

    # ════════════════════════════════════════════════════════════
    #  SMENA TOPSHIRISH
    # ════════════════════════════════════════════════════════════

    @dp.message(Command("handover_start"))
    async def cmd_handover_start(msg: Message):
        if not is_owner(msg): return
        response = await shift_handover.start_handover(msg.from_user.id, msg.chat.id)
        await msg.answer(response)

    @dp.message(Command("handover_history"))
    async def cmd_handover_history(msg: Message):
        if not is_owner(msg): return
        history = await shift_handover.get_handover_history()
        await msg.answer(history)

    # ════════════════════════════════════════════════════════════
    #  PTW VA LOTO
    # ════════════════════════════════════════════════════════════

    @dp.message(Command("ptw_start"))
    async def cmd_ptw_start(msg: Message):
        if not is_owner(msg): return
        args = msg.text.split()
        if len(args) < 2:
            work_types = ptw_assistant.get_work_types()
            types_list = "\n".join([f"  • {k} — {v}" for k, v in work_types.items()])
            await msg.answer(
                f"🦺 *Permit-to-Work tizimi*\n\n"
                f"Ishlatish: `/ptw_start <tur> [joy]`\n\n"
                f"Mavjud turlar:\n{types_list}\n\n"
                f"Masalan: `/ptw_start elektr 2-qavat`"
            )
            return
        work_type = args[1]
        location = " ".join(args[2:]) if len(args) > 2 else ""
        result = ptw_assistant.start_permit(msg.from_user.id, work_type, location)
        if "error" in result:
            await msg.answer(f"❌ {result['error']}")
        else:
            await msg.answer(result["message"])
            await msg.answer(f"✅ *Savol 1/{len(ptw_assistant.WORK_TYPES[work_type]['checklist'])}:*\n{result['first_question']}")

    @dp.message(Command("ptw_answer"))
    async def cmd_ptw_answer(msg: Message):
        if not is_owner(msg): return
        answer = msg.text.replace("/ptw_answer", "").strip()
        if not answer:
            await msg.answer("Javobingizni yozing: ✅ yoki ❌")
            return
        result = ptw_assistant.process_answer(msg.from_user.id, answer)
        await msg.answer(result["message"])

    @dp.message(Command("loto"))
    async def cmd_loto(msg: Message):
        if not is_owner(msg): return
        args = msg.text.split()
        if len(args) > 1 and args[1] == "checklist":
            response = ptw_assistant.get_loto_checklist()
        else:
            response = ptw_assistant.get_loto_steps()
        await msg.answer(response)

    # ════════════════════════════════════════════════════════════
    #  HODISALAR JURNALI
    # ════════════════════════════════════════════════════════════

    @dp.message(Command("incident"))
    async def cmd_incident(msg: Message):
        if not is_owner(msg): return
        text = msg.text.replace("/incident", "").strip()
        if not text:
            await msg.answer(
                "📋 *Hodisa qayd qilish*\n\n"
                "Ishlatish: `/incident nasos PP-612 to'xtadi, vibratsiya yuqori`\n\n"
                "Hodisa avtomatik tahlil qilinadi va jurnalga yoziladi."
            )
            return
        result = await incident_logger.log_incident(text, msg.from_user.first_name)
        await msg.answer(result["message"])

    @dp.message(Command("incidents"))
    async def cmd_incidents(msg: Message):
        if not is_owner(msg): return
        args = msg.text.split()
        if len(args) > 1 and args[1] == "stats":
            stats = await incident_logger.get_incident_stats()
            response = (
                f"📊 *Hodisalar statistikasi (30 kun)*\n\n"
                f"📋 Jami: {stats['total']}\n\n"
                f"📌 *Turlar bo'yicha:*\n"
            )
            for t, c in stats['by_type'].items():
                response += f"  • {t}: {c}\n"
            response += f"\n🚨 *Og'irlik bo'yicha:*\n"
            for s, c in stats['by_severity'].items():
                emoji = "🔴" if s == "critical" else "🟡" if s == "medium" else "🟢"
                response += f"  {emoji} {s}: {c}\n"
            await msg.answer(response)
        else:
            incidents = await incident_logger.get_recent_incidents()
            await msg.answer(incidents)

    @dp.message(Command("incident_action"))
    async def cmd_incident_action(msg: Message):
        if not is_owner(msg): return
        args = msg.text.split(maxsplit=2)
        if len(args) < 3:
            await msg.answer("Ishlatish: `/incident_action 123 Chora matni`")
            return
        incident_id = int(args[1])
        action_text = args[2]
        result = await incident_logger.add_action(incident_id, action_text, msg.from_user.first_name)
        await msg.answer(result["message"])

    # ════════════════════════════════════════════════════════════
    #  ESLATMALAR
    # ════════════════════════════════════════════════════════════

    @dp.message(Command("reminder"))
    async def cmd_reminder(msg: Message):
        if not is_owner(msg): return
        text = msg.text.replace("/reminder", "").strip()
        if not text:
            await msg.answer(
                "⏰ *Eslatma qo'shish*\n\n"
                "Format: `/reminder 21:00 da nasosni tekshir`\n"
                "Yoki guruhda: `eslatilsin 03:32 da PP-612 nasos ochib qoldi`"
            )
            return
        reminders = await group_notifier.extract_reminders_from_message(text, msg.from_user.id)
        if reminders:
            for rem in reminders:
                await group_notifier.save_reminder(rem["text"], rem["remind_at"], msg.from_user.id)
            await msg.answer(f"✅ {len(reminders)} ta eslatma saqlandi!")
        else:
            await msg.answer("❌ Vaqt formatini to'g'ri kiriting. Masalan: `21:00 da ...`")

    @dp.message(Command("reminder_done"))
    async def cmd_reminder_done(msg: Message):
        if not is_owner(msg): return
        args = msg.text.split()
        if len(args) < 2:
            await msg.answer("Ishlatish: `/reminder_done 123`")
            return
        reminder_id = int(args[1])
        await group_notifier.mark_reminder_done(reminder_id)
        await msg.answer(f"✅ Eslatma #{reminder_id} bajarilgan deb belgilandi")

    @dp.message(Command("daily_events"))
    async def cmd_daily_events(msg: Message):
        if not is_owner(msg): return
        report = await group_notifier.get_daily_events_report()
        await msg.answer(report)

    # ════════════════════════════════════════════════════════════
    #  KNOWLEDGE BASE
    # ════════════════════════════════════════════════════════════

    @dp.message(Command("kb"))
    async def cmd_kb(msg: Message):
        if not is_owner(msg): return
        cats = await kb.list_categories()
        lines = ["📚 *MBF-3 Bilim Bazasi*\n"]
        cat_emoji = {"slurry_pump": "🔩", "GMD": "⚡", "mill": "⚙️",
                     "flotation": "⚗️", "conveyor": "🏗", "standards": "📌",
                     "predictive": "🔮", "digital_twin": "🤖", "custom": "📄"}
        for cat, cnt in cats.items():
            e = cat_emoji.get(cat, "📄")
            lines.append(f"{e} {cat}: {cnt} ta hujjat")
        lines.append("\n_Qidirish:_ `KB: warman kaviatsiya`")
        lines.append("_PDF yuborish:_ bilim bazasiga qo'shiladi")
        await msg.answer("\n".join(lines))

    # ════════════════════════════════════════════════════════════
    #  AUTOPILOT / AUTOREPLY
    # ════════════════════════════════════════════════════════════

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

    # ════════════════════════════════════════════════════════════
    #  STANDART BUYRUQLAR
    # ════════════════════════════════════════════════════════════

    @dp.message(Command("tasks"))
    async def cmd_tasks(msg: Message):
        if not is_owner(msg): return
        tasks = await db.get_tasks()
        if not tasks:
            await msg.answer("✅ Faol vazifalar yo'q.")
            return
        lines = ["📋 *Vazifalar:*\n"]
        for i, t in enumerate(tasks, 1):
            due = f" — _{t['due'][:10]}_" if t["due"] else ""
            lines.append(f"{i}. {t['title']}{due}")
        await msg.answer("\n".join(lines))

    @dp.message(Command("notes"))
    async def cmd_notes(msg: Message):
        if not is_owner(msg): return
        notes = await db.get_notes()
        if not notes:
            await msg.answer("📝 Zametka yo'q.")
            return
        lines = ["📝 *Zametkalar:*\n"]
        for i, n in enumerate(notes, 1):
            pin = "⭐ " if n["pinned"] else ""
            short = n["content"][:80] + ("..." if len(n["content"]) > 80 else "")
            lines.append(f"{i}. {pin}{short}")
        await msg.answer("\n".join(lines))

    @dp.message(Command("report"))
    async def cmd_report(msg: Message):
        if not is_owner(msg): return
        stats = await db.get_weekly_stats()
        response = (
            f"📊 *Haftalik Hisobot* _{datetime.now().strftime('%d.%m.%Y')}_\n\n"
            f"💬 {stats['messages']} xabar | 📝 {stats['notes']} zametka\n"
            f"✅ {stats['done']} bajarildi | ⏳ {stats['pending']} kutmoqda"
        )
        await msg.answer(response)

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

    # ════════════════════════════════════════════════════════════
    #  MEDIA HANDLERLAR
    # ════════════════════════════════════════════════════════════

    @dp.message(F.voice)
    async def handle_voice(msg: Message):
        if not is_owner(msg): return
        wait = await msg.answer("🎤 _Ovoz tahlil qilinmoqda..._")
        try:
            file = await msg.bot.get_file(msg.voice.file_id)
            audio = (await msg.bot.download_file(file.file_path)).read()
            text = await ai.transcribe_voice(audio)
            if not text:
                await wait.edit_text("❌ Ovozni tushunib bo'lmadi.")
                return
            await wait.edit_text(f"🎤 _Eshitildi:_ {text}\n\n⏳ _Qayta ishlanmoqda..._")
            resp = await process_text(text, db, ai, userbot, owner_id, tts, mech, vis, kb, digit_twin, personal_twin, group_notifier)
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
        wait = await msg.answer("📄 _PDF qayta ishlanmoqda..._")
        file = await msg.bot.get_file(msg.document.file_id)
        pdf_b = (await msg.bot.download_file(file.file_path)).read()
        caption = msg.caption or ""

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
        wait = await msg.answer("🖼 _Tahlil qilinmoqda..._")
        photo = msg.photo[-1]
        file = await msg.bot.get_file(photo.file_id)
        img = (await msg.bot.download_file(file.file_path)).read()

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
            result = await ai.analyze_image(img, msg.caption or "")
            await wait.edit_text(f"🖼 *Rasm tahlili:*\n\n{result[:3500]}")

    @dp.message(F.text)
    async def handle_text(msg: Message):
        if not is_owner(msg): return
        await db.save_message(msg.from_user.id, "in", msg.text)
        await db.save_conversation("user", msg.text)
        await msg.bot.send_chat_action(msg.chat.id, "typing")

        if personal_twin:
            await personal_twin.learn_from_message(msg.text)

        resp = await process_text(
            msg.text, db, ai, userbot, owner_id, tts, mech, vis, kb, digit_twin, personal_twin, group_notifier
        )
        await msg.answer(resp[:4000])
        await db.save_message(msg.from_user.id, "out", resp)
        await db.save_conversation("assistant", resp)

    # ════════════════════════════════════════════════════════════
    #  GURUH XABARLARINI KUZATISH
    # ════════════════════════════════════════════════════════════

    @dp.message(F.chat.type.in_({"group", "supergroup"}))
    async def monitor_group_messages(message: Message):
        if GROUP_CHAT_ID and str(message.chat.id) != GROUP_CHAT_ID:
            return
        await group_notifier.process_group_message(message, message.bot)

    # ════════════════════════════════════════════════════════════
    #  ESLATMALARNI VAQTI KELGANDA TEKSHIRISH (BACKGROUND)
    # ════════════════════════════════════════════════════════════

    async def reminder_checker_task():
        """Har daqiqada eslatmalarni tekshiruvchi fon vazifasi"""
        while True:
            try:
                # Bot obyektini olish
                bot = dp.bot if hasattr(dp, 'bot') else None
                if bot:
                    notified = await group_notifier.check_reminders_and_notify(bot)
                    if notified:
                        log.info(f"{len(notified)} ta eslatma yuborildi")
            except Exception as e:
                log.error(f"Reminder checker xatosi: {e}")
            await asyncio.sleep(60)

    # Background taskni ishga tushirish
    asyncio.create_task(reminder_checker_task())
    log.info("✅ Background tasklar ishga tushdi: Reminder checker")


# ════════════════════════════════════════════════════════════════
#  ASOSIY QAYTA ISHLASH FUNKSIYASI
# ════════════════════════════════════════════════════════════════

async def process_text(text: str, db: Database, ai: AIServices,
                       userbot: UserBot, owner_id: int,
                       tts: TTSService, mech: MechanicService,
                       vis: VisionService, kb: KnowledgeBase,
                       dt: DigitalTwin,
                       personal_twin=None,
                       group_notifier=None) -> str:
    """Matnli xabarlarni qayta ishlash"""

    action, data = quick_intent(text)
    if action is None:
        intent = await ai.detect_intent(text)
        action = intent.get("action", "chat")
        data = intent

    # ── Ovozli xabar ────────────────────────────────────────
    if action == "voice_send":
        return await action_send_voice_message(
            data.get("target", ""), data.get("content", ""), userbot, ai, tts)

    elif action == "send_message":
        return await action_send_message(data.get("target", ""), data.get("content", ""), userbot)

    # ── Whitelist ────────────────────────────────────────────
    elif action == "whitelist_add":
        if userbot.auto_reply:
            userbot.auto_reply.add_to_whitelist(data.get("contact", ""))
            return f"✅ Whitelist ga qo'shildi: `{data.get('contact')}`"
        return "❌ AutoReply ulanmagan."

    # ── Digital Twin ─────────────────────────────────────────
    elif action == "twin_update":
        eq_id = data.pop("equipment_id", "")
        return await dt.update_state(eq_id, **data)

    elif action == "twin_predict":
        return await dt.get_ai_prediction(data.get("equipment_id", ""))

    elif action == "twin_maintenance":
        eq_id = data.pop("equipment_id", "")
        return await dt.add_maintenance_log(
            eq_id,
            work_type=data.get("work_type", "Ta'mirlash"),
            description=data.get("description", ""),
            parts_used=data.get("parts_used", ""),
            duration_h=float(data.get("duration_h", 0)) if data.get("duration_h") else None
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
        tasks = await db.get_tasks()
        if not tasks:
            return "✅ Faol vazifalar yo'q."
        lines = ["📋 *Vazifalar:*\n"]
        for i, t in enumerate(tasks, 1):
            due = f" — _{t['due'][:10]}_" if t["due"] else ""
            lines.append(f"{i}. {t['title']}{due}")
        return "\n".join(lines)

    elif action == "done_task":
        tid = data.get("task_id")
        if tid:
            await db.complete_task(int(tid))
            return f"✅ Vazifa #{tid} bajarildi!"
        return "❓ Qaysi vazifa?"

    elif action == "get_notes":
        notes = await db.get_notes()
        if not notes:
            return "📝 Zametka yo'q."
        lines = ["📝 *Zametkalar:*\n"]
        for i, n in enumerate(notes, 1):
            pin = "⭐ " if n["pinned"] else ""
            short = n["content"][:80] + ("..." if len(n["content"]) > 80 else "")
            lines.append(f"{i}. {pin}{short}")
        return "\n".join(lines)

    elif action == "currency":
        return await action_currency(data.get("amount"), data.get("currency"))

    elif action == "weather":
        return await action_weather(data.get("city", "Olmaliq"))

    elif action == "report":
        stats = await db.get_weekly_stats()
        return (
            f"📊 *Haftalik Hisobot* _{datetime.now().strftime('%d.%m.%Y')}_\n\n"
            f"💬 {stats['messages']} xabar | 📝 {stats['notes']} zametka\n"
            f"✅ {stats['done']} bajarildi | ⏳ {stats['pending']} kutmoqda"
        )

    elif action == "memory":
        stats = await db.get_all_memories_count()
        return (f"🧠 *Xotira:* Jami:{stats['total']} | "
                f"Doimiy:{stats['permanent']} | Eskirmoqda:{stats['expiring_soon']}")

    # ── Mexanik funksiyalar ───────────────────────────────────
    elif action == "equipment_info":
        return mech.get_equipment_info(data.get("equipment", "nasos"))

    elif action == "safety_check":
        return mech.get_safety_checklist(data.get("work_type") or text)

    elif action == "incident":
        return mech.get_incident_guide(data.get("incident_type") or text)

    elif action == "hydraulic_calc":
        return mech.hydraulic_calc(data.get("flow", 50), data.get("dia", 100), data.get("length", 100))

    elif action == "pneumatic_calc":
        return mech.pneumatic_calc(data.get("vol", 10), data.get("pressure", 8), data.get("time", 5))

    elif action == "bearing_calc":
        return mech.bearing_calc(data.get("C", 50), data.get("P", 20), data.get("n", 1500))

    elif action == "defect_act":
        return mech.build_defect_act(parse_doc_params(data.get("raw", ""), "defect"))

    elif action == "work_report":
        return mech.build_work_report(parse_doc_params(data.get("raw", ""), "report"))

    elif action == "service_letter":
        return mech.build_service_letter(parse_doc_params(data.get("raw", ""), "letter"))

    elif action == "ppr_schedule":
        return await mech.generate_ppr_schedule(data.get("equipment", ["nasos"]))

    else:
        # ── RAG + AI suhbat ─────────────────────────────────
        kb_answer = await kb.answer_with_rag(text)
        if kb_answer:
            return kb_answer

        if personal_twin:
            memories = await db.get_relevant_memories(text)
            context = "\n".join(f"• {m}" for m in memories) if memories else ""
            history = await db.get_conversation_history()
            reply = await personal_twin.generate_reply(text, "")
            if reply:
                return reply

        memories = await db.get_relevant_memories(text)
        context = "\n".join(f"• {m}" for m in memories) if memories else ""
        history = await db.get_conversation_history()
        return await ai.chat(text, history, context)


# ════════════════════════════════════════════════════════════════
#  YORDAMCHI FUNKSIYALAR
# ════════════════════════════════════════════════════════════════

def quick_intent(text: str) -> tuple:
    """Xabar matnidan intensionni aniqlash"""
    t, tl = text.strip(), text.strip().lower()

    # Ovozli xabar
    m = re.search(r'^(.+?)\s+ga\s+ovoz(?:li)?\s+(?:yoz|yubor)\s*[:\s]\s*(.+)$', t, re.I)
    if m:
        return ("voice_send", {"target": m.group(1).strip(), "content": m.group(2).strip()})

    # Matnli xabar
    m = re.search(r'^(.+?)\s+ga\s+yoz(?:ing)?\s*[:\s]\s*(.+)$', t, re.I)
    if m:
        return ("send_message", {"target": m.group(1).strip(), "content": m.group(2).strip()})

    # Whitelist boshqaruv
    m = re.search(r'whitelist\s+(?:qo\'sh|add)[:\s]+(.+)', tl)
    if m:
        return ("whitelist_add", {"contact": m.group(1).strip()})

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
        if note_m:
            params['notes'] = note_m.group(1)
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
            if pm:
                params[key] = pm.group(1).strip()
        return ("twin_maintenance", params)

    # KB qidiruv
    m = re.search(r'^(?:kb|bilim|база)[:\s]+(.+)', tl)
    if m:
        return ("kb_search", {"query": m.group(1).strip()})

    # Zametka
    m = re.match(r'^(?:eslab qol|zametka|yodda tut|saqlab qol|qeyd)[:\s]+(.+)', t, re.I)
    if m:
        return ("save_note", {"content": m.group(1).strip()})

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
    if m:
        return ("done_task", {"task_id": m.group(1)})

    # Valyuta
    if any(w in tl for w in ['dollar', 'kurs', 'valyuta', 'evro', 'rubl', 'usd', 'eur', 'rub']):
        am = re.search(r'(\d[\d\s,.]*)[\s]*(dollar|usd|euro|evro|rubl|rub)', tl)
        return ("currency", {"amount": am.group(1) if am else None,
                            "currency": am.group(2) if am else None})

    # Ob-havo
    if any(w in tl for w in ["ob-havo", "ob havo", "havo", "погода", "temperatura"]):
        cm = re.search(r'(\w+)\s+(?:da|dagi)?\s*(?:ob-havo|havo)', tl)
        return ("weather", {"city": cm.group(1) if cm else "Olmaliq"})

    # Hisob-kitoblar
    if any(w in tl for w in ['gidravlik hisob', 'hydraulic', 'truba hisob']):
        params = {}
        for pat, key in [(r'sarif[=:\s]+([\d.]+)', 'flow'), (r'diametr?[=:\s]+([\d.]+)', 'dia'), (r'uzunlik[=:\s]+([\d.]+)', 'length')]:
            pm = re.search(pat, tl)
            if pm:
                params[key] = float(pm.group(1))
        return ("hydraulic_calc", params)

    if any(w in tl for w in ['pnevmatik hisob', 'kompressor quvvat', 'havo hisob']):
        params = {}
        for pat, key in [(r'hajm[=:\s]+([\d.]+)', 'vol'), (r'bosim[=:\s]+([\d.]+)', 'pressure'), (r'vaqt[=:\s]+([\d.]+)', 'time')]:
            pm = re.search(pat, tl)
            if pm:
                params[key] = float(pm.group(1))
        return ("pneumatic_calc", params)

    if any(w in tl for w in ['podshipnik resurs', 'bearing calc']):
        params = {}
        for pat, key in [(r'\bc[=:\s]+([\d.]+)', 'C'), (r'\bp[=:\s]+([\d.]+)', 'P'), (r'\bn[=:\s]+([\d.]+)', 'n')]:
            pm = re.search(pat, tl)
            if pm:
                params[key] = float(pm.group(1))
        return ("bearing_calc", params)

    # Qurilma muammolari
    for eq in ['nasos', 'kompressor', 'konveyер', 'tegirmon', 'flotatsiya']:
        if eq in tl:
            return ("equipment_info", {"equipment": eq})

    # Xavfsizlik
    if any(w in tl for w in ['xavfsizlik', 'checklist', 'ruxsatnoma', 'xavfli ish']):
        return ("safety_check", {"work_type": t})

    # Hodisa
    if any(w in tl for w in ["hodisa", "baxtsiz", "yong'in", "jarohat", "avaria", "avariya"]):
        return ("incident", {"incident_type": t})

    # Hujjatlar
    if any(w in tl for w in ['defekt akt', 'defekt akti', 'nuqson dalolatnoma']):
        return ("defect_act", {"raw": t})
    if any(w in tl for w in ['ish hisoboti', 'kunlik hisobot', 'smena hisoboti']):
        return ("work_report", {"raw": t})
    if any(w in tl for w in ['xizmat xati', 'xat yoz']):
        return ("service_letter", {"raw": t})
    if any(w in tl for w in ['ppr', 'profilaktik', "ta'mirlash jadvali"]):
        equip = re.findall(r'nasos|kompressor|konveyер|tegirmon|flotatsiya', tl)
        return ("ppr_schedule", {"equipment": equip or ["nasos", "kompressor"]})

    # Yangi funksiyalar
    if any(w in tl for w in ['handover', 'smena topshirish', 'smena protokoli']):
        return ("start_handover", {})

    if any(w in tl for w in ['ptw', 'ruxsatnoma', 'permit']):
        return ("ptw_start", {})

    if any(w in tl for w in ['loto', 'lockout', 'tagout']):
        return ("loto", {})

    if any(w in tl for w in ['eslatma', 'reminder', 'eslatilsin']):
        return ("add_reminder", {"text": text})

    if any(w in tl for w in ['voqealar', 'daily events', 'kunlik hisobot']):
        return ("daily_events", {})

    if '/report' in tl:
        return ("report", {})
    if '/memory' in tl or 'xotira holati' in tl:
        return ("memory", {})

    return (None, {})


def parse_doc_params(raw: str, doc_type: str) -> dict:
    """Hujjat parametrlarini ajratib olish"""
    params = {}
    for key in ['qurilma', 'joy', 'nuqson', 'tamirlash', 'ehtiyot', 'muddat', 'nomer',
                'kimga', 'mavzu', 'matn', 'tel', 'smena', 'bajarildi', 'muammo', 'sarf', 'keyingi', 'davom']:
        m = re.search(rf'{key}[=:\s]+([^,\n]+)', raw, re.I)
        if m:
            params[key] = m.group(1).strip()
    if not params:
        if doc_type == "defect":
            params["nuqson"] = raw
        elif doc_type == "report":
            params["bajarildi"] = raw
        elif doc_type == "letter":
            params["matn"] = raw
    return params


async def action_send_voice_message(target, content, userbot, ai, tts):
    """Ovozli xabar yuborish"""
    if not target or not content:
        return "❓ Format:\n`Azizga ovozli yoz: kechikmoqdaman`"
    if not userbot.is_connected:
        return "❌ UserBot ulanmagan."
    proxy = await ai.build_voice_proxy_text(content, OWNER_NAME)
    audio = await tts.text_to_speech(proxy)
    if not audio:
        res = await userbot.send_message(target, f"[Ovozli xabar] {proxy}")
        if res["ok"]:
            return f"⚠️ TTS ishlamadi, matnli xabar yuborildi: *{res['name']}*"
        return f"❌ Yuborilmadi: {res['error']}"
    with tempfile.NamedTemporaryFile(suffix=".mp3", delete=False) as f:
        f.write(audio)
        tmp = f.name
    try:
        res = await userbot.send_voice(target, tmp)
        os.unlink(tmp)
        if res["ok"]:
            return (f"🎤 *{res['name']}* ga ovozli xabar yuborildi!\n"
                    f"_Matn:_ {proxy[:100]}{'...' if len(proxy) > 100 else ''}")
        return f"❌ Yuborilmadi: {res.get('error', '')}"
    except Exception as e:
        return f"❌ Ovozli xabar xatosi: {e}"


async def action_send_message(target, content, userbot):
    """Matnli xabar yuborish"""
    if not target or not content:
        return "❓ Format:\n`Azizga yoz: ertaga uchrashemiz`"
    if not userbot.is_connected:
        return "❌ UserBot ulanmagan."
    res = await userbot.send_message(target, content)
    return (f"✅ *{res['name']}* ga xabar yuborildi:\n_{content}_"
            if res["ok"] else f"❌ Yuborilmadi: {res['error']}")


async def action_save_note(content, db, ai):
    """Zametka saqlash"""
    imp = await ai.score_importance(content)
    perm = imp >= 0.75
    await db.add_note(content, is_pinned=perm)
    await db.save_memory(content, "note", perm, imp)
    flag = "\n⭐ _Muhim — doimiy saqlandi_" if perm else ""
    return f"✅ *Zametka saqlandi!*{flag}\n\n_{content}_"


async def action_add_task(data, db):
    """Vazifa qo'shish"""
    title = data.get("content", "")
    due = data.get("deadline")
    tid = await db.add_task(title, title, due)
    return f"✅ Vazifa #{tid}:\n*{title}*" + (f"\n📅 {due}" if due else "")


async def action_currency(amount=None, ctype=None):
    """Valyuta kursi"""
    try:
        async with aiohttp.ClientSession() as s:
            async with s.get("https://cbu.uz/uz/arkhiv-kursov-valyut/json/",
                              timeout=aiohttp.ClientTimeout(total=10)) as r:
                data = await r.json(content_type=None)
        rates = {d["Ccy"]: float(d["Rate"]) for d in data}
        res = (f"💱 *Valyuta (CBU)* _{datetime.now().strftime('%d.%m.%Y')}_\n\n"
               f"🇺🇸 USD: {rates.get('USD', 0):,.0f} so'm\n"
               f"🇪🇺 EUR: {rates.get('EUR', 0):,.0f} so'm\n"
               f"🇷🇺 RUB: {rates.get('RUB', 0):.2f} so'm")
        if amount and ctype:
            ccy = {'dollar': 'USD', 'usd': 'USD', 'euro': 'EUR', 'evro': 'EUR', 'rubl': 'RUB', 'rub': 'RUB'}.get(str(ctype).lower())
            if ccy:
                total = float(str(amount).replace(',', '.').replace(' ', '')) * rates.get(ccy, 0)
                res += f"\n\n💰 = *{total:,.0f} so'm*"
        return res
    except Exception as e:
        return f"❌ Kurs xatosi: {e}"


async def action_weather(city):
    """Ob-havo ma'lumoti"""
    key = os.getenv("WEATHER_API_KEY", "")
    if not key:
        return "❌ WEATHER_API_KEY yo'q."
    try:
        async with aiohttp.ClientSession() as s:
            async with s.get(
                f"https://api.openweathermap.org/data/2.5/weather?q={city}&appid={key}&units=metric&lang=ru",
                timeout=aiohttp.ClientTimeout(total=10)
            ) as r:
                d = await r.json()
        if d.get("cod") != 200:
            return f"❌ {city} topilmadi."
        return (f"🌤 *{d['name']}:* {round(d['main']['temp'])}°C\n"
                f"☁️ {d['weather'][0]['description']}\n"
                f"💧 {d['main']['humidity']}% | 💨 {d['wind']['speed']} m/s")
    except Exception as e:
        return f"❌ Ob-havo xatosi: {e}"