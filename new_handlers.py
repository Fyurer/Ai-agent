"""
NEW HANDLERS — handlers.py ga qo'shiladigan yangi handler va funksiyalar
Bu faylni handlers.py ning oxiriga yoki alohida import sifatida ulang.

Yangi buyruqlar:
/autopilot_on /autopilot_off — AutoPilot rejimi
/busy_on [sabab] /busy_off — Band rejimi
/ap_status — AutoPilot holati
/ap_log — Avtomatik javoblar logi
/gmd — GMD/ABB drayverlari ma'lumoti
/slurry — Slurry nasos ma'lumoti
/mbf3 [savol] — MBF-3 ekspert maslahati
/standards [mavzu] — GOST/ISO standartlar

Yangi rasm tahlil rejimlari (caption orqali):
- "defekt" yoki "nosoz" → vizual defektoskopiya
- "hse" yoki "xavfsizlik audit" → HSE tekshiruvi
- "sensor" yoki "o'lchov" → sensor skrinshot tahlili
"""

import os
import logging
from aiogram import Dispatcher, F
from aiogram.types import Message
from aiogram.filters import Command

from visual_inspector import VisualInspector
from autopilot import AutoPilot
from knowledge_base import KnowledgeBase

log = logging.getLogger(__name__)
OWNER_NAME = os.getenv("OWNER_NAME", "O'tkirbek")


