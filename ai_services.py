"""
AI Services v4.0 — Groq + Gemini 2.0 Flash (BEPUL)
Muammo 1: gemini-1.5-flash → gemini-2.0-flash (model nomi tuzatildi)
Muammo 2: safe_md() — Telegram Markdown parse xatosini hal qiladi

API kalitlar (.env):
  GROQ_API_KEY      — chat, intent, whisper (https://console.groq.com)
  GEMINI_API_KEY    — PDF, rasm, vizual, HSE, sensor (https://aistudio.google.com)
"""

import os
import re
import json
import tempfile
import logging
import aiohttp

from groq import Groq
import google.generativeai as genai

log = logging.getLogger(__name__)

# ── Modellar ──────────────────────────────────────────────────
GROQ_MODEL   = os.getenv("GROQ_MODEL",   "llama3-70b-8192")
GEMINI_MODEL = os.getenv("GEMINI_MODEL", "gemini-2.0-flash")   # ← Tuzatildi
OWNER_NAME   = os.getenv("OWNER_NAME",   "O'tkirbek")

MECHANIC_SYSTEM = """Sen Olmaliq kon-metallurgiya kombinati (AGMK) 3-mis boyitish fabrikasida
mexanik bo'lib ishlaydigan O'tkirbek ning shaxsiy AI yordamchisisan.

Ixtisosliging:
- Sanoat nasoslari (Warman, KSB, Metso), kompressorlar, konveyerlar, tegirmonlar
- GMD/ABB drayverlari, flotatsiya mashinalari (Outotec)
- Gidravlik va pnevmatik tizimlar, PPR, kapital ta'mirlash
- GOST standartlari, ISO standartlari
- Chertyo'j va texnik sxemalar tahlili
- Xavfsizlik (OHSAS 18001, ISO 45001, GOST 12.0)
- O'zbek va rus tillarida texnik terminologiya

Javob qoidalari:
- Aniq, qisqa, professional
- Formulalar va GOST raqamlari
- O'zbek tilida
"""


# ══════════════════════════════════════════════════════════════
# safe_md — Telegram "Can't parse entities" xatosini hal qiladi
# ══════════════════════════════════════════════════════════════
def safe_md(text: str) -> str:
    """
    AI javobidagi juft bo'lmagan * _ belgilarini tuzatadi.
    Telegram Markdown parse xatosini bartaraf etadi.
    """
    if not text:
        return text

    # Kod bloklarini saqlaymiz (ularni o'zgartirmaslik kerak)
    code_blocks = {}
    counter = [0]

    def save_code(m):
        key = f"__CODE_{counter[0]}__"
        code_blocks[key] = m.group(0)
        counter[0] += 1
        return key

    text = re.sub(r'```[\s\S]*?```', save_code, text)
    text = re.sub(r'`[^`\n]+`',      save_code, text)

    # Har qatorda juft bo'lmagan * va _ ni tuzatish
    lines = text.split('\n')
    fixed = []
    for line in lines:
        if len(re.findall(r'(?<!\\)\*', line)) % 2 != 0:
            line = re.sub(r'(?<!\\)\*(?=[^*]*$)', '', line)
        if len(re.findall(r'(?<!\\)_', line)) % 2 != 0:
            line = re.sub(r'(?<!\\)_(?=[^_]*$)', '', line)
        fixed.append(line)

    text = '\n'.join(fixed)

    # Kod bloklarini qaytaramiz
    for key, val in code_blocks.items():
        text = text.replace(key, val)

    return text.strip()


