"""
Group Notifier — Telegram guruh integratsiyasi va eslatmalar
"""

import os
import re
import logging
import aiosqlite
from datetime import datetime, timedelta

log = logging.getLogger(__name__)

DB_PATH = os.getenv("DB_PATH", "ai_agent.db")
OWNER_ID = int(os.getenv("OWNER_CHAT_ID", "0"))


class GroupNotifier:
    """Guruh xabarlarini kuzatish va eslatmalar"""

    def __init__(self):
        self.db_path = DB_PATH

    async def init_db(self):
        """Jadvallarni yaratish"""
        async with aiosqlite.connect(self.db_path) as db:
            await db.executescript("""
                CREATE TABLE IF NOT EXISTS group_messages (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    message_id INTEGER,
                    chat_id INTEGER,
                    sender_name TEXT,
                    sender_id INTEGER,
                    content TEXT,
                    importance_level TEXT DEFAULT 'normal',
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                );
                CREATE TABLE IF NOT EXISTS reminders (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    reminder_text TEXT,
                    remind_at TIMESTAMP,
                    is_done INTEGER DEFAULT 0,
                    source TEXT DEFAULT 'group',
                    created_by INTEGER,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                );
                CREATE TABLE IF NOT EXISTS important_events (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    event_text TEXT,
                    event_type TEXT,
                    equipment TEXT,
                    happened_at TIMESTAMP,
                    recorded_by INTEGER,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                );
            """)
            await db.commit()

    async def extract_reminders_from_message(self, text: str, sender_id: int) -> list:
        """Xabardan eslatmalarni avtomatik ajratib olish"""
        reminders = []
        patterns = [
            r'еslatilsin\s+(\d{1,2}:\d{2})\s+da\s+(.+?)(?:\n|$)',
            r'remind\s+(\d{1,2}:\d{2})\s+(.+?)(?:\n|$)',
            r'eslatma\s+(\d{1,2}:\d{2})\s+(.+?)(?:\n|$)',
            r"(\d{1,2}:\d{2})\s+da\s+(.+?)(?:eslat|remind|\n|$)",
        ]
        for pattern in patterns:
            matches = re.findall(pattern, text, re.IGNORECASE)
            for match in matches:
                time_str = match[0]
                reminder_text = match[1] if len(match) > 1 else text
                now = datetime.now()
                hour, minute = map(int, time_str.split(':'))
                remind_at = now.replace(hour=hour, minute=minute, second=0, microsecond=0)
                if remind_at < now:
                    remind_at += timedelta(days=1)
                reminders.append({
                    "text": reminder_text.strip(),
                    "remind_at": remind_at,
                    "source": "auto",
                    "created_by": sender_id
                })
        return reminders

    async def save_reminder(self, reminder_text: str, remind_at: datetime, created_by: int) -> int:
        """Eslatmani bazaga saqlash"""
        async with aiosqlite.connect(self.db_path) as db:
            cursor = await db.execute("""
                INSERT INTO reminders (reminder_text, remind_at, created_by)
                VALUES (?, ?, ?)
            """, (reminder_text, remind_at.isoformat(), created_by))
            await db.commit()
            return cursor.lastrowid

    async def get_pending_reminders(self) -> list:
        """Bajarilmagan va vaqti kelgan eslatmalar"""
        now = datetime.now().isoformat()
        async with aiosqlite.connect(self.db_path) as db:
            cursor = await db.execute("""
                SELECT id, reminder_text, remind_at, created_by
                FROM reminders
                WHERE is_done = 0 AND remind_at <= ?
                ORDER BY remind_at ASC
            """, (now,))
            rows = await cursor.fetchall()
            return [{"id": r[0], "text": r[1], "remind_at": r[2], "created_by": r[3]} for r in rows]

    async def mark_reminder_done(self, reminder_id: int):
        """Eslatmani bajarilgan deb belgilash"""
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute("UPDATE reminders SET is_done = 1 WHERE id = ?", (reminder_id,))
            await db.commit()

    async def check_reminders_and_notify(self, bot) -> list:
        """Vaqti kelgan eslatmalarni tekshirish"""
        reminders = await self.get_pending_reminders()
        notified = []
        for reminder in reminders:
            if OWNER_ID:
                try:
                    remind_time = datetime.fromisoformat(reminder["remind_at"])
                    await bot.send_message(
                        OWNER_ID,
                        f"⏰ *ESLATMA!*\n\n"
                        f"📅 Vaqt: {remind_time.strftime('%H:%M')}\n"
                        f"📝 {reminder['text']}\n\n"
                        f"/reminder_done {reminder['id']} — bajarilgan deb belgilash"
                    )
                    notified.append(reminder["id"])
                except Exception as e:
                    log.error(f"Eslatma yuborish xatosi: {e}")
        return notified

    async def process_group_message(self, message, bot) -> None:
        """Guruh xabarini qayta ishlash"""
        text = message.text or message.caption or ""
        if not text:
            return
        reminders = await self.extract_reminders_from_message(text, message.sender_id)
        for reminder in reminders:
            await self.save_reminder(reminder["text"], reminder["remind_at"], reminder["created_by"])
            log.info(f"Eslatma saqlandi: {reminder['text']}")

    async def get_daily_events_report(self) -> str:
        """Kunlik muhim voqealar hisoboti"""
        today_start = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0).isoformat()
        async with aiosqlite.connect(self.db_path) as db:
            cursor = await db.execute("""
                SELECT reminder_text, remind_at
                FROM reminders
                WHERE date(remind_at) = date('now')
                ORDER BY remind_at ASC
            """)
            reminders = await cursor.fetchall()

        lines = ["📋 *KUNLIK VOQEALAR HISOBOTI*", f"📅 {datetime.now().strftime('%d.%m.%Y')}\n"]
        if reminders:
            lines.append("⏰ *BUGUNGI ESLATMALAR:*")
            for rem in reminders:
                lines.append(f"  • {rem[1][:16]} — {rem[0][:50]}")
        else:
            lines.append("📭 Eslatmalar yo'q.")
        return "\n".join(lines)