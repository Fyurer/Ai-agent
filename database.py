"""
Database — SQLite (Railway da fayl sifatida)
Kengaytirilgan: xotira tizimi, kontekst, metrikalar
"""

import aiosqlite
import os
import json
from datetime import datetime, timedelta

DB_PATH = os.getenv("DB_PATH", "ai_agent.db")
MEMORY_DAYS = int(os.getenv("MEMORY_DAYS", "60"))


class Database:
    def __init__(self):
        self.path = DB_PATH

    async def init(self):
        async with aiosqlite.connect(self.path) as db:
            await db.executescript("""
                CREATE TABLE IF NOT EXISTS messages (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    chat_id INTEGER,
                    direction TEXT DEFAULT 'in',
                    content TEXT,
                    type TEXT DEFAULT 'text',
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                );

                CREATE TABLE IF NOT EXISTS memories (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    content TEXT,
                    category TEXT DEFAULT 'general',
                    tags TEXT,
                    is_permanent INTEGER DEFAULT 0,
                    importance_score REAL DEFAULT 0.5,
                    expires_at TIMESTAMP,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                );

                -- Suhbat xotirasi (kontekst uchun)
                CREATE TABLE IF NOT EXISTS conversation_memory (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_message TEXT,
                    bot_response TEXT,
                    topic TEXT,
                    summary TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                );

                CREATE TABLE IF NOT EXISTS tasks (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    title TEXT,
                    description TEXT,
                    status TEXT DEFAULT 'pending',
                    due_at TIMESTAMP,
                    reminder_sent INTEGER DEFAULT 0,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                );

                CREATE TABLE IF NOT EXISTS notes (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    title TEXT,
                    content TEXT,
                    category TEXT DEFAULT 'general',
                    is_pinned INTEGER DEFAULT 0,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                );

                CREATE TABLE IF NOT EXISTS conversations (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    role TEXT,
                    content TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                );

                -- Metrikalar va statistika
                CREATE TABLE IF NOT EXISTS metrics (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    metric_name TEXT,
                    metric_value TEXT,
                    recorded_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                );

                -- Ehtiyot qismlar
                CREATE TABLE IF NOT EXISTS spare_parts (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    part_name TEXT,
                    part_code TEXT,
                    equipment_type TEXT,
                    expected_life_hours REAL,
                    current_usage_hours REAL DEFAULT 0,
                    last_replaced_at TIMESTAMP,
                    notes TEXT
                );

                -- Arizalar (zayavkalar)
                CREATE TABLE IF NOT EXISTS requests (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    request_number TEXT,
                    equipment_id TEXT,
                    part_name TEXT,
                    quantity INTEGER,
                    request_text TEXT,
                    status TEXT DEFAULT 'pending',
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                );
            """)
            await db.commit()

    # ── Xabarlar ─────────────────────────────────────────────
    async def save_message(self, chat_id: int, direction: str, content: str, msg_type: str = "text"):
        async with aiosqlite.connect(self.path) as db:
            await db.execute(
                "INSERT INTO messages (chat_id, direction, content, type) VALUES (?, ?, ?, ?)",
                (chat_id, direction, content, msg_type)
            )
            await db.commit()

    # ── Xotira (yaxshilangan) ─────────────────────────────────
    async def save_memory(self, content: str, category: str = "general",
                          is_permanent: bool = False, importance: float = 0.5):
        expires_at = None if is_permanent else (
            datetime.now() + timedelta(days=MEMORY_DAYS)
        ).isoformat()

        async with aiosqlite.connect(self.path) as db:
            await db.execute(
                """INSERT INTO memories 
                   (content, category, is_permanent, importance_score, expires_at) 
                   VALUES (?, ?, ?, ?, ?)""",
                (content, category, int(is_permanent), importance, expires_at)
            )
            await db.commit()

    async def get_relevant_memories(self, query: str, limit: int = 8) -> list:
        words = [w.strip() for w in query.lower().split() if len(w.strip()) > 2]
        if not words:
            # Oxirgi esdaliklarni qaytar
            async with aiosqlite.connect(self.path) as db:
                cursor = await db.execute(
                    "SELECT content FROM memories WHERE expires_at IS NULL OR expires_at > ? ORDER BY importance_score DESC, created_at DESC LIMIT ?",
                    (datetime.now().isoformat(), limit)
                )
                rows = await cursor.fetchall()
                return [r[0] for r in rows]

        async with aiosqlite.connect(self.path) as db:
            conditions = " OR ".join(["LOWER(content) LIKE ?" for _ in words])
            params = [f"%{w}%" for w in words]
            params.append(datetime.now().isoformat())
            params.append(limit)

            cursor = await db.execute(
                f"""SELECT content FROM memories
                    WHERE ({conditions})
                    AND (expires_at IS NULL OR expires_at > ?)
                    ORDER BY importance_score DESC, created_at DESC
                    LIMIT ?""",
                params
            )
            rows = await cursor.fetchall()
            return [r[0] for r in rows]

    async def get_all_memories_count(self) -> dict:
        async with aiosqlite.connect(self.path) as db:
            c1 = await db.execute("SELECT COUNT(*) FROM memories")
            total = (await c1.fetchone())[0]
            c2 = await db.execute("SELECT COUNT(*) FROM memories WHERE is_permanent = 1")
            permanent = (await c2.fetchone())[0]
            c3 = await db.execute(
                "SELECT COUNT(*) FROM memories WHERE expires_at <= ?",
                ((datetime.now() + timedelta(days=7)).isoformat(),)
            )
            expiring = (await c3.fetchone())[0]
            return {"total": total, "permanent": permanent, "expiring_soon": expiring}

    # ── Suhbat xotirasi (kontekst) ────────────────────────────
    async def save_conversation_memory(self, user_msg: str, bot_msg: str, topic: str = "", summary: str = ""):
        async with aiosqlite.connect(self.path) as db:
            await db.execute(
                """INSERT INTO conversation_memory (user_message, bot_response, topic, summary)
                   VALUES (?, ?, ?, ?)""",
                (user_msg, bot_msg, topic, summary[:500])
            )
            await db.commit()

    async def get_conversation_history_by_topic(self, topic: str, limit: int = 5) -> list:
        async with aiosqlite.connect(self.path) as db:
            cursor = await db.execute(
                """SELECT user_message, bot_response, created_at
                   FROM conversation_memory
                   WHERE topic LIKE ? OR summary LIKE ?
                   ORDER BY created_at DESC LIMIT ?""",
                (f"%{topic}%", f"%{topic}%", limit)
            )
            rows = await cursor.fetchall()
            return [{"user": r[0], "bot": r[1], "date": r[2]} for r in rows]

    async def get_conversation_memory_context(self, query: str, limit: int = 3) -> str:
        """Qidiruv so'ziga mos suhbat xotirasini topish"""
        words = [w for w in query.lower().split() if len(w) > 3][:3]
        if not words:
            return ""

        async with aiosqlite.connect(self.path) as db:
            conditions = " OR ".join(["LOWER(user_message) LIKE ? OR LOWER(summary) LIKE ?" for _ in words])
            params = []
            for w in words:
                params.extend([f"%{w}%", f"%{w}%"])
            params.append(limit)

            cursor = await db.execute(
                f"""SELECT user_message, bot_response, created_at
                   FROM conversation_memory
                   WHERE {conditions}
                   ORDER BY created_at DESC LIMIT ?""",
                params
            )
            rows = await cursor.fetchall()
            
            if rows:
                result = ["📚 *Eslab qolingan suhbatlar:*\n"]
                for r in rows:
                    result.append(f"📅 {r[2][:10]}:")
                    result.append(f"  👤 {r[0][:100]}")
                    result.append(f"  🤖 {r[1][:100]}")
                    result.append("")
                return "\n".join(result)
            return ""

    # ── Suhbat tarixi (odatdagi) ─────────────────────────────
    async def save_conversation(self, role: str, content: str):
        async with aiosqlite.connect(self.path) as db:
            await db.execute(
                "INSERT INTO conversations (role, content) VALUES (?, ?)",
                (role, content)
            )
            # Faqat oxirgi 50 ta saqlash
            await db.execute(
                """DELETE FROM conversations WHERE id NOT IN (
                   SELECT id FROM conversations ORDER BY id DESC LIMIT 50)"""
            )
            await db.commit()

    async def get_conversation_history(self, limit: int = 10) -> list:
        async with aiosqlite.connect(self.path) as db:
            cursor = await db.execute(
                "SELECT role, content FROM conversations ORDER BY id DESC LIMIT ?",
                (limit,)
            )
            rows = await cursor.fetchall()
            return [{"role": r[0], "content": r[1]} for r in reversed(rows)]

    # ── Vazifalar ─────────────────────────────────────────────
    async def add_task(self, title: str, description: str = "", due_at=None) -> int:
        async with aiosqlite.connect(self.path) as db:
            cursor = await db.execute(
                "INSERT INTO tasks (title, description, due_at) VALUES (?, ?, ?)",
                (title, description, due_at)
            )
            await db.commit()
            return cursor.lastrowid

    async def get_tasks(self, status: str = "pending") -> list:
        async with aiosqlite.connect(self.path) as db:
            cursor = await db.execute(
                "SELECT id, title, description, due_at FROM tasks WHERE status = ? ORDER BY due_at ASC",
                (status,)
            )
            rows = await cursor.fetchall()
            return [{"id": r[0], "title": r[1], "desc": r[2], "due": r[3]} for r in rows]

    async def complete_task(self, task_id: int):
        async with aiosqlite.connect(self.path) as db:
            await db.execute(
                "UPDATE tasks SET status = 'done', updated_at = CURRENT_TIMESTAMP WHERE id = ?", (task_id,)
            )
            await db.commit()

    async def get_upcoming_reminders(self) -> list:
        deadline = (datetime.now() + timedelta(hours=24)).isoformat()
        async with aiosqlite.connect(self.path) as db:
            cursor = await db.execute(
                """SELECT id, title, due_at FROM tasks
                   WHERE status = 'pending' AND reminder_sent = 0
                   AND due_at IS NOT NULL AND due_at <= ?""",
                (deadline,)
            )
            rows = await cursor.fetchall()
            return [{"id": r[0], "title": r[1], "due": r[2]} for r in rows]

    async def mark_reminder_sent(self, task_id: int):
        async with aiosqlite.connect(self.path) as db:
            await db.execute(
                "UPDATE tasks SET reminder_sent = 1 WHERE id = ?", (task_id,)
            )
            await db.commit()

    # ── Zametka ───────────────────────────────────────────────
    async def add_note(self, content: str, category: str = "general", is_pinned: bool = False) -> int:
        async with aiosqlite.connect(self.path) as db:
            cursor = await db.execute(
                "INSERT INTO notes (content, category, is_pinned) VALUES (?, ?, ?)",
                (content, category, int(is_pinned))
            )
            await db.commit()
            return cursor.lastrowid

    async def get_notes(self, limit: int = 15) -> list:
        async with aiosqlite.connect(self.path) as db:
            cursor = await db.execute(
                "SELECT id, content, category, is_pinned FROM notes ORDER BY is_pinned DESC, id DESC LIMIT ?",
                (limit,)
            )
            rows = await cursor.fetchall()
            return [{"id": r[0], "content": r[1], "category": r[2], "pinned": r[3]} for r in rows]

    # ── Ehtiyot qismlar ───────────────────────────────────────
    async def add_spare_part(self, name: str, code: str, equipment_type: str,
                              expected_life_hours: float, notes: str = "") -> int:
        async with aiosqlite.connect(self.path) as db:
            cursor = await db.execute(
                """INSERT INTO spare_parts (part_name, part_code, equipment_type, expected_life_hours, notes)
                   VALUES (?, ?, ?, ?, ?)""",
                (name, code, equipment_type, expected_life_hours, notes)
            )
            await db.commit()
            return cursor.lastrowid

    async def get_spare_part_by_equipment(self, equipment_type: str) -> list:
        async with aiosqlite.connect(self.path) as db:
            cursor = await db.execute(
                """SELECT id, part_name, part_code, expected_life_hours, current_usage_hours, notes
                   FROM spare_parts WHERE equipment_type LIKE ?""",
                (f"%{equipment_type}%",)
            )
            rows = await cursor.fetchall()
            return [{"id": r[0], "name": r[1], "code": r[2], "life_hours": r[3], "usage_hours": r[4], "notes": r[5]} for r in rows]

    async def update_part_usage(self, part_id: int, additional_hours: float):
        async with aiosqlite.connect(self.path) as db:
            await db.execute(
                "UPDATE spare_parts SET current_usage_hours = current_usage_hours + ? WHERE id = ?",
                (additional_hours, part_id)
            )
            await db.commit()

    async def get_part_remaining_life(self, part_id: int) -> float:
        async with aiosqlite.connect(self.path) as db:
            cursor = await db.execute(
                "SELECT expected_life_hours, current_usage_hours FROM spare_parts WHERE id = ?",
                (part_id,)
            )
            row = await cursor.fetchone()
            if row:
                expected, current = row
                remaining = max(0, expected - current)
                return remaining
            return 0

    # ── Arizalar (zayavkalar) ─────────────────────────────────
    async def create_request(self, equipment_id: str, part_name: str, quantity: int, request_text: str) -> str:
        request_number = f"ZAY-{datetime.now().strftime('%Y%m%d')}-{equipment_id[:3]}"
        async with aiosqlite.connect(self.path) as db:
            cursor = await db.execute(
                """INSERT INTO requests (request_number, equipment_id, part_name, quantity, request_text)
                   VALUES (?, ?, ?, ?, ?)""",
                (request_number, equipment_id, part_name, quantity, request_text)
            )
            await db.commit()
            return request_number

    async def get_pending_requests(self) -> list:
        async with aiosqlite.connect(self.path) as db:
            cursor = await db.execute(
                "SELECT id, request_number, equipment_id, part_name, quantity, created_at FROM requests WHERE status = 'pending'"
            )
            rows = await cursor.fetchall()
            return [{"id": r[0], "number": r[1], "equipment": r[2], "part": r[3], "qty": r[4], "date": r[5]} for r in rows]

    # ── Metrikalar ────────────────────────────────────────────
    async def save_metric(self, name: str, value: str):
        async with aiosqlite.connect(self.path) as db:
            await db.execute(
                "INSERT INTO metrics (metric_name, metric_value) VALUES (?, ?)",
                (name, value)
            )
            await db.commit()

    async def get_metrics(self, name: str, days: int = 30) -> list:
        cutoff = (datetime.now() - timedelta(days=days)).isoformat()
        async with aiosqlite.connect(self.path) as db:
            cursor = await db.execute(
                "SELECT metric_value, recorded_at FROM metrics WHERE metric_name = ? AND recorded_at > ? ORDER BY recorded_at",
                (name, cutoff)
            )
            rows = await cursor.fetchall()
            return [{"value": r[0], "date": r[1]} for r in rows]

    # ── Statistika ────────────────────────────────────────────
    async def get_weekly_stats(self) -> dict:
        week_ago = (datetime.now() - timedelta(days=7)).isoformat()
        async with aiosqlite.connect(self.path) as db:
            c1 = await db.execute("SELECT COUNT(*) FROM messages WHERE created_at >= ?", (week_ago,))
            c2 = await db.execute("SELECT COUNT(*) FROM notes WHERE created_at >= ?", (week_ago,))
            c3 = await db.execute("SELECT COUNT(*) FROM tasks WHERE status='done' AND updated_at >= ?", (week_ago,))
            c4 = await db.execute("SELECT COUNT(*) FROM tasks WHERE status='pending'", )
            c5 = await db.execute("SELECT COUNT(*) FROM memories WHERE created_at >= ?", (week_ago,))
            return {
                "messages": (await c1.fetchone())[0],
                "notes":    (await c2.fetchone())[0],
                "done":     (await c3.fetchone())[0],
                "pending":  (await c4.fetchone())[0],
                "memories": (await c5.fetchone())[0],
            }

    async def get_problem_stats(self) -> dict:
        """Eng ko'p takrorlanadigan nosozliklar statistikasi"""
        async with aiosqlite.connect(self.path) as db:
            cursor = await db.execute("""
                SELECT content FROM messages WHERE type = 'text' AND direction = 'in'
            """)
            rows = await cursor.fetchall()
            
            problem_keywords = ['nasos', 'kompressor', 'konveyer', 'tegirmon', 'flotatsiya',
                                'vibratsiya', 'harorat', 'bosim', 'oqish', 'shovqin']
            stats = {kw: 0 for kw in problem_keywords}
            
            for row in rows:
                text = row[0].lower()
                for kw in problem_keywords:
                    if kw in text:
                        stats[kw] += 1
            
            return stats

    # ── Tozalash ──────────────────────────────────────────────
    async def cleanup(self) -> int:
        cutoff = (datetime.now() - timedelta(days=MEMORY_DAYS)).isoformat()
        async with aiosqlite.connect(self.path) as db:
            r1 = await db.execute(
                "DELETE FROM memories WHERE is_permanent = 0 AND expires_at < ?",
                (datetime.now().isoformat(),)
            )
            r2 = await db.execute(
                "DELETE FROM messages WHERE created_at < ?", (cutoff,)
            )
            await db.commit()
            return r1.rowcount + r2.rowcount