"""
Knowledge Base — MBF-3 Bilim Bazasi
AGMK 3-mis boyitish fabrika uchun maxsus texnik ma'lumotlar:
- Slurry nasoslar (Warman, GIW, KSB)
- GMD (Gearless Mill Drive) — ABB va Siemens
- Flotatsiya mashinalari
- Reagentlar tizimi
- Konveyer tizimi
- GOST va xalqaro standartlar

Arxitektura: SQLite + to'liq matn qidiruvi (FTS5)
"""

import os
import re
import logging
import aiosqlite
from datetime import datetime
from groq import Groq

log = logging.getLogger(__name__)
DB_PATH    = os.getenv("DB_PATH", "ai_agent.db")
GROQ_MODEL = os.getenv("GROQ_MODEL", "llama3-70b-8192")


# ═══════════════════════════════════════════════════════════════
#  ICHKI BILIM BAZASI — MBF-3 texnik ma'lumotlar
#  (To'liq PDF yuklamasdan oldin ishlaydigan bazaviy versiya)
# ═══════════════════════════════════════════════════════════════

MBF3_KNOWLEDGE = [

    # ── SLURRY NASOSLAR ──────────────────────────────────────
    {
        "category": "slurry_pump",
        "title": "Warman AH seriyali slurry nasos — umumiy",
        "content": """Warman AH (Horizontal) seriya — pulpa (slurry) transporti uchun eng keng tarqalgan.
MBF-3 da ishlatiladi: 6/4 AH, 8/6 AH, 10/8 AH, 12/10 AH modellar.
Materiallari: A05 (yumshoq po'lat), R55 (rezina futlama), Hi-Chrome (qattiq qotishma).
Kaviatsiya NPSH: har model uchun pasport bo'yicha.
Muhim: slurry zichligi 1.2–1.6 g/cm³, pH 4–12 uchun hisoblangan.
Impeller almashtirish: har 500–1500 soatda (abrazivlik ga qarab).
Moy: Shell Gadus S2 V220 2 (podshipnik uyi).
Tebranish norma: ≤4.5 mm/s RMS (ISO 10816-1).
GOST 6134-2007 — dinamik nasoslar.""",
        "tags": "warman nasos slurry pulpa mis boyitish"
    },
    {
        "category": "slurry_pump",
        "title": "Slurry nasos kaviatsiya — sabab va yechim",
        "content": """Kaviatsiya belgisi: keskin shovqin (shag'al ovozi), tebranish oshishi, unumdorlik pasayishi.
Sabablari (MBF-3 uchun tipik):
1. NPSH mavjud < NPSH talab — kirish bosimi yetarli emas
2. Sump (hovuz) sathi past — sensor tekshiring (level transmitter)
3. Kirish trubasi tiqilgan — to'rni tozalang
4. Ishchi tezlik haddan tashqari — VFD ni kamaytiring
5. Pulpa zichligi loyiha qiymatidan oshib ketgan — texnolog bilan kelishing.
Yechim: kirish bosimini oshiring (sump sathini ko'taring), tezlikni kamaytiring,
kirish truba diametrini tekshiring (≥ chiqish truba diametridan 1 pog'ona katta bo'lishi kerak).
Standart: GOST 6134-2007 §8.2.""",
        "tags": "kaviatsiya nasos slurry NPSH sump"
    },
    {
        "category": "slurry_pump",
        "title": "KSB WARMAN — muhrlash tizimi",
        "content": """Muhrlash turlari slurry nasoslarda:
1. Packing (sal'nik to'ldiruvchi): eng oddiy, suv sarflanadi (water flush 3–8 l/min).
   Siqish: nafas olmasi uchun ozgina sizib turishi kerak (3–5 tomchi/min normal).
2. Mechanical seal (mexanik muhr): tozaroq, ammo abrazivda tez yeyiladi.
   Flesh suv bosimi: ≥ pulpa bosimi + 0.1 bar.
3. Expeller (dinamik muhr): suvsiz, impeller yordamida — faqat to'liq yuk bilan ishlaydi.
Muhrlash ishlamayotgan belgilar: katta oqish, podshipnik tezroq qizishi.
Almashtirish oralig'i: sal'nik to'ldiruvchi — 2000–3000 soat.""",
        "tags": "muhr sal'nik mexanik seal nasos"
    },

    # ── GMD — GEARLESS MILL DRIVE ─────────────────────────────
    {
        "category": "GMD",
        "title": "GMD (Gearless Mill Drive) — asosiy tushuncha",
        "content": """GMD — dişlisiz (gearless) tegirmon drayveri. ABB va Siemens ishlab chiqaradi.
AGMK MBF-3 da SAG/AG tegirmonlar uchun ishlatiladi.
Prinsipi: tegirmon baraban o'zi — rotor bo'ladi. Stator tashqi tomondan o'rnatilgan.
Ustunliklari: gear yoki pinion yo'q — mexanik yeyilish kamayadi, FIK yuqori (~98%).
Kuchlanish: 3.3–11 kV (ABB модели бўйича).
Quvvat: 5 MW dan 28 MW gacha.
Sovutish: statorni havo bilan sovutish (ACU — Air Cooling Unit).
Kritik parametrlar: stator havo oralig'i (air gap) — har 6 oyda o'lchash.
Harorat monitoring: PT100 datchiklar stator chulg'amida (limit: 130°C — F class izolyatsiya).""",
        "tags": "GMD gearless mill drive ABB tegirmon SAG"
    },
    {
        "category": "GMD",
        "title": "ABB GMD — xavfsizlik va blokirovka",
        "content": """GMD xavfsizlik tizimlari (ABB ACS6000/ACS5000):
1. Creep drive (sürünme rejimi): texnik ko'rik uchun sekin aylantirish (0.5 RPM).
   FAQAT mexanik ruxsat bilan ishlatish!
2. Inching mode: qisqa impuls bilan burish.
3. Baraban bloklash: mexanik pim (pin) kiritiladi — ta'mirlash vaqtida.
   Pim kiritilmasdan elektr ta'mirlash MUMKIN EMAS.
4. Stator havo oralig'i (air gap) tekshirish: min 10 mm (ishlab chiqaruvchi ko'rsatmasiga qarang).
   Agar air gap kamaysa — stator rotor bilan tegadi (AVARIA!).
Lock-out/Tag-out (LOTO): 3 kalit — mexanik, elektr, texnolog.
Harorat alarmasi: 120°C — diqqat, 130°C — favqulodda to'xtatish.""",
        "tags": "GMD blokirovka xavfsizlik ABB creep drive LOTO"
    },
    {
        "category": "GMD",
        "title": "GMD tebranish diagnostikasi",
        "content": """GMD rotoridagi nomuvozanat (unbalance) tebranish hosil qiladi.
Tashxis: akselerometr o'lchashlar + FFT spektr tahlili.
Asosiy chastotalar:
- 1× RPM — statik nomuvozanat (muvozanatlash kerak)
- 2× RPM — dinamik nomuvozanat
- Yuqori chastotalar — elektromagnit ta'sir yoki air gap muammosi.
Tebranish limiti (ISO 10816-3): A zonasi ≤2.3 mm/s, C zonasi >7.1 mm/s (to'xtatish).
Rotor tozalagandan keyin muvozanatlash: ISO 1940-1 G6.3 sinfida.
Elektr tashxis: partial discharge (PD) monitoring — stator chulg'am holatini kuzatish.""",
        "tags": "GMD tebranish vibratsiya diagnostika unbalance FFT"
    },

    # ── TEGIRMONLAR ───────────────────────────────────────────
    {
        "category": "mill",
        "title": "SAG/AG tegirmon — liner (futlama) almashtirish",
        "content": """Liner (futlama) — tegirmon barabanining ichki himoya qoplama.
Material: yuqori marganetsli po'lat (Mn13Cr2) yoki kompozit.
Almashtirish oralig'i: MBF-3 uchun 6–18 oy (mineralning abrazivligiga qarab).
Qalinlik nazorat: ultrasonik o'lchash — minimal qalinlik 30–40 mm (pasport bo'yicha).
Almashtirish tartibi:
1. Tegirmonni to'xtatish, sovutish (≥2 soat)
2. Barrelni bloklash (GMD pin kiritish)
3. Kirish shlyuzi orqali kirish — faqat ikki kishi
4. Eski linerni demontaj (liner handler mashina)
5. Yangi linerni o'rnatish, moment bilan (pasport torque ga qarab)
Xavf: tegirmon ichida kislorod yetarli emas — gaz tahlili (O2 ≥ 19.5%) kerak.
Standart: MSHA (Mining Safety) va OHSAS 18001.""",
        "tags": "liner futlama tegirmon almashtirish SAG AG"
    },
    {
        "category": "mill",
        "title": "Tegirmon moy tizimi — TROMMEL va yog' stansiyasi",
        "content": """Tegirmon trunnion podshipniklari uchun moy tizimi:
Moy markasi: ISO VG 320 yoki ISO VG 460 (pasport bo'yicha, odatda Shell Omala S2 G 320).
Moy bosimi: 0.15–0.35 bar (podshipnikda).
Jacking pump (ko'taruvchi nasos): ishga tushirish va to'xtatishda podshipnikni yuqori bosimda yog'laydi.
Oqim: 50–200 l/min (quvvat ga qarab).
Filtr: beta 10 ≥ 200 (10 mikron).
Moy harorati: 45–55°C optimal (sovutgich orqali nazorat).
Alarmalar: bosim past → darhol tegirmon to'xtaydi.
Moy almashtirish: yiliga 1 marta (laboratoriya tahlildan keyin).
GOST 17216 — moy tozaligi sinfi.""",
        "tags": "tegirmon moy trunnion podshipnik yog' stansiya jacking"
    },

    # ── FLOTATSIYA ────────────────────────────────────────────
    {
        "category": "flotation",
        "title": "Flotatsiya mashinalari — MBF-3 uchun",
        "content": """Flotatsiya — mis minerallarini boyitishning asosiy usuli.
MBF-3 da: Outotec (Metso) va FLSmidth flotatsiya mashinalar.
Hujayra hajmi: 50–300 m³.
Asosiy mexanik qismlar:
1. Rotor (impeller) — pulpani aralashtiradi, havo disperslashtiradi.
   Almashtirish: 6000–12000 soat (po'liuretan yoki qattiq rezina).
2. Stator (diffuser) — rotor atrofida joylashgan.
3. Havo trubasi — kompressor dan havo keladi.
4. Ko'pik toshib o'tuvchi qutular (launder) — boyitilgan minerallar.
Reagentlar (MBF-3): ksantogenat (collector), ko'pirtiruvchi (MIBC), sulfidlovchi.
Pulpa pH: flotatsiyada 9–11 (ohak bilan boshqariladi).
Tebranish norma: ≤4.5 mm/s.""",
        "tags": "flotatsiya Outotec FLSmidth impeller rotor mis boyitish"
    },
    {
        "category": "flotation",
        "title": "Flotatsiya reagentlari — xavfsizlik",
        "content": """MBF-3 da ishlatiladigan reagentlar va xavflari:
1. Ksantogenat (Potassium Amyl Xanthate — PAX):
   Xavf: suv bilan reaksiyada CS2 (uglerод disulfid) — zaharli gaz!
   Saqlash: quruq, issiqdan uzoq, yopiq idishda.
   PPE: respirator A1/P2, rezina qo'lqop, ko'zoynak.
2. MIBC (ko'pirtiruvchi): yonuvchi, bug'lanadi.
   PPE: respirator, yong'inga chidamli kiyim.
3. Ohak suspenziyasi (Ca(OH)₂):
   Teriga: kislota kabi ta'sir qiladi, darhol suvda yuvish.
   Ko'zga tushsa: 20 daqiqa yuvish, darhol tibbiy yordam.
4. Kupur sulfat (CuSO4): atrof-muhit uchun toksik.
Barcha reagentlar uchun MSDS (Material Safety Data Sheet) sexda bo'lishi shart!
GOST 12.1.007 — kimyoviy moddalar bilan ishlash.""",
        "tags": "reagent ksantogenat MIBC ohak xavfsizlik MSDS flotatsiya"
    },

    # ── KONVEYERLAR ───────────────────────────────────────────
    {
        "category": "conveyor",
        "title": "Konveyer lenta — MBF-3 tipik muammolar",
        "content": """MBF-3 konveyer lenta tizimlari (kontsentrát va rudani tashish):
Lenta kengligi: 800–1200 mm (MBF-3 uchun tipik).
Tezlik: 1.5–3.5 m/s.
Lenta materiali: EP/NN (polimer to'qima), kimyoviy muhitga chidamli.
Asosiy muammolar:
1. Lenta chetga chiqishi: rolik noto'g'ri joylashgan → lenta tuzatuvchi rolikni sozlang.
   Tekshirish: yuklangan va yuklansiz holatda alohida.
2. Lenta sirpanishi: taranglik yetarli emas → vintli tortuvchini social.
   Formulа: taranglik F ≥ P/(μ), bu yerda P — kuch, μ — ishqalanish koeffitsienti 0.35–0.45.
3. Rolik ishlamaяпти: yog'lash interval o'tib ketgan (yog'lash: har 500 soatda LGMT2).
4. Lenta yirtilishi: tosh yoki qattiq jism — joriy ta'mirlash materiallari (lenta yamoq).
GOST 22645 — konveyer lenta.""",
        "tags": "konveyer lenta rolik taranglik sirpanish LGMT2"
    },

    # ── GOST VA STANDARTLAR ───────────────────────────────────
    {
        "category": "standards",
        "title": "MBF-3 uchun asosiy GOST standartlari ro'yxati",
        "content": """Mexanik texnik xizmat uchun asosiy standartlar:
GOST 6134-2007 — Dinamik nasoslar, texnik talablar.
GOST 17216-2001 — Moy tozaligi sinflari.
GOST 22645 — Konveyer lentalari.
GOST 18855-1994 — Podshipniklar, ISO 281 analog.
GOST 12.0.004 — Xavfsizlik yo'riqnomasi va instruktaj.
GOST 12.1.007 — Kimyoviy moddalar xavfliligi sinfi.
GOST 12.4.011 — Shaxsiy himoya vositalari (PPE).
GOST ISO 10816-1 — Mashina tebranishi o'lchash.
GOST ISO 13373-1 — Vibratsiya monitoring.
ISO 45001:2018 — Ish xavfsizligi menejment tizimi (OHSAS 18001 o'rnini bosdi).
ISO 9001:2015 — Sifat menejment tizimi.
ISO 55001 — Aktiv menejment (maintenance management).
MSHA 30 CFR Part 56/57 — Kon xavfsizligi qoidalari.""",
        "tags": "GOST ISO standart xavfsizlik tebranish podshipnik nasos"
    },

    # ── PREDICTIVE MAINTENANCE ────────────────────────────────
    {
        "category": "predictive",
        "title": "Oldindan ta'mirlash (PdM) — MBF-3 strategiyasi",
        "content": """Predictive Maintenance (PdM) — avariya bo'lmasdan oldin ta'mirlash.
MBF-3 uchun monitoring usullari:
1. Vibratsiya tahlili (VA): akselerometr, har smena.
   Asosiy chastotalar: BPFO, BPFI, BSF, FTF (podshipnik defekt chastotalari).
2. Termal kamera (infraqizil): podshipnik, elektr ulanmalar, qisqa tutashuv.
3. Moy tahlili: har 3 oyda laboratoriyaga (Fe, Cu, Cr, Si miqdori → yeyilish haqida xabar beradi).
4. Ultrasonik (UT): lenta qalinligi, liner qalinligi, truba devori.
5. Motor Current Signature Analysis (MCSA): elektr motor nosozliklarini tokladan aniqlash.
Kalit ko'rsatkichlar (KPI):
- MTBF (Mean Time Between Failures) > 4000 soat — maqsad.
- MTTR (Mean Time To Repair) < 4 soat — maqsad.
- OEE (Overall Equipment Effectiveness) > 85%.""",
        "tags": "predictive maintenance PdM vibratsiya termal moy tahlil MTBF OEE"
    },

    # ── DIGITAL TWIN ─────────────────────────────────────────
    {
        "category": "digital_twin",
        "title": "Digital Twin (Raqamli Egizak) — tushuncha va foyda",
        "content": """Digital Twin — real uskunaning virtual raqamli nusxasi.
MBF-3 kontekstida foydalanish:
1. Real vaqtda monitoring: sensor ma'lumotlari → virtual model → anomaliya aniqlash.
2. "What-if" simulatsiya: ta'mirlash oldidan oqibatni modellashtirish.
3. Qolgan resurs prognozi (RUL — Remaining Useful Life).
4. Optimal ish parametrlarini hisoblash (throughput, energy efficiency).
O'tkirbek uchun amaliy foyda:
- Nasos avariyasini 24–48 soat oldin prognoz qilish.
- Liner almashtirish muddatini aniq belgilash (ortiqcha erta almashtirish xarajatlari kamaytirish).
- Smena menejerlariga real-time hisobot.
Texnologiyalar: IoT (OPC-UA protokoli), cloud (AWS/Azure IoT), ML modellari (LSTM, Random Forest).
AGMK da mavjud: ABB Ability, Rockwell FactoryTalk, Siemens MindSphere.""",
        "tags": "digital twin raqamli egizak IoT monitoring RUL prognoz"
    },
]


