"""
AI Services — Groq (Llama 3) + Gemini 1.5 Flash
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


class AIServices:
    def __init__(self):
        self.groq = Groq(api_key=os.getenv("GROQ_API_KEY"))
        genai.configure(api_key=os.getenv("GEMINI_API_KEY"))
        self.gemini = genai.GenerativeModel(GEMINI_MODEL)

    # ── Intent aniqlash ───────────────────────────────────────
    async def detect_intent(self, text: str) -> dict:
        prompt = f"""Xabarni tahlil qil va FAQAT JSON qaytар:
Xabar: "{text}"

{{"action":"send_message|save_note|add_task|get_tasks|done_task|currency|weather|get_notes|report|memory|chat",
"target":"kimga yozish ismi yoki null",
"content":"asosiy mazmun",
"deadline":"muddat ISO format yoki null",
"task_id":"vazifa raqami yoki null",
"city":"shahar yoki null"}}"""

        try:
            resp = self.groq.chat.completions.create(
                model=GROQ_MODEL,
                messages=[{"role": "user", "content": prompt}],
                max_tokens=200,
                temperature=0.1
            )
            raw = resp.choices[0].message.content
            clean = re.sub(r'```json|```', '', raw).strip()
            return json.loads(clean)
        except Exception as e:
            log.warning(f"Intent xatosi: {e}")
            return {"action": "chat"}

    # ── Groq suhbat ───────────────────────────────────────────
    async def chat(self, user_text: str, history: list, context: str = "") -> str:
        system = (
            "Sen o'zbek tilida gaplashadigan aqlli shaxsiy yordamchisan. "
            "Qisqa, aniq va foydali javob ber. Telegram Markdown ishlatishingiz mumkin (*bold*, _italic_).\n"
        )
        if context:
            system += f"\nBazadan topilgan tegishli ma'lumotlar:\n{context}"

        messages = [{"role": "system", "content": system}]

        # Oxirgi 10 ta suhbat tarixi
        for h in history[-10:]:
            messages.append({"role": h["role"], "content": h["content"]})

        messages.append({"role": "user", "content": user_text})

        try:
            resp = self.groq.chat.completions.create(
                model=GROQ_MODEL,
                messages=messages,
                max_tokens=1000,
                temperature=0.7
            )
            return resp.choices[0].message.content
        except Exception as e:
            return f"❌ AI xatosi: {e}"

    # ── Muhimlik darajasi ─────────────────────────────────────
    async def score_importance(self, text: str) -> float:
        keywords = [
            'shartnoma', 'muddat', 'deadline', 'muhim', 'urgent', 'kritik',
            'to\'lov', 'pul', 'kredit', 'bank', 'loyiha', 'yig\'ilish',
            'majlis', 'kontrakt', 'qurilish', 'buyurtma', 'imzo'
        ]
        score = 0.3
        lower = text.lower()
        for kw in keywords:
            if kw in lower:
                score += 0.08
        if re.search(r'\d{4,}', text):
            score += 0.1
        if re.search(r'\d{1,2}[-\/]\d{1,2}', text):
            score += 0.15
        return min(1.0, score)

    # ── Ovoz → Matn (Gemini) ──────────────────────────────────
    async def transcribe_voice(self, audio_bytes: bytes) -> str:
        try:
            with tempfile.NamedTemporaryFile(suffix=".ogg", delete=False) as f:
                f.write(audio_bytes)
                tmp_path = f.name

            audio_file = genai.upload_file(tmp_path, mime_type="audio/ogg")
            response = self.gemini.generate_content([
                audio_file,
                "Bu ovozni o'zbek, rus yoki ingliz tilida matnga o'gir. Faqat gapirilgan so'zlar, boshqa hech narsa yozma."
            ])
            os.unlink(tmp_path)
            return response.text.strip()
        except Exception as e:
            log.error(f"Ovoz tahlil xatosi: {e}")
            return ""

    # ── PDF tahlil (Gemini) ───────────────────────────────────
    async def analyze_pdf(self, file_bytes: bytes) -> str:
        try:
            with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False) as f:
                f.write(file_bytes)
                tmp_path = f.name

            pdf_file = genai.upload_file(tmp_path, mime_type="application/pdf")
            response = self.gemini.generate_content([
                pdf_file,
                "Bu hujjatni o'zbek tilida tahlil qil:\n1. Asosiy mavzu\n2. Muhim ma'lumotlar\n3. Sanalar va raqamlar\n4. Xulosa"
            ])
            os.unlink(tmp_path)
            return response.text.strip()
        except Exception as e:
            return f"❌ PDF tahlil xatosi: {e}"

    # ── Rasm tahlil (Gemini) ──────────────────────────────────
    async def analyze_image(self, image_bytes: bytes) -> str:
        try:
            with tempfile.NamedTemporaryFile(suffix=".jpg", delete=False) as f:
                f.write(image_bytes)
                tmp_path = f.name

            img_file = genai.upload_file(tmp_path, mime_type="image/jpeg")
            response = self.gemini.generate_content([
                img_file,
                "Bu rasmda nima bor? O'zbek tilida qisqacha tasvirla."
            ])
            os.unlink(tmp_path)
            return response.text.strip()
        except Exception as e:
            return f"❌ Rasm tahlil xatosi: {e}"
