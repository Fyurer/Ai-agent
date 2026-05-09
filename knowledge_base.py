"""
MBF-3 Knowledge Base — Maxsus bilimlar bazasi
AGMK 3-mis boyitish fabrikasi uchun:
- GMD (Gearless Mill Drive) / ABB uskunalari
- Slurry nasoslar (Warman, KSB, Metso)
- SAG/AG/Ball tegirmonlari
- Flotatsiya mashinalari (Outotec, Metso)
- Konchilik texnikasi terminologiyasi
"""

import os
import logging
from groq import Groq

log = logging.getLogger(__name__)
GROQ_MODEL = os.getenv("GROQ_MODEL", "llama3-70b-8192")

# ── GMD (Gearless Mill Drive) ma'lumotlar bazasi ──────────────
GMD_KNOWLEDGE = {
    "umumiy": """
GMD (Gearless Mill Drive) — dişlisiz tegirmon drayveri.
ABB ishlab chiqarishi. AGMK SAG va Ball tegirmonlarida qo'llaniladi.

Asosiy qismlar:
- Rotor (tegirmon tanasiga o'rnatiladi — tashqi rotor)
- Stator (stasionar, tegirmon atrofida)
- Cycloconverter (chastota konverteri)
- Transformer (xos kuchlanish)
- ABB MV-yurgatgich qo'zg'atish tizimi

Afzalliklari vs an'anaviy:
- Reduktorsiz (dişlisiz) → tebranish kam
- Yuqori samaradorlik (≥97%)
- Sekin ishga tushirish (torque control)
- Elektronik tormozlash imkoni
""",
    "texnik_parametrlar": """
Tipik GMD parametrlari (SAG tegirmon):
- Quvvat: 10-30 MW
- Kuchlanish: 3-13.8 kV
- Chastota: 0-12 Hz (tegirmon RPM ga qarab)
- Samaradorlik: ≥97%
- Sovutish: havo yoki suv-havo

Muhim o'lchov parametrlari:
- Stator harorati: <130°C (F sinfi izolyatsiya)
- Havo tirmig'i harorati: <85°C
- Tebranish stator: <2.5 mm/s
- Air gap (havo oralig'i): 10-20 mm (nominal)
""",
    "nosozliklar": """
GMD tez-tez uchraydigan muammolar:

1. 🔴 Air gap (havo oralig'i) nomuvofiqliği
   Belgi: tebranish ortadi, g'alati shovqin
   Sabab: tegirmon tanasi deformatsiyasi, montaj xatosi
   Chorа: CMM o'lchash, shimlar bilan tuzatish

2. 🔴 Stator izolyatsiya muammosi
   Belgi: IR test past (< 100 MΩ), qisqa tutashuv
   Sabab: namlik, mexanik shikast, qizib ketish
   Chorа: izolyatsiya quritish, seksiya almashtirish

3. 🟡 Sovutish tizimi nosozligi
   Belgi: harorat sensori alarm
   Sabab: filtr tiqilgan, ventilyator ishlamayapti
   Chorа: filtr tozalash, ventilyator tekshirish

4. 🟡 Cycloconverter alarmlari
   Belgi: ABB AC800 da fault kodi
   Sabab: thyristor nosozligi, signalizatsiya muammosi
   Chorа: ABB texnik manual bo'yicha fault kod tahlili

5. 🟢 Sensor kalibrovkasi
   Belgi: o'lchov qiymatlari xato ko'rsatadi
   Chorа: sensорlarni kalibrovka qilish (yillik)
""",
    "ppr": """
GMD PPR jadvali (ABB tavsiya):

Kunlik:
- Air gap o'lchash (laser o'lchovchi)
- Harorat sensorlari nazorati
- Sovutish tizimi ishlashi
- ABB dashboard alarm tekshirish

Oylik:
- Stator vizual tekshiruvi
- Havo filtrlari tozalash/almashtirish
- Aloqa kabellari tekshiruvi
- Inverter sovutish suvosi sifati

Yillik:
- To'liq elektrik diagnostika (partial discharge test)
- Stator sargilari izolyatsiya o'lchash (IR/PI test)
- Air gap to'liq o'lchash (CMM bilan)
- ABB texnik xizmati muhandisi bilan tekshiruv
""",
    "fault_kodlar": """
ABB GMD tez-tez fault kodlari:

A001 — Motor harorati yuqori (>130°C) → sovutish tekshiring
A002 — Air gap alarm → o'lchovni tekshiring
A010 — Thyristor fault → ABB muhandisi chaqiring
A015 — Transformer harorati → transformator yonidagi fan tekshiring
A020 — Izolyatsiya resistans past → IR test bajarib ABBga xabar bering
F001 — Kritik fault, to'xtatish → darhol ABB texnikini chaqiring
F005 — Overcurrent → yuklama tekshiring, cyclokоnverter tekshiring
"""
}

