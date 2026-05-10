"""
PersonalTwin v2.0 — O'tkirbek ning raqamli egizagi
Suhbatlardan uslubni o'rganib, aynan o'sha kishi kabi gapiradi
"""

import os
import json
import re
import logging
import aiosqlite
from datetime import datetime
from groq import Groq

log = logging.getLogger(__name__)

DB_PATH    = os.getenv("DB_PATH", "ai_agent.db")
GROQ_MODEL = os.getenv("GROQ_MODEL", "llama3-70b-8192")
OWNER_NAME = os.getenv("OWNER_NAME", "O'tkirbek")
OWNER_JOB  = os.getenv("OWNER_JOB", "AGMK 3-MBF mexanigi")
OWNER_CITY = os.getenv("OWNER_CITY", "Olmaliq")


class PersonalTwin:
    def __init__(self):
        self.groq         = Groq(api_key=os.getenv("GROQ_API_KEY", ""))
        self._style_cache = None

    async def init_db(self):
        async with aiosqlite.connect(DB_PATH) as db:
            await db.executescript("""
                CREATE TABLE IF NOT EXISTS twin_samples (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    situation TEXT,
                    my_response TEXT,
                    language TEXT DEFAULT 'uz',
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                );
                CREATE TABLE IF NOT EXISTS twin_style (
                    id INTEGER PRIMARY KEY,
                    style_analysis TEXT,
                    keywords TEXT,
                    phrases TEXT,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                );
                CREATE TABLE IF NOT EXISTS twin_knowledge (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    topic TEXT,
                    content TEXT,
                    source TEXT DEFAULT 'manual',
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                );
            """)
            await db.commit()
            await self._seed_knowledge(db)

    async def _seed_knowledge(self, db):
        cur = await db.execute("SELECT COUNT(*) FROM twin_knowledge")
        row = await cur.fetchone()
        if row and row[0] > 0:
            return
        initial = [
            ("shaxs",   f"Men {OWNER_NAME}, {OWNER_JOB}. {OWNER_CITY}da yashayman."),
            ("kasb",    "Warman nasoslar, ABB/GMD dvigatellar, konveyerlar, flotatsiya bilan ishlayman."),
            ("ishxona", "AGMK 3-mis boyitish fabrikasida mexanik bo'lib ishlayman."),
            ("uslub",   "Qisqa va aniq gapiraman. Texnik savollarga professional javob beraman."),
            ("til",     "O'zbek va rus tillarida gaplashaman."),
        ]
        for topic, content in initial:
            await db.execute(
                "INSERT OR IGNORE INTO twin_knowledge (topic, content) VALUES (?, ?)",
                (topic, content))
        await db.commit()

    async def learn_from_message(self, msg: str, situation: str = ""):
        if not msg or len(msg) < 5:
            return
        lang = "ru" if self._is_russian(msg) else "uz"
        async with aiosqlite.connect(DB_PATH) as db:
            await db.execute(
                "INSERT INTO twin_samples (situation, my_response, language) VALUES (?, ?, ?)",
                (situation, msg, lang))
            await db.commit()

            cur = await db.execute("SELECT COUNT(*) FROM twin_samples")
            row = await cur.fetchone()
            total = row[0] if row else 0
            if total > 0 and total % 20 == 0:
                await self._update_style(db)

    async def _update_style(self, db):
        cur  = await db.execute(
            "SELECT my_response FROM twin_samples ORDER BY id DESC LIMIT 50")
        rows = await cur.fetchall()
        if not rows:
            return

        samples = "\n".join(f"- {r[0]}" for r in rows)
        prompt  = (
            f"Bu shaxsning so'nggi xabarlari:\n{samples}\n\n"
            "Yozish uslubini tahlil qil. FAQAT JSON:\n"
            '{"style":"uslub","keywords":["so\'z1"],"phrases":["ibora1"],"tone":"neytral"}'
        )
        try:
            resp = self.groq.chat.completions.create(
                model=GROQ_MODEL,
                messages=[{"role": "user", "content": prompt}],
                max_tokens=300, temperature=0.3)
            data = json.loads(re.sub(r'```json|```', '',
                                      resp.choices[0].message.content).strip())
            await db.execute("""
                INSERT OR REPLACE INTO twin_style
                (id, style_analysis, keywords, phrases, updated_at)
                VALUES (1, ?, ?, ?, CURRENT_TIMESTAMP)""",
                (data.get("style", ""),
                 json.dumps(data.get("keywords", []), ensure_ascii=False),
                 json.dumps(data.get("phrases", []), ensure_ascii=False)))
            await db.commit()
            self._style_cache = data
            log.info("✅ Twin uslubi yangilandi")
        except Exception as e:
            log.error(f"Uslub yangilash xatosi: {e}")

    async def generate_reply(self, incoming: str, sender_name: str = "") -> str:
        knowledge = await self._get_knowledge(incoming)
        style     = await self._get_style()
        samples   = await self._get_samples(incoming)
        lang      = "ru" if self._is_russian(incoming) else "uz"

        kn_str  = "\n".join(f"- {k}" for k in knowledge) if knowledge else ""
        sm_str  = "\n".join(f'- "{s}"' for s in samples[:5]) if samples else ""
        st_str  = style.get("style", "qisqa, aniq") if style else "qisqa, aniq"
        kw_str  = ", ".join(style.get("keywords", [])[:8]) if style else ""
        lang_i  = "O'zbek tilida yoz." if lang == "uz" else "Rus tilida yoz."

        system = (
            f"Sen {OWNER_NAME} — {OWNER_JOB}. Bu sening profilingdan kelayotgan xabar.\n\n"
            f"SHAXSIY MA'LUMOTLAR:\n{kn_str}\n\n"
            f"YOZISH USLUBIM: {st_str}\n"
            f"Xarakterli so'zlarim: {kw_str}\n\n"
            f"NAMUNALAR:\n{sm_str}\n\n"
            f"QOIDALAR: Aynan men kabi gapir. Qisqa va aniq. "
            f"Hech qachon 'AI' yoki 'bot' ekanligingni aytma. {lang_i}"
        )
        try:
            resp = self.groq.chat.completions.create(
                model=GROQ_MODEL,
                messages=[
                    {"role": "system", "content": system},
                    {"role": "user",   "content": f"{sender_name}: {incoming}"}],
                max_tokens=300, temperature=0.85)
            return resp.choices[0].message.content.strip()
        except Exception as e:
            log.error(f"Twin javob xatosi: {e}")
            return "Tushunarli. Keyinroq xabar beraman." if lang == "uz" else "Понял. Отпишу позже."

    async def add_knowledge(self, topic: str, content: str, source: str = "manual"):
        async with aiosqlite.connect(DB_PATH) as db:
            await db.execute(
                "INSERT INTO twin_knowledge (topic, content, source) VALUES (?, ?, ?)",
                (topic, content, source))
            await db.commit()

    async def get_stats(self) -> dict:
        async with aiosqlite.connect(DB_PATH) as db:
            c1 = await db.execute("SELECT COUNT(*) FROM twin_samples")
            r1 = await c1.fetchone()
            c2 = await db.execute("SELECT COUNT(*) FROM twin_knowledge")
            r2 = await c2.fetchone()
            c3 = await db.execute("SELECT updated_at FROM twin_style WHERE id=1")
            r3 = await c3.fetchone()
            samples   = r1[0] if r1 else 0
            knowledge = r2[0] if r2 else 0
            updated   = r3[0] if r3 else "Hali tahlil qilinmagan"
        return {"samples": samples, "knowledge": knowledge,
                "updated": updated, "ready": samples >= 10}

    async def _get_style(self) -> dict:
        if self._style_cache:
            return self._style_cache
        async with aiosqlite.connect(DB_PATH) as db:
            cur = await db.execute(
                "SELECT style_analysis, keywords, phrases FROM twin_style WHERE id=1")
            row = await cur.fetchone()
            if row:
                self._style_cache = {
                    "style":   row[0],
                    "keywords": json.loads(row[1] or "[]"),
                    "phrases":  json.loads(row[2] or "[]")}
                return self._style_cache
        return {}

    async def _get_knowledge(self, query: str) -> list:
        words = [w for w in query.lower().split() if len(w) > 2][:5]
        if not words:
            return []
        async with aiosqlite.connect(DB_PATH) as db:
            cond   = " OR ".join(["LOWER(content) LIKE ?" for _ in words])
            params = [f"%{w}%" for w in words]
            cur    = await db.execute(
                f"SELECT content FROM twin_knowledge WHERE {cond} LIMIT 5", params)
            rows   = await cur.fetchall()
            return [r[0] for r in rows]

    async def _get_samples(self, text: str) -> list:
        words = [w for w in text.lower().split() if len(w) > 3][:3]
        async with aiosqlite.connect(DB_PATH) as db:
            if not words:
                cur = await db.execute(
                    "SELECT my_response FROM twin_samples ORDER BY id DESC LIMIT 10")
            else:
                cond   = " OR ".join(["LOWER(my_response) LIKE ?" for _ in words])
                params = [f"%{w}%" for w in words]
                cur    = await db.execute(
                    f"SELECT my_response FROM twin_samples WHERE {cond} "
                    "ORDER BY id DESC LIMIT 8", params)
            rows = await cur.fetchall()
            return [r[0] for r in rows]

    @staticmethod
    def _is_russian(text: str) -> bool:
        ru = sum(1 for c in text if '\u0430' <= c <= '\u044f' or '\u0410' <= c <= '\u042f')
        return ru > len(text) * 0.3
