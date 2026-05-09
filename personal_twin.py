"""
PersonalTwin — O'tkirbek ning raqamli egizagi
Suhbatlardan uslubni o'rganib, aynan o'sha kishi kabi gapiradi
"""

import os
import json
import logging
import aiosqlite
from datetime import datetime
from groq import Groq

log = logging.getLogger(__name__)

DB_PATH      = os.getenv("DB_PATH", "ai_agent.db")
GROQ_MODEL   = os.getenv("GROQ_MODEL", "llama3-70b-8192")
OWNER_NAME   = os.getenv("OWNER_NAME", "O'tkirbek")
OWNER_ID     = int(os.getenv("OWNER_CHAT_ID", "0"))

# Shaxsiy ma'lumotlar — .env dan
OWNER_JOB    = os.getenv("OWNER_JOB", "AGMK 3-MBF mexanigi")
OWNER_CITY   = os.getenv("OWNER_CITY", "Olmaliq")
OWNER_STYLE  = os.getenv("OWNER_STYLE", "qisqa, aniq, do'stona")


class PersonalTwin:
    """
    Sizning raqamli egizagingiz.
    - Suhbatlardan uslubni o'rganadi
    - Aynan siz kabi javob beradi
    - Texnik savollarga mutaxassis sifatida javob beradi
    - O'zbek va rus tillarida gapiradi
    """

    def __init__(self):
        self.groq = Groq(api_key=os.getenv("GROQ_API_KEY", ""))
        self._style_cache = None
        self._style_updated = None

    # ── Database yaratish ─────────────────────────────────────
    async def init_db(self):
        async with aiosqlite.connect(DB_PATH) as db:
            await db.executescript("""
                -- O'tkirbek ning suhbat namunalari
                CREATE TABLE IF NOT EXISTS twin_samples (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    situation TEXT,
                    my_response TEXT,
                    context TEXT,
                    language TEXT DEFAULT 'uz',
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                );

                -- Uslub tahlili (AI tomonidan)
                CREATE TABLE IF NOT EXISTS twin_style (
                    id INTEGER PRIMARY KEY,
                    style_analysis TEXT,
                    keywords TEXT,
                    phrases TEXT,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                );

                -- Shaxsiy bilimlar bazasi
                CREATE TABLE IF NOT EXISTS twin_knowledge (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    topic TEXT,
                    content TEXT,
                    source TEXT DEFAULT 'manual',
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                );
            """)
            await db.commit()

            # Boshlang'ich bilimlarni qo'shish
            await self._seed_knowledge(db)

    async def _seed_knowledge(self, db):
        """Boshlang'ich shaxsiy ma'lumotlarni yuklash"""
        cursor = await db.execute("SELECT COUNT(*) FROM twin_knowledge")
        row    = await cursor.fetchone()
        if row[0] > 0:
            return  # Allaqo'shilgan

        initial = [
            ("shaxs", f"Men {OWNER_NAME}, {OWNER_JOB}. {OWNER_CITY}da yashayman.", "system"),
            ("kasb",  "Mexanik sifatida nasos, kompressor, konveyer, elektrodvigatel bilan ishlayman.", "system"),
            ("ishxona", "AGMK (Olmaliq Kon Metallurgiya Kombinati) 3-mis boyitish fabrikasida ishlayman.", "system"),
            ("texnik", "Warman nasoslar, GMD/ABB dvigatellari, flotatsiya mashinalari mutaxassisiman.", "system"),
            ("uslub",  "Qisqa va aniq gapiraman. Ortiqcha so'z ishlatmayman. Muammoni tezda hal qilaman.", "system"),
            ("til",    "O'zbek va rus tillarida gaplashaman. Savol qaysi tilda bo'lsa, shu tilda javob beraman.", "system"),
        ]

        for topic, content, source in initial:
            await db.execute(
                "INSERT OR IGNORE INTO twin_knowledge (topic, content, source) VALUES (?, ?, ?)",
                (topic, content, source)
            )
        await db.commit()

    # ── Suhbatdan o'rganish ───────────────────────────────────
    async def learn_from_message(self, my_message: str, situation: str = ""):
        """
        Siz har safar botga yozganingizda — uslubingizni o'rganadi.
        Bu funksiya handlers.py dan chaqiriladi.
        """
        if not my_message or len(my_message) < 5:
            return

        lang = "ru" if self._is_russian(my_message) else "uz"

        async with aiosqlite.connect(DB_PATH) as db:
            await db.execute(
                "INSERT INTO twin_samples (situation, my_response, language) VALUES (?, ?, ?)",
                (situation, my_message, lang)
            )
            await db.commit()

            # Har 20 ta yangi namunadan keyin uslubni yangilash
            count_cur = await db.execute("SELECT COUNT(*) FROM twin_samples")
            total = (await count_cur.fetchone())[0]
            if total % 20 == 0:
                await self._update_style_analysis(db)

    async def _update_style_analysis(self, db):
        """Suhbat namunalaridan uslubni tahlil qilish"""
        cursor  = await db.execute(
            "SELECT my_response FROM twin_samples ORDER BY id DESC LIMIT 50"
        )
        samples = await cursor.fetchall()
        if not samples:
            return

        samples_text = "\n".join([f"- {s[0]}" for s in samples])

        prompt = f"""Bu shaxsning so'nggi xabarlari:
{samples_text}

Ushbu xabarlar asosida shu shaxsning yozish uslubini tahlil qil:
1. Qanday so'zlar ko'p ishlatadi?
2. Jumlalar qisqa yoki uzunmi?
3. Do'stona yoki rasmiy?
4. Qanday iboralar xarakterli?
5. Emoji ishlatadiim?

JSON formatda qaytар:
{{"style": "uslub tavsifi", "keywords": ["so'z1","so'z2"], "phrases": ["ibora1","ibora2"], "tone": "do'stona/rasmiy/neytral"}}"""

        try:
            resp = self.groq.chat.completions.create(
                model=GROQ_MODEL,
                messages=[{"role": "user", "content": prompt}],
                max_tokens=300,
                temperature=0.3
            )
            analysis = resp.choices[0].message.content
            import re
            clean = re.sub(r'```json|```', '', analysis).strip()
            data  = json.loads(clean)

            await db.execute("""
                INSERT OR REPLACE INTO twin_style (id, style_analysis, keywords, phrases, updated_at)
                VALUES (1, ?, ?, ?, CURRENT_TIMESTAMP)
            """, (
                data.get("style", ""),
                json.dumps(data.get("keywords", []), ensure_ascii=False),
                json.dumps(data.get("phrases", []), ensure_ascii=False)
            ))
            await db.commit()
            self._style_cache   = data
            self._style_updated = datetime.now()
            log.info("✅ Twin uslubi yangilandi")
        except Exception as e:
            log.error(f"Uslub tahlil xatosi: {e}")

    # ── Javob yaratish (asosiy) ───────────────────────────────
    async def generate_reply(self, incoming_text: str, sender_name: str = "") -> str:
        """
        Sizning nomingizdan javob yaratish.
        incoming_text — kelgan xabar
        sender_name   — kim yozdi
        """
        # Shaxsiy bilimlar
        knowledge = await self._get_relevant_knowledge(incoming_text)

        # Uslub tahlili
        style = await self._get_style()

        # Suhbat namunalari
        samples = await self._get_similar_samples(incoming_text)

        # Til aniqlash
        lang = "ru" if self._is_russian(incoming_text) else "uz"

        system = self._build_system_prompt(style, knowledge, samples, lang)

        try:
            resp = self.groq.chat.completions.create(
                model=GROQ_MODEL,
                messages=[
                    {"role": "system", "content": system},
                    {"role": "user",   "content": f"{sender_name} yozdi: {incoming_text}"}
                ],
                max_tokens=300,
                temperature=0.85
            )
            reply = resp.choices[0].message.content.strip()
            return reply
        except Exception as e:
            log.error(f"Twin javob xatosi: {e}")
            return self._fallback_reply(lang)

    def _build_system_prompt(self, style: dict, knowledge: list,
                              samples: list, lang: str) -> str:
        """Tizim promptini qurish"""

        knowledge_str = "\n".join([f"- {k}" for k in knowledge]) if knowledge else ""
        samples_str   = "\n".join([f"- \"{s}\"" for s in samples[:5]]) if samples else ""
        style_str     = style.get("style", OWNER_STYLE) if style else OWNER_STYLE
        keywords      = ", ".join(style.get("keywords", [])[:10]) if style else ""
        phrases       = ", ".join(style.get("phrases", [])[:5]) if style else ""

        lang_instruction = (
            "Javobni o'zbek tilida yoz." if lang == "uz"
            else "Отвечай на русском языке."
        )

        return f"""Sen {OWNER_NAME} — {OWNER_JOB}. Bu SENING profilingdan kelayotgan xabar.

SHAXSIY MA'LUMOTLAR:
{knowledge_str}

YOZISH USLUBIM:
{style_str}
Xarakterli so'zlarim: {keywords}
Sevimli iboralarim: {phrases}

NAMUNALAR (avval shunday yozganman):
{samples_str}

QOIDALAR:
1. Aynan men kabi gapir — xuddi shu odam yozayotgandek
2. Qisqa va aniq — ortiqcha gap yozma
3. Texnik savollarga mutaxassis sifatida javob ber
4. Agar bilmasam — "Keyin aniqlayman" de, ixtiro qilma
5. Hech qachon "AI" yoki "bot" ekanligingni aytma
6. {lang_instruction}
7. Emoji — faqat men ishlatsam ishlat"""

    # ── Yordamchi metodlar ────────────────────────────────────
    async def _get_style(self) -> dict:
        """Uslub tahlilini olish (cache bilan)"""
        if self._style_cache:
            return self._style_cache

        async with aiosqlite.connect(DB_PATH) as db:
            cursor = await db.execute(
                "SELECT style_analysis, keywords, phrases FROM twin_style WHERE id=1"
            )
            row = await cursor.fetchone()
            if row:
                self._style_cache = {
                    "style":    row[0],
                    "keywords": json.loads(row[1] or "[]"),
                    "phrases":  json.loads(row[2] or "[]")
                }
                return self._style_cache
        return {}

    async def _get_relevant_knowledge(self, query: str) -> list:
        """Tegishli bilimlarni qidirish"""
        words = [w for w in query.lower().split() if len(w) > 2]
        if not words:
            return []

        async with aiosqlite.connect(DB_PATH) as db:
            conditions = " OR ".join(["LOWER(content) LIKE ?" for _ in words])
            params     = [f"%{w}%" for w in words[:5]]
            cursor     = await db.execute(
                f"SELECT content FROM twin_knowledge WHERE {conditions} LIMIT 5",
                params
            )
            rows = await cursor.fetchall()
            return [r[0] for r in rows]

    async def _get_similar_samples(self, text: str) -> list:
        """O'xshash vaziyatdagi javoblarni qidirish"""
        words = [w for w in text.lower().split() if len(w) > 3][:3]
        if not words:
            # Oxirgi namunalar
            async with aiosqlite.connect(DB_PATH) as db:
                cursor = await db.execute(
                    "SELECT my_response FROM twin_samples ORDER BY id DESC LIMIT 10"
                )
                rows = await cursor.fetchall()
                return [r[0] for r in rows]

        async with aiosqlite.connect(DB_PATH) as db:
            conditions = " OR ".join(["LOWER(my_response) LIKE ?" for _ in words])
            params     = [f"%{w}%" for w in words]
            cursor     = await db.execute(
                f"SELECT my_response FROM twin_samples WHERE {conditions} "
                f"ORDER BY id DESC LIMIT 8",
                params
            )
            rows = await cursor.fetchall()
            return [r[0] for r in rows]

    async def add_knowledge(self, topic: str, content: str, source: str = "manual"):
        """Bilim bazasiga qo'lda qo'shish"""
        async with aiosqlite.connect(DB_PATH) as db:
            await db.execute(
                "INSERT INTO twin_knowledge (topic, content, source) VALUES (?, ?, ?)",
                (topic, content, source)
            )
            await db.commit()

    async def get_stats(self) -> dict:
        """Statistika"""
        async with aiosqlite.connect(DB_PATH) as db:
            c1 = await db.execute("SELECT COUNT(*) FROM twin_samples")
            c2 = await db.execute("SELECT COUNT(*) FROM twin_knowledge")
            c3 = await db.execute(
                "SELECT updated_at FROM twin_style WHERE id=1"
            )
            samples   = (await c1.fetchone())[0]
            knowledge = (await c2.fetchone())[0]
            row3      = await c3.fetchone()
            updated   = row3[0] if row3 else "Hali tahlil qilinmagan"

        return {
            "samples":   samples,
            "knowledge": knowledge,
            "updated":   updated,
            "ready":     samples >= 10
        }

    @staticmethod
    def _is_russian(text: str) -> bool:
        cyrillic_ru = sum(1 for c in text if '\u0430' <= c <= '\u044f' or '\u0410' <= c <= '\u042f')
        return cyrillic_ru > len(text) * 0.3

    @staticmethod
    def _fallback_reply(lang: str) -> str:
        if lang == "ru":
            return "Хорошо, понял. Дам знать позже."
        return "Tushunarli. Keyinroq xabar beraman."
