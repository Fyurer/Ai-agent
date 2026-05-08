"""
Database — SQLite (Railway da fayl sifatida)
"""

import aiosqlite
import os
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

                CREATE TABLE IF NOT EXISTS tasks (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    title TEXT,
                    description TEXT,
                    status TEXT DEFAULT 'pending',
                    due_at TIMESTAMP,
                    reminder_sent INTEGER DEFAULT 0,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
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

    # ── Xotira ───────────────────────────────────────────────
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
            return []

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

    # ── Suhbat tarixi ─────────────────────────────────────────
    async def save_conversation(self, role: str, content: str):
        async with aiosqlite.connect(self.path) as db:
            await db.execute(
                "INSERT INTO conversations (role, content) VALUES (?, ?)",
                (role, content)
            )
            # Faqat oxirgi 20 ta saqlash
            await db.execute(
                """DELETE FROM conversations WHERE id NOT IN (
                   SELECT id FROM conversations ORDER BY id DESC LIMIT 20)"""
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
                "UPDATE tasks SET status = 'done' WHERE id = ?", (task_id,)
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
