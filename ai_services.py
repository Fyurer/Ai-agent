"""
AI Services — Groq (Llama 3 + Whisper) + Gemini 1.5 Flash
Mexanik O'tkirbek uchun maxsus prompt
"""

import os
import json
import re
import tempfile
import logging
from groq import Groq
import google.generativeai as genai

log = logging.getLogger(__name__)

GROQ_MODEL   = os.getenv("GROQ_MODEL", "llama3-70b-8192")
GEMINI_MODEL = os.getenv("GEMINI_MODEL", "gemini-1.5-flash")

MECHANIC_SYSTEM = """Sen Olmaliq kon-metallurgiya kombinati (AGMK) 3-mis boyitish fabrikasida 
mexanik bo'lib ishlaydigan O'tkirbek ning shaxsiy AI yordamchisisan.

Sening ixtisosliging:
- Sanoat nasoslari, kompressorlar, konveyerlar, tegirmonlar, flotatsiya mashinalari
- Gidravlik va pnevmatik tizimlar
- PPR (profilaktik ta'mirlash) va kapital ta'mirlash
- GOST standartlari (rus va O'zbekiston)
- Chertyo'j va texnik sxemalar o'qish
- Xavfsizlik talablari (OHSAS 18001, GOST 12.0)
- Defekt aktlari, xizmat xatlari, ish hisobotlari
- O'zbek va rus tillarida texnik terminologiya

Javob berish uslubi:
- Aniq, qisqa va professional
- Kerak bo'lsa formulalar va hisob-kitoblar
- GOST raqamlarini ko'rsat
- Xavfsizlik ogohlantirishlarini yoz ⚠️
- Telegram Markdown (*bold*, _italic_, `kod`) ishlatishingiz mumkin
- O'zbek tilida gapir, texnik atamalar rus/ingliz tilida bo'lishi mumkin
"""