# ══════════════════════════════════════════════════════════════
# AIServices
# ══════════════════════════════════════════════════════════════
class AIServices:

    def __init__(self):
        self.groq = Groq(api_key=os.getenv("GROQ_API_KEY", ""))
        genai.configure(api_key=os.getenv("GEMINI_API_KEY", ""))
        self.gemini = genai.GenerativeModel(GEMINI_MODEL)

    # ── Intent aniqlash (Groq — tez) ─────────────────────────
    async def detect_intent(self, text: str) -> dict:
        prompt = f"""Xabarni tahlil qil va FAQAT JSON qaytар (boshqa narsa yozma):
Xabar: "{text}"

Mumkin actionlar:
send_message, voice_send, save_note, add_task, get_tasks, done_task,
currency, weather, report, memory, get_notes,
equipment_info, safety_check, incident,
hydraulic_calc, pneumatic_calc, bearing_calc,
defect_act, work_report, service_letter, ppr_schedule,
drawing_analysis, sensor_analysis, gmd_info, slurry_info, mbf3_expert,
late_notify, autopilot_on, autopilot_off, busy_on, busy_off, chat

{{"action":"...",
"target":null,"content":"mazmun","deadline":null,
"task_id":null,"city":null,"equipment":null,
"work_type":null,"minutes":null,"reason":null,"params":{{}}}}"""

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

    # ── Asosiy chat (Groq) ────────────────────────────────────
    async def chat(self, user_text: str, history: list, context: str = "") -> str:
        system = MECHANIC_SYSTEM
        if context:
            system += f"\n\nKontekst:\n{context}"

        messages = [{"role": "system", "content": system}]
        for h in history[-10:]:
            messages.append({"role": h["role"], "content": h["content"]})
        messages.append({"role": "user", "content": user_text})

        try:
            resp = self.groq.chat.completions.create(
                model=GROQ_MODEL, messages=messages,
                max_tokens=1200, temperature=0.6
            )
            return safe_md(resp.choices[0].message.content)
        except Exception as e:
            return f"❌ AI xatosi: {e}"

    # ── Muhimlik bahosi ───────────────────────────────────────
    async def score_importance(self, text: str) -> float:
        keywords = [
            'shartnoma', 'muddat', 'deadline', 'muhim', 'urgent', 'kritik',
            "to'lov", 'pul', 'kredit', 'bank', 'loyiha', "yig'ilish",
            'majlis', 'kontrakt', 'buyurtma', 'imzo',
            'avaria', 'nosoz', "to'xtadi", 'buzildi', 'kapital', 'PPR',
            'xavf', 'baxtsiz', 'hodisa', 'defekt', "ta'mirlash"
        ]
        score = 0.3
        lower = text.lower()
        for kw in keywords:
            if kw in lower:
                score += 0.08
        if re.search(r'\d{4,}', text):               score += 0.1
        if re.search(r'\d{1,2}[-\/]\d{1,2}', text): score += 0.15
        return min(1.0, score)

    # ── Ovoz → Matn (Groq Whisper) ────────────────────────────
    async def transcribe_voice(self, audio_bytes: bytes) -> str:
        try:
            with tempfile.NamedTemporaryFile(suffix=".ogg", delete=False) as f:
                f.write(audio_bytes)
                tmp_path = f.name
            with open(tmp_path, "rb") as af:
                transcription = self.groq.audio.transcriptions.create(
                    file=("voice.ogg", af, "audio/ogg"),
                    model="whisper-large-v3",
                    response_format="text",
                    language="uz"
                )
            os.unlink(tmp_path)
            return (transcription if isinstance(transcription, str)
                    else getattr(transcription, 'text', '')).strip()
        except Exception as e:
            log.error(f"Ovoz tahlil xatosi: {e}")
            return ""

    # ── PDF tahlil (Gemini 2.0 Flash) ────────────────────────
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
5. Mexanik uchun muhim xulosalar"""
            ])
            os.unlink(tmp_path)
            return safe_md(response.text.strip())
        except Exception as e:
            return f"❌ PDF tahlil xatosi: {e}"

    # ── Rasm / Chertyo'j tahlili (Gemini Vision) ─────────────
    async def analyze_image(self, image_bytes: bytes, extra_prompt: str = "") -> str:
        try:
            with tempfile.NamedTemporaryFile(suffix=".jpg", delete=False) as f:
                f.write(image_bytes)
                tmp_path = f.name

            img_file = genai.upload_file(tmp_path, mime_type="image/jpeg")

            if extra_prompt and any(w in extra_prompt.lower() for w in
                                     ['chertyo', 'sxema', 'chizma', 'drawing', 'scheme']):
                prompt = (
                    f"Bu sanoat chertyo'ji. O'zbek tilida tahlil qil:\n"
                    f"1. Nima tasvirlangan\n2. O'lchamlar va parametrlar\n"
                    f"3. Texnik belgilar izohi\n4. GOST standarti\n"
                    f"5. Mexanik uchun muhim ma'lumotlar\n"
                    f"Savol: {extra_prompt}"
                )
            else:
                prompt = extra_prompt or (
                    "Bu rasmda nima bor? Mexanik nuqtai nazaridan tahlil qil. "
                    "O'zbek tilida qisqacha javob ber."
                )

            response = self.gemini.generate_content([img_file, prompt])
            os.unlink(tmp_path)
            return safe_md(response.text.strip())
        except Exception as e:
            return f"❌ Rasm tahlil xatosi: {e}"

    # ── Vizual Defektoskopiya (Gemini Vision) ─────────────────
    async def inspect_equipment_visual(self, image_bytes: bytes,
                                        extra_info: str = "") -> str:
        try:
            with tempfile.NamedTemporaryFile(suffix=".jpg", delete=False) as f:
                f.write(image_bytes)
                tmp_path = f.name

            img_file = genai.upload_file(tmp_path, mime_type="image/jpeg")
            prompt = (
                "Sen AGMK uskunalarini vizual tekshirish ekspertisan. O'zbek tilida:\n\n"
                "VIZUAL DEFEKTOSKOPIYA HISOBOTI\n\n"
                "1. Uskuna turi\n"
                "2. KRITIK nosozliklar (darhol to'xtatish kerak)\n"
                "3. O'rtacha muammolar (5 kun ichida ta'mirlash)\n"
                "4. Kuzatish kerak (keyingi PPRda)\n"
                "5. Umumiy holat: YAXSHI / QONIQARLI / YOMON / KRITIK\n"
                "6. Tavsiyalar va kerakli ehtiyot qismlar\n"
                "7. Xavfsizlik ogohlantirishlari\n\n"
                "GOST 18322-2016 asosida."
                + (f"\nQo'shimcha: {extra_info}" if extra_info else "")
            )
            response = self.gemini.generate_content([img_file, prompt])
            os.unlink(tmp_path)
            return safe_md(response.text.strip())
        except Exception as e:
            return f"❌ Vizual tekshiruv xatosi: {e}"

    # ── HSE Audit (Gemini Vision) ─────────────────────────────
    async def hse_audit_image(self, image_bytes: bytes, location: str = "") -> str:
        try:
            with tempfile.NamedTemporaryFile(suffix=".jpg", delete=False) as f:
                f.write(image_bytes)
                tmp_path = f.name

            img_file = genai.upload_file(tmp_path, mime_type="image/jpeg")
            prompt = (
                "Sen HSE auditori sifatida rasmni tekshirasan.\n"
                "AGMK OHSAS 18001 / ISO 45001 asosida. O'zbek tilida:\n\n"
                "HSE VIZUAL AUDIT\n\n"
                "1. PPE tekshiruvi:\n"
                "   Kaska, kombinezon, poyabzal, ko'zoynak, qo'lqop, respirator\n"
                "2. Ish maydoni xavfsizligi\n"
                "3. Aniqlangan xavflar\n"
                "4. Qaror: RUXSAT ETILGAN / EHTIYOT BILAN / TAQIQLANGAN\n"
                "5. Zarur choralar"
                + (f"\nJoylashuv: {location}" if location else "")
            )
            response = self.gemini.generate_content([img_file, prompt])
            os.unlink(tmp_path)
            result = safe_md(response.text.strip())

            if "TAQIQLANGAN" in result.upper():
                badge = "🔴 KIRISH TAQIQLANGAN"
            elif "EHTIYOT BILAN" in result.upper():
                badge = "🟡 EHTIYOT BILAN"
            else:
                badge = "🟢 RUXSAT ETILGAN"
            return f"🦺 *HSE AUDIT: {badge}*\n\n{result}"
        except Exception as e:
            return f"❌ HSE audit xatosi: {e}"

    # ── Sensor ekran tahlili (Gemini Vision) ──────────────────
    async def analyze_sensor_screenshot(self, image_bytes: bytes,
                                         equipment: str = "") -> str:
        try:
            with tempfile.NamedTemporaryFile(suffix=".jpg", delete=False) as f:
                f.write(image_bytes)
                tmp_path = f.name

            img_file = genai.upload_file(tmp_path, mime_type="image/jpeg")
            prompt = (
                f"Bu sanoat sensor/monitoring ekrani. Uskuna: {equipment or 'aniqla'}\n"
                "Rasmdan qiymatlarni o'qib O'zbek tilida tahlil qil:\n\n"
                "1. O'qilgan qiymatlar (har bir parametr)\n"
                "2. Normadan chetga chiqqanlar (alarmlar)\n"
                "3. Prognoz: kritik holatga qancha vaqt?\n"
                "4. Darhol tavsiya\n"
                "5. Xavf darajasi: XAVFSIZ / DIQQAT / OGOHLANISH / KRITIK"
            )
            response = self.gemini.generate_content([img_file, prompt])
            os.unlink(tmp_path)
            return safe_md(response.text.strip())
        except Exception as e:
            return f"❌ Sensor ekran tahlil xatosi: {e}"

    # ── Sensor matn tahlili (Groq) ────────────────────────────
    async def analyze_sensor_text(self, sensor_data: str,
                                   equipment: str = "") -> str:
        normal = self._get_default_params(equipment)
        try:
            resp = self.groq.chat.completions.create(
                model=GROQ_MODEL,
                messages=[
                    {"role": "system", "content": MECHANIC_SYSTEM},
                    {"role": "user", "content":
                     f"Sensor ma'lumotlarini tahlil qil:\n"
                     f"Uskuna: {equipment if equipment else 'noma_lum'}\n"
                     f"Normal parametrlar: {normal}\n"
                     f"Ma'lumotlar:\n{sensor_data}\n\n"
                     f"O'zbek tilida:\n"
                     f"1. Holat (normada / normadan chetda)\n"
                     f"2. Anomaliyalar va sabablari\n"
                     f"3. Prognoz\n"
                     f"4. Tavsiyalar\n"
                     f"5. Xavf: XAVFSIZ / DIQQAT / OGOHLANISH / KRITIK"}
                ],
                max_tokens=900, temperature=0.3
            )
            return safe_md(resp.choices[0].message.content)
        except Exception as e:
            return f"❌ Sensor tahlil xatosi: {e}"

    def _get_default_params(self, equipment: str) -> str:
        eq = equipment.lower()
        for key, val in {
            "nasos":      "Tebranish ≤4.5 mm/s, Podshipnik ≤80°C",
            "tegirmon":   "Tebranish ≤7.1 mm/s, Moy bosimi 0.1-0.3 MPa",
            "motor":      "Harorat ≤105°C, Tebranish ≤4.5 mm/s",
            "kompressor": "Harorat ≤120°C, Moy bosimi 0.15-0.35 MPa",
            "gmd":        "Stator ≤130°C, Air gap 10-20 mm, Tebranish ≤2.5 mm/s",
        }.items():
            if key in eq:
                return val
        return "Pasportga ko'ra normal diapazon"

    # ── MBF-3 Ekspert maslahati (Groq + KB kontekst) ─────────
    async def mbf3_expert_consult(self, question: str) -> str:
        kb = self._build_kb_context(question)
        system = MECHANIC_SYSTEM + (f"\n\nMBF-3 bilimlar:\n{kb}" if kb else "")
        try:
            resp = self.groq.chat.completions.create(
                model=GROQ_MODEL,
                messages=[
                    {"role": "system", "content": system},
                    {"role": "user",   "content": question}
                ],
                max_tokens=1200, temperature=0.3
            )
            return safe_md("🏭 *MBF-3 Ekspert:*\n\n" + resp.choices[0].message.content)
        except Exception as e:
            return f"❌ Ekspert maslahat xatosi: {e}"

    def _build_kb_context(self, question: str) -> str:
        q, parts = question.lower(), []
        if any(w in q for w in ["gmd", "abb", "gearless", "air gap", "cycloconverter"]):
            parts.append(
                "GMD/ABB: Stator <130°C, Air gap 10-20mm, Tebranish <2.5mm/s\n"
                "Fault kodlar: A001=harorat, A002=air gap, A010=thyristor(ABB chaqirish!),\n"
                "A020=izolyatsiya past, F001=kritik(darhol to'xtatish)"
            )
        if any(w in q for w in ["warman", "slurry", "kaviatsiya", "impeller", "liner"]):
            parts.append(
                "Warman AH/HH slurry nasos: Impeller resursi 500-3000h, Liner 1000-4000h\n"
                "Packing: har 2-4 hafta. Kaviatsiya: NPSH yetarli emas, g'alati shovqin\n"
                "Tebranish norma: ≤7.1 mm/s (ISO 10816), Podshipnik: ≤80°C"
            )
        if any(w in q for w in ["flotatsiya", "reagent", "xantogenat", "outotec"]):
            parts.append(
                "Outotec flotatsiya: Havo 0.5-1.5 m³/(min·m²), pH 9.5-12 (ohak bilan)\n"
                "Xantogenat (KBX): 20-100 g/t. MIBC: 5-30 g/t.\n"
                "XAVF: Xantogenat yonuvchan va toksik!"
            )
        if any(w in q for w in ["gost", "iso", "standart", "norma"]):
            parts.append(
                "ISO 10816/20816 tebranish, ISO 281/GOST 18855 podshipnik,\n"
                "GOST 22247/API 610 nasoslar, ISO 45001/OHSAS 18001 HSE,\n"
                "GOST 18322-2016 TO va ta'mirlash"
            )
        return "\n\n".join(parts)

    # ── AutoPilot — O'tkirbek nomidan javob ──────────────────
    async def autopilot_reply(self, incoming_message: str,
                               sender_name: str = "") -> str:
        try:
            resp = self.groq.chat.completions.create(
                model=GROQ_MODEL,
                messages=[
                    {"role": "system", "content":
                     f"Sen {OWNER_NAME} — AGMK 3-MBF mexanigi. "
                     f"Bu sening profilingdan kelgan xabar. "
                     f"Qisqa (1-3 jumla), O'zbek tilida javob ber. "
                     f"Bot ekanligingni hech qachon aytma."},
                    {"role": "user", "content":
                     f"{sender_name or 'Kimdir'} yozdi: {incoming_message}"}
                ],
                max_tokens=200, temperature=0.8
            )
            return safe_md(resp.choices[0].message.content.strip())
        except Exception as e:
            return "Kechirasiz, hozir band. Keyinroq murojaat qiling."

    # ── Band rejimi javob ─────────────────────────────────────
    async def busy_reply(self, incoming_msg: str, sender_name: str = "",
                          reason: str = "ish",
                          urgent: str = "smena boshlig'iga murojaat qiling") -> str:
        try:
            resp = self.groq.chat.completions.create(
                model=GROQ_MODEL,
                messages=[{"role": "user", "content":
                           f"{sender_name} yozdi: '{incoming_msg}'\n"
                           f"{OWNER_NAME} hozir {reason}da band.\n"
                           f"Qisqa avtomatik javob (2-3 jumla, O'zbek tilida).\n"
                           f"Shoshilinch: {urgent}"}],
                max_tokens=150, temperature=0.5
            )
            return safe_md(resp.choices[0].message.content.strip())
        except Exception:
            return (f"Salom! Hozir {reason}da bandman. "
                    f"Keyinroq javob beraman. Shoshilinch: {urgent}")

    # ── Kechikish xabari ──────────────────────────────────────
    async def late_notification_text(self, minutes: int,
                                      reason: str = "",
                                      recipient: str = "") -> str:
        try:
            resp = self.groq.chat.completions.create(
                model=GROQ_MODEL,
                messages=[{"role": "user", "content":
                           f"{OWNER_NAME} {minutes} daqiqa kechikmoqda."
                           f"{f' Sabab: {reason}.' if reason else ''}\n"
                           f"Professional ovozli xabar matni yoz (O'zbek tilida, 3-4 jumla). "
                           f"'Assalomu alaykum! Men {OWNER_NAME}ning AI yordamchisiman...' "
                           f"deb boshlang."}],
                max_tokens=200, temperature=0.5
            )
            return safe_md(resp.choices[0].message.content.strip())
        except Exception:
            return (f"Assalomu alaykum! Men {OWNER_NAME}ning AI yordamchisiman. "
                    f"{OWNER_NAME} {minutes} daqiqaga kechikmoqdalar.")

    # ── Ovozli vositachi matn ─────────────────────────────────
    async def build_voice_proxy_text(self, original_msg: str,
                                      owner_name: str = None) -> str:
        name = owner_name or OWNER_NAME
        try:
            resp = self.groq.chat.completions.create(
                model=GROQ_MODEL,
                messages=[{"role": "user", "content":
                           f"Xabarni professional vositachi tarzida qayta yoz (O'zbek tilida):\n"
                           f"Original: '{original_msg}'\n"
                           f"Format: 'Assalomu alaykum! Men {name}ning AI yordamchisiman. "
                           f"{name} sizga: [mazmun]'\n"
                           f"Faqat tayyor matnni yoz."}],
                max_tokens=250, temperature=0.5
            )
            return safe_md(resp.choices[0].message.content.strip())
        except Exception:
            return f"Assalomu alaykum! Men {name}ning AI yordamchisiman. Xabar: {original_msg}"
