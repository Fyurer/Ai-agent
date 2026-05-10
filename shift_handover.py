"""
Shift Handover Service — Smena topshirish protokoli
"""

import os
import logging
import aiosqlite
from datetime import datetime, timedelta

log = logging.getLogger(__name__)

DB_PATH = os.getenv("DB_PATH", "ai_agent.db")


class ShiftHandover:
    """Smena topshirish tizimi"""

    def __init__(self):
        self.db_path = DB_PATH
        self.pending_handovers = {}

    def get_handover_questions(self) -> list:
        """Smena topshirish uchun savollar ro'yxati"""
        return [
            {"id": "shift_num", "question": "📋 Qaysi smena?", "type": "text"},
            {"id": "operator", "question": "👤 Kim topshiryapti?", "type": "text"},
            {"id": "receiver", "question": "👥 Kim qabul qilyapti?", "type": "text"},
            {"id": "equipment_status", "question": "⚙️ Uskunalar holati (ishlayotgan/to'xtagan/nosoz):", "type": "text"},
            {"id": "issues", "question": "⚠️ Smenada qanday muammolar bo'ldi?", "type": "text"},
            {"id": "repairs_done", "question": "🔧 Qanday ta'mirlash ishlari bajarildi?", "type": "text"},
            {"id": "pending_tasks", "question": "⏳ Keyingi smenaga qanday vazifalar qoldi?", "type": "text"},
            {"id": "spare_parts", "question": "🔩 Qanday ehtiyot qismlar sarflandi?", "type": "text"},
            {"id": "safety_notes", "question": "🦺 Xavfsizlik bo'yicha eslatmalar?", "type": "text"},
            {"id": "general_notes", "question": "📝 Umumiy eslatmalar?", "type": "text"}
        ]

    async def start_handover(self, user_id: int, chat_id: int) -> str:
        """Smena topshirishni boshlash"""
        questions = self.get_handover_questions()
        self.pending_handovers[user_id] = {
            "step": 0,
            "answers": {},
            "chat_id": chat_id,
            "started_at": datetime.now().isoformat()
        }
        first_q = questions[0]
        return f"{first_q['question']}\n\n_Javobingizni yozing_"

    async def process_answer(self, user_id: int, answer: str, bot) -> str:
        """Javobni qayta ishlash"""
        if user_id not in self.pending_handovers:
            return "❌ Faol smena topshirish jarayoni yo'q. /handover_start bilan boshlang."

        handover = self.pending_handovers[user_id]
        questions = self.get_handover_questions()
        step = handover["step"]

        if step >= len(questions):
            return await self.finalize_handover(user_id, bot)

        current_q = questions[step]
        handover["answers"][current_q["id"]] = answer.strip()
        handover["step"] += 1

        if handover["step"] >= len(questions):
            return await self.finalize_handover(user_id, bot)

        next_q = questions[handover["step"]]
        return f"{next_q['question']}\n\n_Javobingizni yozing_"

    async def finalize_handover(self, user_id: int, bot) -> str:
        """Smena topshirish hisobotini tayyorlash"""
        handover = self.pending_handovers.pop(user_id, None)
        if not handover:
            return "❌ Xatolik yuz berdi."

        answers = handover["answers"]
        now = datetime.now()

        report = f"""📋 *SMENA TOPSHIRISH PROTOKOLI*
━━━━━━━━━━━━━━━━━━━━━━━
📅 Sana: {now.strftime('%d.%m.%Y')} {now.strftime('%H:%M')}
👤 Topshiruvchi: {answers.get('operator', '—')}
👥 Qabul qiluvchi: {answers.get('receiver', '—')}
📋 Smena: {answers.get('shift_num', '—')}

⚙️ *USKUNALAR HOLATI:*
{answers.get('equipment_status', '—')}

⚠️ *MUAMMOLAR:*
{answers.get('issues', '—')}

🔧 *BAJARILGAN ISHLAR:*
{answers.get('repairs_done', '—')}

⏳ *KEYINGI SMENAGA QOLDIRILGAN:*
{answers.get('pending_tasks', '—')}

🔩 *SARFLANGAN EHTIYOT QISMLAR:*
{answers.get('spare_parts', '—')}

🦺 *XAVFSIZLIK ESLATMALARI:*
{answers.get('safety_notes', '—')}

📝 *UMUMIY ESLATMALAR:*
{answers.get('general_notes', '—')}
━━━━━━━━━━━━━━━━━━━━━━━
✅ Smena topshirildi
"""
        await self._save_handover(answers, report)
        return report

    async def _save_handover(self, answers: dict, report: str):
        """Hisobotni bazaga saqlash"""
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute("""
                CREATE TABLE IF NOT EXISTS shift_handovers (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    shift_num TEXT,
                    operator TEXT,
                    receiver TEXT,
                    equipment_status TEXT,
                    issues TEXT,
                    repairs_done TEXT,
                    pending_tasks TEXT,
                    spare_parts TEXT,
                    safety_notes TEXT,
                    general_notes TEXT,
                    report_text TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            await db.execute("""
                INSERT INTO shift_handovers 
                (shift_num, operator, receiver, equipment_status, issues, repairs_done, pending_tasks, spare_parts, safety_notes, general_notes, report_text)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                answers.get('shift_num', ''),
                answers.get('operator', ''),
                answers.get('receiver', ''),
                answers.get('equipment_status', ''),
                answers.get('issues', ''),
                answers.get('repairs_done', ''),
                answers.get('pending_tasks', ''),
                answers.get('spare_parts', ''),
                answers.get('safety_notes', ''),
                answers.get('general_notes', ''),
                report
            ))
            await db.commit()

    async def get_handover_history(self, days: int = 7) -> str:
        """Smena topshirish tarixi"""
        cutoff = (datetime.now() - timedelta(days=days)).isoformat()
        async with aiosqlite.connect(self.db_path) as db:
            cursor = await db.execute("""
                SELECT shift_num, operator, issues, created_at 
                FROM shift_handovers 
                WHERE created_at > ?
                ORDER BY created_at DESC LIMIT 10
            """, (cutoff,))
            rows = await cursor.fetchall()

        if not rows:
            return "📋 Smena topshirish tarixi topilmadi."

        lines = ["📋 *Smena topshirish tarixi (oxirgi 7 kun):*\n"]
        for row in rows:
            lines.append(f"📅 {row[3][:16]} | {row[0]} | {row[1]}")
            lines.append(f"   ⚠️ {row[2][:60]}{'...' if len(row[2]) > 60 else ''}")
            lines.append("")
        return "\n".join(lines)