# ── Slurry Nasos ma'lumotlar bazasi ──────────────────────────
SLURRY_PUMP_KNOWLEDGE = {
    "warman": """
Warman slurry nasos (Weir Minerals) — AGMK da keng qo'llaniladi.

Seriyalar: AH, HH, M, L, R, WBH
Mis boyitishda asosan: AH seriya (horizontal), M seriya (mill discharge)

Asosiy wearing parts (yeyiladigan qismlar):
- Impeller (krylchatka) — polimer yoki metal
- Liners: Front/Back/Side liner
- Shaft seal: gland packing yoki mechanical seal
- Suction/Discharge nozzle liners

Yeyilish normlari (AH nasos):
- Impeller resursi: 500-3000 soat (materialga qarab)
- Liner resursi: 1000-4000 soat
- Packing almashtirish: har 2-4 haftada

Muhim parametrlar (o'lchash kerak):
- Differential pressure: ΔP = 0.1-0.8 MPa (ish nuqtasiga qarab)
- Vibration: ≤ 7.1 mm/s (ISO 10816)
- Bearing temperature: ≤ 80°C
- Flow rate va head: nasos egri chizig'iga solishtiring
""",
    "diagnostika": """
Slurry nasos diagnostika qoidalari:

Kaviatsiya (eng keng tarqalgan muammo):
- Belgi: g'alati "shag'al ovozi", tebranish ortadi
- Sabab: NPSH etarli emas, qovurg'a tiqilgan
- Tekshirish: kirish bosimini o'lchang, PRE tekshiring

Ortiqcha tebranish:
- Sabab 1: Impeller yeyilgan → impeller almashtiring
- Sabab 2: Podshipnik yeyilgan → almashtiring
- Sabab 3: Muvozanat buzilgan → balansировка

Oqish (seal):
- Gland packing: tortiş sozlang yoki packing almashtiring
- Mechanical seal: seal almashtirish (ixtisoslashgan)

Unumdorlik pasayishi:
- Impeller yeyilganligi tekshiring (vizual)
- Nasos krivoy chizig'i bilan hozirgi ish nuqtasini solishtiring
- Zabornik filtri tozalang
""",
    "o_lchamlar": """
Warman AH nasos optimal o'lchamlari:

Nasos tanlaganda:
1. Flow rate (Q) — m³/soat
2. Head (H) — metr
3. Density (rho) — slurry zichligi (kg/m³)
4. Solid content (Cw) — % qattiq zarrachalar
5. d50/d85 — zarracha o'lchami

Korreksiya koeffitsienti:
- Suv bilan ishlash uchun: η_water
- Slurry uchun: η_slurry = η_water × HR × HQ
- HR, HQ — Warman diagrammasidan olinadi

Qoidа: Nasos 70-90% samaradorlik nuqtasida ishlashi kerak.
"""
}

