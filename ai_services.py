"""
AI Services — OpenRouter (Llama 3 + Vision) + Groq Whisper
Mexanik O'tkirbek uchun maxsus prompt
OpenRouter orqali Gemini va boshqa modellarga ulanish
"""

import os
import json
import re
import tempfile
import logging
import aiohttp
from groq import Groq

log = logging.getLogger(__name__)

GROQ_MODEL   = os.getenv("GROQ_MODEL", "llama3-70b-8192")
OPENROUTER_MODEL = os.getenv("OPENROUTER_MODEL", "google/gemini-2.0-flash-exp:free")
OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY", "")

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
        self.openrouter_key = OPENROUTER_API_KEY
        self.openrouter_model = OPENROUTER_MODEL

    async def _openrouter_request(self, messages: list, max_tokens: int = 1200, temperature: float = 0.6) -> str:
        """OpenRouter API orqali so'rov yuborish"""
        if not self.openrouter_key:
            log.warning("OpenRouter API key topilmadi, Groq-ga o'tish...")
            return None

        headers = {
            "Authorization": f"Bearer {self.openrouter_key}",
            "Content-Type": "application/json",
            "HTTP-Referer": "https://t.me/agmk_mexanik_bot",
            "X-Title": "AGMK Mexanik AI"
        }
        
        payload = {
            "model": self.openrouter_model,
            "messages": messages,
            "max_tokens": max_tokens,
            "temperature": temperature
        }
        
        try:
            async with aiohttp.ClientSession() as session:
                async with session.post(
                    "https://openrouter.ai/api/v1/chat/completions",
                    headers=headers,
                    json=payload,
                    timeout=aiohttp.ClientTimeout(total=60)
                ) as resp:
                    if resp.status == 200:
                        data = await resp.json()
                        return data["choices"][0]["message"]["content"]
                    else:
                        error_text = await resp.text()
                        log.error(f"OpenRouter xatosi {resp.status}: {error_text}")
                        return None
        except Exception as e:
            log.error(f"OpenRouter so'rov xatosi: {e}")
            return None

    async def detect_intent(self, text: str) -> dict:
        prompt = f"""Xabarni tahlil qil va FAQAT JSON qaytar (boshqa narsa yozma):
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
- spare_part_calc: ehtiyot qismlar hisobi
- request_generator: ariza/zayavka yaratish
- trend_analysis: trend tahlili
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
            # Avval OpenRouter, keyin Groq fallback
            resp_text = await self._openrouter_request(
                [{"role": "user", "content": prompt}],
                max_tokens=300,
                temperature=0.1
            )
            
            if resp_text is None:
                # Fallback to Groq
                resp = self.groq.chat.completions.create(
                    model=GROQ_MODEL,
                    messages=[{"role": "user", "content": prompt}],
                    max_tokens=300, temperature=0.1
                )
                resp_text = resp.choices[0].message.content
            
            clean = re.sub(r'```json|```', '', resp_text).strip()
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
            # Avval OpenRouter
            resp_text = await self._openrouter_request(
                messages,
                max_tokens=1200,
                temperature=0.6
            )
            
            if resp_text:
                return resp_text
            
            # Fallback to Groq
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
                    language="uz"
                )
            os.unlink(tmp_path)
            result = transcription if isinstance(transcription, str) else getattr(transcription, 'text', '')
            return result.strip()
        except Exception as e:
            log.error(f"Ovoz tahlil xatosi: {e}")
            return ""

    async def analyze_pdf(self, file_bytes: bytes) -> str:
        """OpenRouter Vision orqali PDF tahlili"""
        try:
            import base64
            pdf_b64 = base64.b64encode(file_bytes).decode('utf-8')
            
            prompt = """Bu texnik hujjatni o'zbek tilida tahlil qil:
1. Hujjat turi va mavzusi
2. Asosiy texnik ma'lumotlar
3. O'lchamlar, parametrlar, standartlar
4. Muhim sanalar va muddatlar
5. Xulosa va tavsiyalar

Mexanik nuqtai nazaridan muhim ma'lumotlarni ajratib ko'rsat."""

            messages = [
                {"role": "system", "content": "Sen texnik hujjatlarni tahlil qiluvchi ekspert mexaniksan."},
                {"role": "user", "content": f"PDF kontenti (base64): {pdf_b64[:5000]}\n\n{prompt}"}
            ]
            
            result = await self._openrouter_request(messages, max_tokens=2000, temperature=0.3)
            if result:
                return result.strip()
            return "❌ PDF tahlil qilishda xatolik (OpenRouter ishlamadi)"
        except Exception as e:
            return f"❌ PDF tahlil xatosi: {e}"

    async def analyze_image(self, image_bytes: bytes, extra_prompt: str = "") -> str:
        """OpenRouter Vision orqali rasm tahlili"""
        try:
            import base64
            img_b64 = base64.b64encode(image_bytes).decode('utf-8')
            
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

            messages = [
                {"role": "system", "content": "Sen sanoat jihozlarini vizual tahlil qiluvchi ekspert mexaniksan."},
                {"role": "user", "content": f"Rasm (base64): {img_b64}\n\n{prompt}"}
            ]
            
            result = await self._openrouter_request(messages, max_tokens=2000, temperature=0.3)
            if result:
                return result.strip()
            return "❌ Rasm tahlil qilishda xatolik"
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
            resp_text = await self._openrouter_request(
                [{"role": "user", "content": prompt}],
                max_tokens=300,
                temperature=0.5
            )
            if resp_text:
                return resp_text.strip()
            
            # Fallback to Groq
            resp = self.groq.chat.completions.create(
                model=GROQ_MODEL,
                messages=[{"role": "user", "content": prompt}],
                max_tokens=300, temperature=0.5
            )
            return resp.choices[0].message.content.strip()
        except Exception as e:
            return f"Assalomu alaykum! Men {owner_name} ning AI yordamchisiman. Xabar: {original_msg}"