def register_new_handlers(dp: Dispatcher, db, ai, userbot, owner_id: int):
    """
    Yangi funksiyalar handlerlari.
    bot.py da: register_new_handlers(dp, db, ai, userbot, owner_id) qo'shing.
    """
    visual = VisualInspector()
    ap     = AutoPilot()
    kb     = KnowledgeBase()

    def is_owner(msg: Message) -> bool:
        return msg.from_user.id == owner_id

    # ════════════════════════════════════════════════════
    # 🤖 AUTOPILOT BUYRUQLARI
    # ════════════════════════════════════════════════════

    @dp.message(Command("autopilot_on"))
    async def cmd_autopilot_on(msg: Message):
        if not is_owner(msg): return
        await msg.answer(ap.enable())

    @dp.message(Command("autopilot_off"))
    async def cmd_autopilot_off(msg: Message):
        if not is_owner(msg): return
        await msg.answer(ap.disable())

    @dp.message(Command("ap_status"))
    async def cmd_ap_status(msg: Message):
        if not is_owner(msg): return
        await msg.answer(ap.get_status())

    @dp.message(Command("ap_log"))
    async def cmd_ap_log(msg: Message):
        if not is_owner(msg): return
        await msg.answer(ap.get_reply_log())

    # Band rejimi
    @dp.message(Command("busy_on"))
    async def cmd_busy_on(msg: Message):
        if not is_owner(msg): return
        # /busy_on ish yoki /busy_on yig'ilish
        args = msg.text.replace("/busy_on", "").strip()
        reason = args if args else "ish"
        await msg.answer(ap.enable_busy(reason))

    @dp.message(Command("busy_off"))
    async def cmd_busy_off(msg: Message):
        if not is_owner(msg): return
        await msg.answer(ap.disable_busy())

    # Kechikish xabari
    @dp.message(Command("late"))
    async def cmd_late(msg: Message):
        """
        /late 15 [sabab] [kimga]
        Misol: /late 20 transport muammosi smena boshliq
        """
        if not is_owner(msg): return
        parts = msg.text.replace("/late", "").strip().split()
        minutes = 15
        reason  = ""
        if parts:
            try:
                minutes = int(parts[0])
                reason  = " ".join(parts[1:])
            except ValueError:
                reason = " ".join(parts)

        wait = await msg.answer("⏳ _Kechikish xabari tayyorlanmoqda..._")
        text = await ap.late_notification(minutes, reason)
        await wait.edit_text(
            f"🕐 *KECHIKISH XABARI*\n"
            f"_{minutes} daqiqa | {reason or 'sabab ko\\'rsatilmadi'}_\n\n"
            f"📝 *Tayyor matn:*\n{text}\n\n"
            f"_Bu matnni ovozli xabar sifatida yuborish uchun:_\n"
            f"`[kontakt] ga ovozli yoz: {text[:50]}...`"
        )

    # ════════════════════════════════════════════════════
    # 🏭 MBF-3 BILIMLAR BAZASI BUYRUQLARI
    # ════════════════════════════════════════════════════

    @dp.message(Command("gmd"))
    async def cmd_gmd(msg: Message):
        if not is_owner(msg): return
        query = msg.text.replace("/gmd", "").strip()
        await msg.answer(kb.get_gmd_info(query))

    @dp.message(Command("slurry"))
    async def cmd_slurry(msg: Message):
        if not is_owner(msg): return
        query = msg.text.replace("/slurry", "").strip()
        await msg.answer(kb.get_slurry_pump_info(query))

    @dp.message(Command("flotation"))
    async def cmd_flotation(msg: Message):
        if not is_owner(msg): return
        query = msg.text.replace("/flotation", "").strip()
        await msg.answer(kb.get_flotation_info(query))

    @dp.message(Command("mbf3"))
    async def cmd_mbf3(msg: Message):
        """
        /mbf3 [savol] — MBF-3 ekspert darajasida maslahat
        Misol: /mbf3 GMD air gap qanday o'lchanadi?
        """
        if not is_owner(msg): return
        question = msg.text.replace("/mbf3", "").strip()
        if not question:
            await msg.answer(
                "💡 *MBF-3 Ekspert Maslahati*\n\n"
                "Savol yozing:\n"
                "`/mbf3 GMD fault kodi A010 nima degan?`\n"
                "`/mbf3 Warman AH nasos kaviatsiyasi qanday aniqlanadi?`\n"
                "`/mbf3 Flotatsiya reagenti dozalash qanday hisoblanadi?`\n\n"
                "Yoki buyruqlar:\n"
                "/gmd — GMD/ABB drayverlari\n"
                "/slurry — Slurry nasoslar\n"
                "/flotation — Flotatsiya mashinalari\n"
                "/standards [mavzu] — GOST/ISO standartlar"
            )
            return
        wait = await msg.answer("🏭 _MBF-3 bilimlar bazasidan izlanmoqda..._")
        result = await kb.expert_consult(question)
        await wait.edit_text(result)

    @dp.message(Command("standards"))
    async def cmd_standards(msg: Message):
        if not is_owner(msg): return
        topic = msg.text.replace("/standards", "").strip()
        if not topic:
            await msg.answer(
                "📋 *Mavjud standartlar:*\n\n"
                "• tebranish — ISO 10816/20816\n"
                "• podshipnik — ISO 281, GOST 18855\n"
                "• nasoslar — GOST 22247, API 610\n"
                "• elektr_xavfsizlik — GOST 12.1.019\n"
                "• hse — ISO 45001, GOST 12.0.004\n"
                "• texnik_xizmat — GOST 18322-2016\n"
                "• chertyo'j — GOST 2.101, GOST 2.602\n"
                "• metall — GOST 380, GOST 1050\n"
                "• payvand — GOST 5264, GOST 14771\n\n"
                "_Misol: /standards tebranish_"
            )
            return
        await msg.answer(kb.get_standard(topic))

    @dp.message(Command("kbsearch"))
    async def cmd_kbsearch(msg: Message):
        """Bilimlar bazasida qidirish"""
        if not is_owner(msg): return
        query = msg.text.replace("/kbsearch", "").strip()
        if not query:
            await msg.answer("🔍 `/kbsearch [so'z]` — bilimlar bazasida qidirish")
            return
        await msg.answer(kb.search(query))

    # ════════════════════════════════════════════════════
    # 📊 SENSOR TAHLILI (MATN ORQALI)
    # ════════════════════════════════════════════════════

    @dp.message(Command("sensor"))
    async def cmd_sensor(msg: Message):
        """
        /sensor [uskuna nomi]
        Keyin sensor ma'lumotlarini matn sifatida yuboring.
        
        Misol:
        /sensor Nasos №5
        Tebranish: 6.2 mm/s
        Harorat podshipnik: 87°C
        Bosim: 0.45 MPa
        Tok: 48A (nominal 45A)
        """
        if not is_owner(msg): return
        parts = msg.text.split("\n", 1)
        equipment = parts[0].replace("/sensor", "").strip() or "Noma'lum uskuna"

        if len(parts) < 2:
            await msg.answer(
                "📊 *Sensor Ma'lumotlari Tahlili*\n\n"
                "Format:\n"
                "```\n"
                "/sensor Nasos №5 (uskuna nomi)\n"
                "Tebranish: 6.2 mm/s\n"
                "Harorat: 87°C\n"
                "Bosim: 0.45 MPa\n"
                "Tok: 48A\n"
                "```\n\n"
                "Yoki sensor ekranining rasmini yuboring:\n"
                "`[rasm] + sensor` deb yozing"
            )
            return

        sensor_data = parts[1].strip()
        wait = await msg.answer(f"📊 _{equipment} sensor ma'lumotlari tahlil qilinmoqda..._")
        result = await visual.analyze_sensor_data(sensor_data, equipment)
        await wait.edit_text(result)

    # ════════════════════════════════════════════════════
    # 🖼 RASM HANDLERI YANGILANGAN (handlers.py dagi handle_photo ni almashtiring)
    # ════════════════════════════════════════════════════

    # Bu funksiya handlers.py dagi handle_photo ni kengaytiradi
    # Quyidagi caption kalitlarini tekshiradi:
    # "defekt" / "nosoz" → vizual defektoskopiya
    # "hse" / "audit" / "ppe" → HSE tekshiruv
    # "sensor" / "o'lchov" / "skrinshot" → sensor ekran tahlil
    # "chertyo'j" / "sxema" → chertyo'j (mavjud)

    @dp.message(F.photo)
    async def handle_photo_extended(msg: Message):
        if not is_owner(msg): return
        caption = (msg.caption or "").lower()

        wait  = await msg.answer("🖼 _Rasm tahlil qilinmoqda..._")
        photo = msg.photo[-1]
        file  = await msg.bot.get_file(photo.file_id)
        img   = (await msg.bot.download_file(file.file_path)).read()

        # HSE Audit
        if any(w in caption for w in ["hse", "audit", "ppe", "xavfsizlik audit", "kiyim tekshir"]):
            location = msg.caption or ""
            result = await visual.hse_audit(img, location)
            await wait.edit_text(result)

        # Vizual Defektoskopiya
        elif any(w in caption for w in ["defekt", "nosoz", "tekshir", "inspect", "vizual"]):
            extra = msg.caption or ""
            result = await visual.inspect_equipment(img, extra)
            await wait.edit_text(f"🔍 *VIZUAL DEFEKTOSKOPIYA*\n\n{result}")

        # Sensor skrinshot
        elif any(w in caption for w in ["sensor", "o'lchov", "skrinshot", "monitoring", "scada", "hmi"]):
            equip = msg.caption or ""
            result = await visual.analyze_sensor_screenshot(img, equip)
            await wait.edit_text(f"📊 *SENSOR EKRANI TAHLILI*\n\n{result}")

        # Chertyo'j (mavjud funksiya)
        elif any(w in caption for w in ["chertyo", "sxema", "chizma", "drawing", "scheme", "план"]):
            result = await ai.analyze_image(img, msg.caption or "")
            await wait.edit_text(f"📐 *Chertyo'j Tahlili:*\n\n{result}")

        # Oddiy rasm → avval defektoskopiya taklifi
        else:
            result = await ai.analyze_image(img, msg.caption or "")
            await wait.edit_text(
                f"🖼 *Rasm tahlili:*\n\n{result}\n\n"
                f"💡 _Maxsus tahlil uchun caption yozing:_\n"
                f"`defekt` — vizual nosozlik tekshiruvi\n"
                f"`hse` — xavfsizlik audit\n"
                f"`sensor` — o'lchov ma'lumotlari"
            )

    # ════════════════════════════════════════════════════
    # 📖 YANGI HELP QOSHIMCHASI
    # ════════════════════════════════════════════════════

    @dp.message(Command("help2"))
    async def cmd_help2(msg: Message):
        """Yangi funksiyalar ro'yxati"""
        if not is_owner(msg): return
        await msg.answer(
            "🆕 *YANGI FUNKSIYALAR:*\n\n"

            "🤖 *AUTOPILOT:*\n"
            "/autopilot_on — kelgan xabarlarga O'tkirbek nomidan javob\n"
            "/autopilot_off — o'chirish\n"
            "/busy_on [sabab] — band rejimi\n"
            "/busy_off — band rejimini o'chirish\n"
            "/late [daqiqa] [sabab] — kechikish xabari tayyorlash\n"
            "/ap_status — AutoPilot holati\n"
            "/ap_log — avtomatik javoblar logi\n\n"

            "🏭 *MBF-3 BILIMLAR BAZASI:*\n"
            "/gmd [savol] — GMD/ABB drayverlari\n"
            "/slurry [savol] — Warman slurry nasoslar\n"
            "/flotation — Flotatsiya mashinalari\n"
            "/mbf3 [savol] — ekspert darajasida maslahat\n"
            "/standards [mavzu] — GOST/ISO standartlar\n"
            "/kbsearch [so'z] — bilimlar bazasida qidirish\n\n"

            "🔍 *VIZUAL TAHLIL (rasm + caption):*\n"
            "`[rasm] + defekt` → vizual defektoskopiya\n"
            "`[rasm] + hse` → HSE xavfsizlik audit\n"
            "`[rasm] + sensor` → o'lchov ekrani tahlili\n\n"

            "📊 *SENSOR TAHLILI:*\n"
            "/sensor [uskuna] — sensor ma'lumotlari tahlili\n"
            "(Ko'p qatorli: har qatorda parametr=qiymat)\n\n"

            "💡 Misol:\n"
            "`/late 20 transport muammosi`\n"
            "`/mbf3 GMD fault A010 nima?`\n"
            "`/sensor Nasos №3\\nTebranish: 6.5mm/s\\nHarorat: 85C`"
        )

    return ap  # AutoPilot ob'ektini qaytaramiz (userbot handleri uchun)
