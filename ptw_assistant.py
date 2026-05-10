"""
PTW Assistant — Permit-to-Work yordamchisi
"""

import os
import json
import logging
import aiosqlite
from datetime import datetime

log = logging.getLogger(__name__)

DB_PATH = os.getenv("DB_PATH", "ai_agent.db")


class PTWAssistant:
    """Permit-to-Work tizimi"""

    WORK_TYPES = {
        "elektr": {
            "name": "Elektr ta'mirlash ishlari",
            "checklist": [
                "Energiya manbai o'chirilganmi?",
                "Voltmetr bilan kuchlanish yo'qligi tekshirilganmi?",
                "Qulflash (Lockout) qurilmasi o'rnatilganmi?",
                "Ogohlantiruvchi yorliq osilganmi?",
                "Dielektrik qo'lqop va poyabzal mavjudmi?"
            ]
        },
        "balandlik": {
            "name": "Balandlikda ishlash (3m dan yuqori)",
            "checklist": [
                "Xavfsizlik kamari (harness) to'g'ri kiyilganmi?",
                "Xavfsizlik arqoni mahkamlanganmi?",
                "Narvon/iskala mustahkamligi tekshirilganmi?",
                "Pastda xavfsizlik maydoni ajratilganmi?",
                "2 kishidan kam bo'lmagan holda ishlanayaptimi?"
            ]
        },
        "bosimli": {
            "name": "Bosimli tizimda ishlash",
            "checklist": [
                "Bosim nolga tushirilganmi?",
                "Bosim manbai bloklanganmi?",
                "Manometr ko'rsatkichi nolni ko'rsatyaptimi?",
                "Purgatsiya (havo chiqarish) qilinganmi?",
                "Himoya ko'zoynak va yuz qalqoni kiyilganmi?"
            ]
        }
    }

    LOTO_STEPS = [
        "1. 📋 KIMLAR XABARDOR: Uskunada ish boshlanishi haqida barchani xabardor qiling",
        "2. 🔍 ENERGIYA MANBALARINI ANIQLASH: Barcha energiya manbalarini toping",
        "3. ⚡ TO'XTATISH: Uskunani to'liq va xavfsiz to'xtating",
        "4. 🔒 QULFLASH (LOCKOUT): Har bir energiya manbasiga shaxsiy qulfni o'rnating",
        "5. 🏷 TEG (TAGOUT): Har bir qulfga o'zingizning tegingizni osing",
        "6. 🔧 ENERGIYANI CHIQARISH: Qolgan energiyani xavfsiz chiqaring",
        "7. ✅ TEKSHIRISH: Uskuna ishga tushmasligiga ishonch hosil qiling",
        "8. 🔨 ISHNI BOSHLASH: Faqat tekshiruvdan keyin ishni boshlang",
        "9. 🔓 QAYTA TIKLASH: Ish tugagach, qulflarni olib tashlang",
        "10. 📝 HUJJATLASHTIRISH: LOTO protsedurasini jurnalga yozing"
    ]

    def __init__(self):
        self.db_path = DB_PATH
        self.active_permits = {}

    async def init_db(self):
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute("""
                CREATE TABLE IF NOT EXISTS ptw_permits (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    permit_number TEXT,
                    work_type TEXT,
                    requester TEXT,
                    location TEXT,
                    checklist_answers TEXT,
                    status TEXT DEFAULT 'pending',
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            await db.commit()

    def get_work_types(self) -> dict:
        return {k: v["name"] for k, v in self.WORK_TYPES.items()}

    def start_permit(self, user_id: int, work_type: str, location: str = "") -> dict:
        if work_type not in self.WORK_TYPES:
            return {"error": f"'{work_type}' ish turi topilmadi"}
        work_info = self.WORK_TYPES[work_type]
        self.active_permits[user_id] = {
            "work_type": work_type,
            "work_name": work_info["name"],
            "location": location,
            "step": 0,
            "answers": {},
            "checklist": work_info["checklist"]
        }
        return {
            "success": True,
            "message": f"🦺 *PTW Jarayoni boshlandi*\n⚙️ Ish turi: {work_info['name']}\n📍 Joy: {location or '—'}",
            "first_question": work_info["checklist"][0]
        }

    def process_answer(self, user_id: int, answer: str) -> dict:
        if user_id not in self.active_permits:
            return {"error": "Faol PTW jarayoni yo'q."}
        permit = self.active_permits[user_id]
        step = permit["step"]
        checklist = permit["checklist"]
        if step >= len(checklist):
            return self.finalize_permit(user_id)
        is_approved = answer.strip().lower() in ['✅', 'ha', 'yes', 'y', '1', '+', 'ok']
        permit["answers"][step] = {"question": checklist[step], "answer": is_approved}
        if not is_approved:
            del self.active_permits[user_id]
            return {"success": False, "message": f"❌ *PTW BEKOR QILINDI*\nSavol: {checklist[step]}\nJavob: {answer}"}
        permit["step"] += 1
        if permit["step"] >= len(checklist):
            return self.finalize_permit(user_id)
        return {
            "success": True,
            "step": permit["step"] + 1,
            "total": len(checklist),
            "question": checklist[permit["step"]],
            "message": f"✅ Javob qabul qilindi.\n\n*Savol {permit['step'] + 1}/{len(checklist)}:*\n{checklist[permit['step']]}"
        }

    def finalize_permit(self, user_id: int) -> dict:
        permit = self.active_permits.pop(user_id, None)
        if not permit:
            return {"error": "Xatolik yuz berdi."}
        permit_number = f"PTW-{datetime.now().strftime('%Y%m%d')}-{permit['work_type'][:3].upper()}"
        all_approved = all(v["answer"] for v in permit["answers"].values())
        if all_approved:
            message = f"✅ *PERMIT-TO-WORK TASDIQLANDI*\n\n📋 Ruxsatnoma №: {permit_number}\n⚙️ Ish turi: {permit['work_name']}\n📍 Joy: {permit['location'] or '—'}\n\n⚠️ /loto — LOTO qadamlarini ko'rish"
        else:
            message = f"❌ *PTW TASDIQLANMADI*\n\n⚠️ Ba'zi xavfsizlik shartlari bajarilmagan."
        return {"success": all_approved, "permit_number": permit_number, "message": message}

    def get_loto_steps(self) -> str:
        return "🔒 *LOCK-OUT/TAG-OUT (LOTO) PROTSEDURASI*\n\n" + "\n".join(self.LOTO_STEPS)

    def get_loto_checklist(self) -> str:
        checklist = self.WORK_TYPES["elektr"]["checklist"][:5]
        lines = ["🔒 *LOTO CHECKLIST*", ""]
        for item in checklist:
            lines.append(f"  ❓ {item}")
        return "\n".join(lines)