# ── Flotatsiya mashinalari ─────────────────────────────────────
FLOTATION_KNOWLEDGE = {
    "outotec": """
Outotec (nowe Metso Outotec) OK/ТС flotatsiya mashinasi:

Asosiy qismlar:
- Rotor/Stator (impeller-disperser)
- Drive shaft va seal
- Air control system (nasos yoki kompressor)
- Level control valve
- Froth launder (ko'pik o'tkazgich)

Kritik parametrlar (mis flotatsiyasi):
- Havo sarfi: 0.5-1.5 m³/(min·m²) — AGMK texnologiyasiga qarab
- Pульpa sathi: texnologik reglamentga ko'ra
- Rotor RPM: nasos nominaliga ko'ra
- Havo bosimi kirish: 0.3-0.6 bar (g)

Tez-tez muammolar:
1. Ko'pik kam → havo ko'paytir yoki reagent tekshir
2. Rotor qiziydi → moy tekshir, sovutish
3. Havo yo'q → kompressor, ventil, quvur tekshir
4. Pульpa sathи o'zgaradi → level valve kalibratsiyasi
""",
    "reagentlar": """
Mis flotatsiyasida asosiy reagentlar (AGMK):

Kollektorlar (mis minerallarini yig'ish):
- Xantogenat (kaliy butilxantogenat — KBX)
- Aerofloat
- Dozalash: 20-100 g/t rudaga qarab

Ko'pirtuvchilar:
- MIBC (metilizobutilkarbinol)
- T-66, T-80 (turpentin asosida)
- Dozalash: 5-30 g/t

Regulyatorlar:
- Ohak (CaO) — pH ni 9.5-12 ga olib kelish
- Soda — pH regulyatsiyasi

⚠️ Xavfsizlik: Xantogenat yonuvchan va toksik!
MSDS ni o'qing, himoya vositalarini kiyng.
"""
}

# ── Texnik standartlar (GOST + ISO) ───────────────────────────
STANDARDS_DB = {
    "tebranish": "ISO 10816 (ISO 20816) — Mashina tebranish normalari",
    "podshipnik": "ISO 281 — Podshipnik resurs hisoblash. GOST 18855",
    "nasoslar": "GOST 22247 — Sentrifugal nasoslar. API 610 (neft sanoati)",
    "elektr_xavfsizlik": "GOST 12.1.019 — Elektr xavfsizlik. GOST R 50571 (IEC 60364)",
    "hse": "ISO 45001 (OHSAS 18001) — Mehnat xavfsizligi. GOST 12.0.004",
    "texnik_xizmat": "GOST 18322-2016 — TO va ta'mirlash tizimi",
    "chertyo'j": "GOST 2.101 — Texnik hujjatlar. GOST 2.602 — Ta'mirlash hujjatlari",
    "metall": "GOST 380 — Konstruksiya po'lati. GOST 1050 — Sifatli po'lat",
    "payvand": "GOST 5264 — Payvand choklar. GOST 14771 — Gaz-himoya payvandlash",
}


