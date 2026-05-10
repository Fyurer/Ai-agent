"""
Briefing Service — Kunlik audio/matnli hisobot
"""

import os
import logging
import aiosqlite
from datetime import datetime

log = logging.getLogger(__name__)

DB_PATH = os.getenv("DB_PATH", "ai_agent.db")


class BriefingService:
    """Kunlik briefing"""

    def __init__(self):
        self.db_path = DB_PATH

    async def generate_daily_briefing(self) -> str:
        async with aiosqlite.connect(self.db_path) as db:
            cursor = await db.execute("""
                SELECT title, due_at FROM tasks 
                WHERE status = 'pending' AND due_at IS NOT NULL
                AND date(due_at) = date('now')
                LIMIT 5
            """)
            today_tasks = await cursor.fetchall()

        lines = [
            "🌅 *KUNLIK BRIEFING*",
            f"📅 {datetime.now().strftime('%d.%m.%Y, %A')}",
            "",
            "📋 *BUGUNGI PPR / VAZIFALAR:*"
        ]
        if today_tasks:
            for task in today_tasks:
                lines.append(f"  • {task[0]}")
        else:
            lines.append("  • Bugungi rejalashtirilgan vazifalar yo'q")
        lines.append("\n📞 _Xabar bering: /tasks, /notes, /dashboard_")
        return "\n".join(lines)

    async def generate_audio_briefing(self) -> bytes:
        return None  # TTS uchun keyin qo'shiladi