class KnowledgeBase:
    """MBF-3 texnik bilim bazasi — SQLite FTS5 qidiruv"""

    def __init__(self):
        self.db_path = DB_PATH
        self.groq    = Groq(api_key=os.getenv("GROQ_API_KEY"))
        self._loaded = False

    async def init(self):
        """Jadval va boshlang'ich ma'lumotlarni yaratish"""
        async with aiosqlite.connect(self.db_path) as db:
            # FTS5 virtual jadval — to'liq matn qidiruvi
            await db.executescript("""
                CREATE TABLE IF NOT EXISTS kb_documents (
                    id       INTEGER PRIMARY KEY AUTOINCREMENT,
                    category TEXT,
                    title    TEXT,
                    content  TEXT,
                    tags     TEXT,
                    source   TEXT DEFAULT 'internal',
                    added_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                );

                CREATE VIRTUAL TABLE IF NOT EXISTS kb_fts
                USING fts5(
                    title, content, tags,
                    content='kb_documents',
                    content_rowid='id',
                    tokenize='unicode61'
                );

                CREATE TRIGGER IF NOT EXISTS kb_ai
                AFTER INSERT ON kb_documents BEGIN
                    INSERT INTO kb_fts(rowid, title, content, tags)
                    VALUES (new.id, new.title, new.content, new.tags);
                END;
            """)
            await db.commit()

            # Boshlang'ich ma'lumotlar yuklanganmi tekshirish
            cursor = await db.execute("SELECT COUNT(*) FROM kb_documents WHERE source='internal'")
            count = (await cursor.fetchone())[0]

            if count == 0:
                await self._seed_internal(db)
                log.info(f"✅ KnowledgeBase: {len(MBF3_KNOWLEDGE)} ta hujjat yuklandi")
            else:
                log.info(f"✅ KnowledgeBase: {count} ta hujjat mavjud")

        self._loaded = True

    async def _seed_internal(self, db):
        """Ichki bilim bazasini to'ldirish"""
        for doc in MBF3_KNOWLEDGE:
            await db.execute(
                "INSERT INTO kb_documents (category, title, content, tags, source) VALUES (?,?,?,?,?)",
                (doc["category"], doc["title"], doc["content"], doc["tags"], "internal")
            )
        await db.commit()

    async def search(self, query: str, limit: int = 4) -> list:
        """To'liq matn qidiruvi"""
        if not self._loaded:
            await self.init()
        try:
            async with aiosqlite.connect(self.db_path) as db:
                # FTS5 qidiruvi
                clean_q = re.sub(r'[^\w\s]', ' ', query)
                words   = [w for w in clean_q.split() if len(w) > 2]
                if not words:
                    return []

                fts_query = " OR ".join(words[:5])
                cursor = await db.execute(
                    """SELECT d.title, d.content, d.category
                       FROM kb_fts f
                       JOIN kb_documents d ON f.rowid = d.id
                       WHERE kb_fts MATCH ?
                       ORDER BY rank
                       LIMIT ?""",
                    (fts_query, limit)
                )
                rows = await cursor.fetchall()
                return [{"title": r[0], "content": r[1], "category": r[2]} for r in rows]
        except Exception as e:
            log.error(f"KB qidiruv xatosi: {e}")
            return await self._fallback_search(query, limit)

    async def _fallback_search(self, query: str, limit: int) -> list:
        """FTS ishlamasa — oddiy LIKE qidiruv"""
        try:
            async with aiosqlite.connect(self.db_path) as db:
                words = query.lower().split()[:3]
                conds = " OR ".join(["LOWER(content) LIKE ? OR LOWER(tags) LIKE ?" for _ in words])
                params = []
                for w in words:
                    params.extend([f"%{w}%", f"%{w}%"])
                cursor = await db.execute(
                    f"SELECT title, content, category FROM kb_documents WHERE {conds} LIMIT ?",
                    params + [limit]
                )
                rows = await cursor.fetchall()
                return [{"title": r[0], "content": r[1], "category": r[2]} for r in rows]
        except Exception as e:
            log.error(f"Fallback qidiruv xatosi: {e}")
            return []

    async def add_document(self, title: str, content: str,
                            category: str = "custom",
                            tags: str = "",
                            source: str = "user") -> int:
        """Yangi hujjat qo'shish (foydalanuvchi yuklaydigan PDF kontenti uchun)"""
        async with aiosqlite.connect(self.db_path) as db:
            cursor = await db.execute(
                "INSERT INTO kb_documents (category, title, content, tags, source) VALUES (?,?,?,?,?)",
                (category, title, content, tags, source)
            )
            await db.commit()
            return cursor.lastrowid

    async def get_rag_context(self, query: str) -> str:
        """RAG (Retrieval Augmented Generation) uchun kontekst"""
        docs = await self.search(query, limit=3)
        if not docs:
            return ""
        parts = []
        for d in docs:
            parts.append(f"[{d['category'].upper()}] {d['title']}:\n{d['content'][:500]}")
        return "\n\n---\n\n".join(parts)

    async def answer_with_rag(self, question: str) -> str:
        """Savol → KB dan qidirish → AI bilan javob"""
        context = await self.get_rag_context(question)

        if not context:
            return None  # KB da ma'lumot yo'q, oddiy chat ishlatilsin

        system = """Sen AGMK MBF-3 texnik ekspertisan.
Faqat taqdim etilgan texnik bilim bazasidan foydalanib javob ber.
O'zbek tilida qisqa va aniq javob ber. Formulalar va standart raqamlarini ko'rsat."""

        prompt = f"""Texnik bilim bazasidan topilgan ma'lumot:
{context}

Savol: {question}

Faqat yuqoridagi ma'lumot asosida javob ber. Agar javob bilim bazasida yo'q bo'lsa, aniq ayt."""

        try:
            resp = self.groq.chat.completions.create(
                model=GROQ_MODEL,
                messages=[
                    {"role": "system", "content": system},
                    {"role": "user", "content": prompt}
                ],
                max_tokens=800,
                temperature=0.2
            )
            answer = resp.choices[0].message.content
            return f"📚 *MBF-3 Bilim Bazasi:*\n\n{answer}"
        except Exception as e:
            return f"❌ RAG javob xatosi: {e}"

    async def list_categories(self) -> dict:
        """Kategoriyalar va hujjatlar soni"""
        async with aiosqlite.connect(self.db_path) as db:
            cursor = await db.execute(
                "SELECT category, COUNT(*) FROM kb_documents GROUP BY category"
            )
            rows = await cursor.fetchall()
            return {r[0]: r[1] for r in rows}

    async def get_all_titles(self) -> list:
        """Barcha sarlavhalar ro'yxati"""
        async with aiosqlite.connect(self.db_path) as db:
            cursor = await db.execute(
                "SELECT id, title, category FROM kb_documents ORDER BY category, id"
            )
            rows = await cursor.fetchall()
            return [{"id": r[0], "title": r[1], "category": r[2]} for r in rows]