class KnowledgeBase:
    def __init__(self):
        self.groq = Groq(api_key=os.getenv("GROQ_API_KEY"))

    def get_gmd_info(self, query: str = "") -> str:
        """GMD haqida ma'lumot berish"""
        if any(w in query.lower() for w in ["fault", "kod", "xato", "alarm"]):
            section = "fault_kodlar"
        elif any(w in query.lower() for w in ["ppr", "jadval", "ta'mirlash", "texnik xizmat"]):
            section = "ppr"
        elif any(w in query.lower() for w in ["nosoz", "muammo", "ishlamayapti"]):
            section = "nosozliklar"
        elif any(w in query.lower() for w in ["parametr", "o'lchov", "harorat", "tebranish"]):
            section = "texnik_parametrlar"
        else:
            section = "umumiy"

        content = GMD_KNOWLEDGE.get(section, GMD_KNOWLEDGE["umumiy"])
        return f"⚙️ *GMD / ABB Drayverlari — {section.replace('_', ' ').title()}*\n\n{content}"

    def get_slurry_pump_info(self, query: str = "") -> str:
        """Slurry nasos haqida ma'lumot"""
        if any(w in query.lower() for w in ["diagnos", "muammo", "nosoz", "kaviatsiya"]):
            section = "diagnostika"
        elif any(w in query.lower() for w in ["o'lcham", "tanlash", "flow", "head"]):
            section = "o_lchamlar"
        else:
            section = "warman"

        content = SLURRY_PUMP_KNOWLEDGE.get(section, SLURRY_PUMP_KNOWLEDGE["warman"])
        return f"🔧 *Slurry Nasos (Warman) — {section.replace('_', ' ').title()}*\n\n{content}"

    def get_flotation_info(self, query: str = "") -> str:
        """Flotatsiya mashinalari haqida"""
        if any(w in query.lower() for w in ["reagent", "kimyo", "xantogenat", "ko'pirtuvchi"]):
            section = "reagentlar"
        else:
            section = "outotec"

        content = FLOTATION_KNOWLEDGE.get(section, FLOTATION_KNOWLEDGE["outotec"])
        return f"🏭 *Flotatsiya Mashinalari — {section.title()}*\n\n{content}"

    def get_standard(self, topic: str) -> str:
        """Tegishli standartni qaytarish"""
        for key, val in STANDARDS_DB.items():
            if key in topic.lower() or topic.lower() in key:
                return f"📋 *Standart:* {val}"
        # Eng yaqinini topishga urinish
        results = []
        for key, val in STANDARDS_DB.items():
            if any(word in topic.lower() for word in key.split("_")):
                results.append(f"• {val}")
        if results:
            return "📋 *Tegishli standartlar:*\n" + "\n".join(results)
        return f"📋 '{topic}' uchun maxsus standart topilmadi. GOST / ISO ro'yxatini tekshiring."

    async def expert_consult(self, question: str) -> str:
        """
        Foydalanuvchi savoliga MBF-3 ekspert darajasida javob berish.
        Maxsus bilimlar bazasi + AI kombinatsiyasi.
        """
        # Tegishli bilimlarni topish
        context_parts = []

        q_lower = question.lower()
        if any(w in q_lower for w in ["gmd", "abb", "drayvеr", "gearless", "cycloconverter"]):
            context_parts.append(GMD_KNOWLEDGE["umumiy"])
            context_parts.append(GMD_KNOWLEDGE["nosozliklar"])
        if any(w in q_lower for w in ["warman", "slurry", "nasos", "pump"]):
            context_parts.append(SLURRY_PUMP_KNOWLEDGE["warman"])
            context_parts.append(SLURRY_PUMP_KNOWLEDGE["diagnostika"])
        if any(w in q_lower for w in ["flotatsiya", "flot", "ko'pik", "reagent"]):
            context_parts.append(FLOTATION_KNOWLEDGE["outotec"])
        if any(w in q_lower for w in ["gost", "iso", "standart"]):
            context_parts.append(str(STANDARDS_DB))

        kb_context = "\n\n---\n\n".join(context_parts) if context_parts else ""

        system_prompt = f"""
Sen AGMK 3-mis boyitish fabrikasi (MBF-3) bo'yicha ekspert mexanıksan.
Quyidagi texnik bilimlar bazasi mavjud:

{kb_context if kb_context else "Umumiy mexanik bilimlar bilan javob ber."}

O'zbek tilida, professional va aniq javob ber.
Formulalar, GOST raqamlari va amaliy tavsiyalar ber.
"""
        try:
            resp = self.groq.chat.completions.create(
                model=GROQ_MODEL,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user",   "content": question}
                ],
                max_tokens=1000, temperature=0.3
            )
            return "🏭 *MBF-3 Ekspert Maslahati:*\n\n" + resp.choices[0].message.content
        except Exception as e:
            return f"❌ Ekspert maslahat xatosi: {e}"

    def search(self, query: str) -> str:
        """Barcha bilimlar bazasida qidirish"""
        q = query.lower()
        results = []

        # GMD
        for section, content in GMD_KNOWLEDGE.items():
            if q in content.lower():
                results.append(f"🔌 GMD/{section}: ...{self._extract_context(content, q)}...")

        # Slurry nasos
        for section, content in SLURRY_PUMP_KNOWLEDGE.items():
            if q in content.lower():
                results.append(f"💧 Slurry/{section}: ...{self._extract_context(content, q)}...")

        # Flotatsiya
        for section, content in FLOTATION_KNOWLEDGE.items():
            if q in content.lower():
                results.append(f"⚗️ Flotatsiya/{section}: ...{self._extract_context(content, q)}...")

        if results:
            return "🔍 *Bilimlar bazasidan topildi:*\n\n" + "\n\n".join(results[:3])
        return f"🔍 '{query}' bo'yicha bilimlar bazasida ma'lumot topilmadi."

    def _extract_context(self, text: str, query: str, window: int = 150) -> str:
        """Matndан qidirilayotgan so'z atrofidagi kontekstni ajratish"""
        idx = text.lower().find(query.lower())
        if idx == -1:
            return text[:window]
        start = max(0, idx - 50)
        end = min(len(text), idx + window)
        return text[start:end].strip()