class AIServices:
    def __init__(self):
        self.groq = Groq(api_key=os.getenv("GROQ_API_KEY"))
        genai.configure(api_key=os.getenv("GEMINI_API_KEY"))
        self.gemini = genai.GenerativeModel(GEMINI_MODEL)

    async def detect_intent(self, text: str) -> dict:
        prompt = f"""Xabarni tahlil qil va FAQAT JSON qaytар (boshqa narsa yozma):
Xabar: "{text}"

Mumkin bo'lgan actionlar:
- send_message: kimgadir xabar yozish
- voice_send: ovozli xabar yuborish (ElevenLabs TTS)
- save_note, add_task, get_tasks, done_task
- currency, weather, report, memory, get_notes
- equipment_info: qurilma muammolari (nasos, kompressor va h.k.)
- safety_check: xavfsizlik checklisti
- incident: hodisa ko'rsatmasi
- hydraulic_calc: gidravlik hisob
- pneumatic_calc: pnevmatik hisob
- bearing_calc: podshipnik resurs
- defect_act: defekt akti yozish
- work_report: ish hisoboti
- service_letter: xizmat xati
- ppr_schedule: PPR jadvali
- drawing_analysis: chertyo'j tahlili
- chat: oddiy suhbat

{{"action":"...",
"target":"kimga yozish ismi yoki null",
"content":"asosiy mazmun",
"deadline":"muddat yoki null",
"task_id":"vazifa raqami yoki null",
"city":"shahar yoki null",
"equipment":"qurilma nomi yoki null",
"work_type":"ish turi xavfsizlik uchun yoki null",
"params":{{}}}}"""

        try:
            resp = self.groq.chat.completions.create(
                model=GROQ_MODEL,
                messages=[{"role": "user", "content": prompt}],
                max_tokens=300, temperature=0.1
            )
            raw   = resp.choices[0].message.content
            clean = re.sub(r'```json|```', '', raw).strip()
            return json.loads(clean)
        except Exception as e:
            log.warning(f"Intent xatosi: {e}")
            return {"action": "chat"}

    async def chat(self, user_text: str, history: list, context: str = "") -> str:
        system = MECHANIC_SYSTEM
        if context:
            system += f"\n\nBazadan topilgan kontekst:\n{context}"

        messages = [{"role": "system", "content": system}]
        for h in history[-10:]:
            messages.append({"role": h["role"], "content": h["content"]})
        messages.append({"role": "user", "content": user_text})

        try:
            resp = self.groq.chat.completions.create(
                model=GROQ_MODEL, messages=messages,
                max_tokens=1200, temperature=0.6
            )
            return resp.choices[0].message.content
        except Exception as e:
            return f"❌ AI xatosi: {e}"

    async def score_importance(self, text: str) -> float:
        keywords = [
            'shartnoma', 'muddat', 'deadline', 'muhim', 'urgent', 'kritik',
            "to'lov", 'pul', 'kredit', 'bank', 'loyiha', "yig'ilish",
            'majlis', 'kontrakt', 'qurilish', 'buyurtma', 'imzo',
            # Mexanik uchun qo'shimcha
            'avaria', 'nosoz', 'to\'xtadi', 'buzildi', 'kapital', 'PPR',
            'xavf', 'baxtsiz', 'hodisa', 'defekt', 'ta\'mirlash'
        ]
        score = 0.3
        lower = text.lower()
        for kw in keywords:
            if kw in lower:
                score += 0.08
        if re.search(r'\d{4,}', text): score += 0.1
        if re.search(r'\d{1,2}[-\/]\d{1,2}', text): score += 0.15
        return min(1.0, score)

    # ── Ovoz → Matn (Groq Whisper) ────────────────────────────
    async def transcribe_voice(self, audio_bytes: bytes) -> str:
        try:
            with tempfile.NamedTemporaryFile(suffix=".ogg", delete=False) as f:
                f.write(audio_bytes)
                tmp_path = f.name

            with open(tmp_path, "rb") as audio_file:
                transcription = self.groq.audio.transcriptions.create(
                    file=("voice.ogg", audio_file, "audio/ogg"),
                    model="whisper-large-v3",
                    response_format="text",
                    language="uz"  # O'zbek tili
                )
            os.unlink(tmp_path)
            result = transcription if isinstance(transcription, str) else getattr(transcription, 'text', '')
            return result.strip()
        except Exception as e:
            log.error(f"Ovoz tahlil xatosi: {e}")
            return ""

    # ── PDF tahlil ────────────────────────────────────────────
    async def analyze_pdf(self, file_bytes: bytes) -> str:
        try:
            with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False) as f:
                f.write(file_bytes)
                tmp_path = f.name
            pdf_file = genai.upload_file(tmp_path, mime_type="application/pdf")
            response = self.gemini.generate_content([
                pdf_file,
                """Bu texnik hujjatni o'zbek tilida tahlil qil:
                1. Hujjat turi va mavzusi
                2. Asosiy texnik ma'lumotlar
                3. O'lchamlar, parametrlar, standartlar
                4. Muhim sanalar va muddatlar
                5. Xulosa va tavsiyalar
                
                Mexanik nuqtai nazaridan muhim ma'lumotlarni ajratib ko'rsat."""
            ])
            os.unlink(tmp_path)
            return response.text.strip()
        except Exception as e:
            return f"❌ PDF tahlil xatosi: {e}"

    # ── Rasm/Chertyo'j tahlil ─────────────────────────────────
    async def analyze_image(self, image_bytes: bytes, extra_prompt: str = "") -> str:
        try:
            with tempfile.NamedTemporaryFile(suffix=".jpg", delete=False) as f:
                f.write(image_bytes)
                tmp_path = f.name
            img_file = genai.upload_file(tmp_path, mime_type="image/jpeg")
            
            if extra_prompt and any(w in extra_prompt.lower() for w in 
                                     ['chertyo', 'sxema', 'chizma', 'drawing', 'scheme']):
                prompt = f"""Bu sanoat chertyo'ji yoki texnik sxema. O'zbek tilida tahlil qil:

1. 📐 Nima tasvirlangan (qurilma, tizim, uzlari)
2. 📏 Ko'rinadigan o'lchamlar va parametrlar
3. 🔤 Texnik belgilar va qisqartmalar izohi
4. 📌 GOST/ISO standarti (agar aniqlansa)
5. ⚙️ Mexanik uchun muhim ma'lumotlar
6. ⚠️ Xavfsizlik talablari (agar bo'lsa)

Qo'shimcha savol: {extra_prompt}"""
            else:
                prompt = extra_prompt or (
                    "Bu rasmda nima bor? Mexanik nuqtai nazaridan tahlil qil. "
                    "O'zbek tilida qisqacha va aniq javob ber."
                )
            
            response = self.gemini.generate_content([img_file, prompt])
            os.unlink(tmp_path)
            return response.text.strip()
        except Exception as e:
            return f"❌ Rasm tahlil xatosi: {e}"

    async def build_voice_proxy_text(self, original_msg: str, owner_name: str = "O'tkirbek") -> str:
        """Foydalanuvchi xabari → vositachi ovoz matni (ElevenLabs uchun)"""
        prompt = f"""
        Quyidagi xabarni professional vositachi tarzida qayta yoz:
        Original xabar: "{original_msg}"
        
        Format: "Assalomu alaykum! Men {owner_name} ning sun'iy intellekt yordamchisiman. 
        {owner_name} sizga quyidagini yetkazishimni so'radi: [xabar mazmuni]"
        
        Faqat tayyor matnni yoz, boshqa izoh qo'shma. O'zbek tilida.
        """
        try:
            resp = self.groq.chat.completions.create(
                model=GROQ_MODEL,
                messages=[{"role": "user", "content": prompt}],
                max_tokens=300, temperature=0.5
            )
            return resp.choices[0].message.content.strip()
        except Exception as e:
            return f"Assalomu alaykum! Men {owner_name} ning AI yordamchisiman. Xabar: {original_msg}"
