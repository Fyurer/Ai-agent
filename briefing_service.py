"""
Briefing Service — Kunlik audio/matnli hisobot
Ertalab PPR jadvali, ehtiyot qismlar, muhim voqealar haqida
"""

import os
import logging
from datetime import datetime, timedelta
import aiosqlite
from groq import Groq

log = logging.getLogger(__name__)

DB_PATH = os.getenv("DB_PATH", "ai_agent.db")
GROQ_MODEL = os.getenv("GROQ_MODEL", "llama3-70b-8192")


class BriefingService:
    """Kunlik briefing va eslatmalar"""

    def __init__(self):
        self.groq = Groq(api_key=os.getenv("GROQ_API_KEY"))
        self.db_path = DB_PATH

    async def generate_daily_briefing(self) -> str:
        """
        Ertalabki briefing matnini tayyorlash:
        - Bugungi PPR jadvali
        - Kutilayotgan ehtiyot qismlar
        - Kechagi muhim voqealar
        - Vazifalar eslatmasi
        """
        # 1. Bugungi PPR jadvali (o'xshash vazifalardan)
        async with aiosqlite.connect(self.db_path) as db:
            today = datetime.now().strftime('%Y-%m-%d')
            cursor = await db.execute("""
                SELECT title, due_at FROM tasks 
                WHERE status = 'pending' AND due_at IS NOT NULL
                AND date(due_at) = date('now')
                LIMIT 5
            """)
            today_tasks = await cursor.fetchall()
            
            # 2. Muddati yaqinlashayotgan vazifalar
            cursor = await db.execute("""
                SELECT title, due_at FROM tasks 
                WHERE status = 'pending' AND due_at IS NOT NULL
                AND date(due_at) BETWEEN date('now', '+1 day') AND date('now', '+3 days')
                LIMIT 3
            """)
            upcoming_tasks = await cursor.fetchall()
            
            # 3. Kechagi muhim hodisalar (critical status)
            yesterday = (datetime.now() - timedelta(days=1)).isoformat()
            cursor = await db.execute("""
                SELECT content FROM messages 
                WHERE direction = 'in' AND created_at > ?
                AND (content LIKE '%kritik%' OR content LIKE '%avaria%' OR content LIKE '%to\'xtadi%')
                LIMIT 5
            """, (yesterday,))
            incidents = await cursor.fetchall()
            
            # 4. Ehtiyot qismlar holati
            cursor = await db.execute("""
                SELECT part_name, expected_life_hours, current_usage_hours
                FROM spare_parts
                WHERE current_usage_hours > expected_life_hours * 0.8
                LIMIT 3
            """)
            expiring_parts = await cursor.fetchall()
        
        # Briefing matnini yaratish
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
        
        lines.append("\n⏰ *YAQINDA (2-3 kun ichida):*")
        if upcoming_tasks:
            for task in upcoming_tasks:
                due_date = task[1][:10] if task[1] else "? kun"
                lines.append(f"  • {task[0]} (muddat: {due_date})")
        else:
            lines.append("  • Yaqin muddatli vazifalar yo'q")
        
        lines.append("\n⚠️ *ECHKI EHTIYOT QISMLAR:*")
        if expiring_parts:
            for part in expiring_parts:
                remaining = part[1] - part[2]
                lines.append(f"  • {part[0]} — {remaining:.0f} soat qoldi")
        else:
            lines.append("  • Norma holatida")
        
        lines.append("\n📌 *KECHAGI MUHIM XABARLAR:*")
        if incidents:
            for inc in incidents:
                lines.append(f"  • {inc[0][:50]}...")
        else:
            lines.append("  • Muhim hodisa qayt etilmagan")
        
        lines.append("\n📞 _Xabar bering: /tasks, /notes, /dashboard_")
        
        return "\n".join(lines)

    async def generate_audio_briefing(self) -> bytes:
        """
        Ovozli briefing yaratish (ElevenLabs orqali)
        """
        briefing_text = await self.generate_daily_briefing()
        # TTS orqali ovozga aylantirish
        from tts_service import TTSService
        tts = TTSService()
        audio = await tts.text_to_speech(briefing_text[:2500])  # Cheklov
        return audio

    async def send_daily_briefing(self, bot, user_id: int, as_voice: bool = False):
        """
        Ertalab briefingni yuborish
        """
        if as_voice:
            audio = await self.generate_audio_briefing()
            if audio:
                from aiogram.types import BufferedInputFile
                await bot.send_voice(
                    user_id,
                    BufferedInputFile(audio, filename="briefing.mp3"),
                    caption="🌅 Kunlik ovozli briefing"
                )
            else:
                text = await self.generate_daily_briefing()
                await bot.send_message(user_id, text)
        else:
            text = await self.generate_daily_briefing()
            await bot.send_message(user_id, text)