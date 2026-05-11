"""
AI Services v4.0 — OpenRouter (Gemini o'rniga) + Groq Whisper
AGMK 3-MBF Mexanik O'tkirbek uchun
"""

import os, json, re, tempfile, base64, logging
import aiohttp
from groq import Groq

log = logging.getLogger(__name__)

GROQ_MODEL       = os.getenv("GROQ_MODEL", "llama-3.3-70b-versatile")
OPENROUTER_KEY   = os.getenv("OPENROUTER_API_KEY", "")
OPENROUTER_MODEL = os.getenv("OPENROUTER_MODEL", "google/gemini-2.0-flash-exp:free")
OPENROUTER_URL   = "https://openrouter.ai/api/v1/chat/completions"

MECHANIC_SYSTEM = """Sen O'tkirbek — AGMK 3-mis boyitish fabrikasining mexanigisan. 
Bu SENING shaxsiy botingsan, o'ZINGGA yozmoqdasan.

MUHIM QOIDALAR:
- "Tushunarli. Keyinroq xabar beraman" DEMA — bu AutoPilot uchun
- Oddiy salomlashuvga: "Salom! Nima yordam kerak?" kabi javob ber
- Texnik savollarga mutaxassis sifatida javob ber
- Qisqa va aniq gapir
- O'zbek yoki Rus tilida (xabar tiliga qarab)
- Telegram Markdown ishlatishingiz mumkin (*bold*, _italic_)

Ixtisosliging: Warman nasoslari, ABB/GMD dvigatellar, konveyerlar, 
flotatsiya mashinalari, PPR, GOST standartlari, OHSAS 18001."""


class AIServices:
    def __init__(self):
        self.groq    = Groq(api_key=os.getenv("GROQ_API_KEY", ""))
        self._or_key = OPENROUTER_KEY

    async def _openrouter(self, messages: list, max_tokens: int = 1500, model: str = None) -> str:
        if not self._or_key:
            return "❌ OPENROUTER_API_KEY sozlanmagan. Railway Variables ga qo'shing."
        headers = {
            "Authorization": f"Bearer {self._or_key}",
            "Content-Type": "application/json",
            "HTTP-Referer": "https://github.com/agmk-bot",
            "X-Title": "AGMK MBF-3 Bot",
        }
        payload = {"model": model or OPENROUTER_MODEL, "messages": messages, "max_tokens": max_tokens}
        try:
            async with aiohttp.ClientSession() as s:
                async with s.post(OPENROUTER_URL, json=payload, headers=headers,
                                  timeout=aiohttp.ClientTimeout(total=30)) as r:
                    data = await r.json()
                    if "error" in data:
                        return f"❌ OpenRouter: {data['error'].get('message','')}"
                    return data["choices"][0]["message"]["content"].strip()
        except Exception as e:
            return f"❌ OpenRouter xatosi: {e}"

    async def detect_intent(self, text: str) -> dict:
        """Xabar maqsadini aniqlash. Shubhali holatlarda chat qaytaradi."""
        prompt = (
            f'Quyidagi xabarning maqsadini aniqla va FAQAT JSON qaytар. Boshqa hech narsa yozma.\n\n'
            f'Xabar: "{text}"\n\n'
            'QOIDALAR (muhim):\n'
            '- Savol, suhbat, maslahat, texnik yordam = action="chat"\n'
            '- "send_message" FAQAT "Azizga yoz: ..." shakli uchun\n'
            '- target aniq ism bo\'lmasa = action="chat"\n'
            '- Shubha bo\'lsa = action="chat"\n\n'
            '{"action":"send_message|voice_send|save_note|add_task|get_tasks|done_task|'
            'currency|weather|get_notes|report|memory|safety_check|incident|'
            'hydraulic_calc|defect_act|work_report|service_letter|ppr_schedule|chat",'
            '"target":"null","content":"xabar matni","deadline":"null",'
            '"task_id":"null","city":"null","equipment":"null","work_type":"null"}'
        )
        try:
            resp = self.groq.chat.completions.create(
                model=GROQ_MODEL, messages=[{"role": "user", "content": prompt}],
                max_tokens=300, temperature=0.1)
            raw = resp.choices[0].message.content
            parsed = json.loads(re.sub(r'```json|```', '', raw).strip())
            # Xavfsizlik: target aniq bo'lmasa chat ga o'tkazish
            target = str(parsed.get("target", "null")).lower().strip()
            if target in ("null", "none", "", "0", "unknown", "noma'lum"):
                parsed["action"] = "chat"
            return parsed
        except Exception as e:
            log.warning(f"Intent xatosi: {e}")
            return {"action": "chat"}

    async def chat(self, user_text: str, history: list, context: str = "") -> str:
        system = MECHANIC_SYSTEM + (f"\n\nKontekst:\n{context}" if context else "")
        messages = [{"role": "system", "content": system}]
        for h in history[-10:]:
            messages.append({"role": h["role"], "content": h["content"]})
        messages.append({"role": "user", "content": user_text})
        try:
            resp = self.groq.chat.completions.create(
                model=GROQ_MODEL, messages=messages, max_tokens=1200, temperature=0.6)
            return resp.choices[0].message.content
        except Exception as e:
            return f"❌ AI xatosi: {e}"

    async def score_importance(self, text: str) -> float:
        keywords = ['shartnoma','muddat','muhim','urgent','avaria','nosoz',
                    "to'xtadi",'buzildi','PPR','xavf','hodisa','defekt','eslatilsin']
        score = 0.3
        lower = text.lower()
        for kw in keywords:
            if kw in lower: score += 0.08
        if re.search(r'\d{4,}', text): score += 0.1
        if re.search(r'\d{1,2}[-\/]\d{1,2}', text): score += 0.15
        return min(1.0, score)

    async def transcribe_voice(self, audio_bytes: bytes) -> str:
        try:
            with tempfile.NamedTemporaryFile(suffix=".ogg", delete=False) as f:
                f.write(audio_bytes); tmp = f.name
            with open(tmp, "rb") as af:
                t = self.groq.audio.transcriptions.create(
                    file=("voice.ogg", af, "audio/ogg"),
                    model="whisper-large-v3",
                    response_format="text",
                    language="uz")          # ← faqat o'zbek tili
            os.unlink(tmp)
            return (t if isinstance(t, str) else getattr(t, 'text', '')).strip()
        except Exception as e:
            log.error(f"Ovoz xatosi: {e}"); return ""

    async def analyze_pdf(self, file_bytes: bytes) -> str:
        try:
            import io
            try:
                import pypdf
                reader = pypdf.PdfReader(io.BytesIO(file_bytes))
                text = "\n".join(p.extract_text() or "" for p in reader.pages[:10])[:6000]
            except ImportError:
                return "❌ pypdf o'rnatilmagan. requirements.txt ga qo'shing: pypdf"
            if not text.strip():
                return "❌ PDF dan matn ajratib bo'lmadi."
            return await self._openrouter([{"role": "user", "content":
                f"Bu texnik hujjatni o'zbek tilida tahlil qil:\n{text}\n\n"
                "1.Hujjat turi 2.Texnik parametrlar 3.O'lchamlar/standartlar 4.Muhim sanalar 5.Xulosa"}])
        except Exception as e:
            return f"❌ PDF xatosi: {e}"

    async def analyze_image(self, image_bytes: bytes, extra_prompt: str = "") -> str:
        try:
            b64 = base64.b64encode(image_bytes).decode()
            if extra_prompt and any(w in extra_prompt.lower() for w in ['chertyo','sxema','chizma','drawing']):
                prompt = (f"Bu sanoat chertyo'ji. O'zbek tilida:\n1.Nima tasvirlangan\n"
                         f"2.O'lchamlar\n3.Belgilar izohi\n4.GOST standarti\n5.Mexanik uchun muhim\n"
                         f"6.⚠️ Xavfsizlik\nSavol: {extra_prompt}")
            else:
                prompt = extra_prompt or "Bu sanoat rasmini mexanik nuqtai nazaridan tahlil qil. Nosozlik yoki xavfli holat bormi?"
            messages = [{"role":"user","content":[
                {"type":"image_url","image_url":{"url":f"data:image/jpeg;base64,{b64}"}},
                {"type":"text","text":prompt}]}]
            return await self._openrouter(messages, model=os.getenv(
                "OPENROUTER_VISION_MODEL","google/gemini-2.0-flash-exp:free"))
        except Exception as e:
            return f"❌ Rasm xatosi: {e}"

    async def translate_document(self, text: str, target_lang: str = "uz") -> str:
        langs = {"uz":"o'zbek","ru":"rus","en":"ingliz"}
        return await self._openrouter([{"role":"user","content":
            f"Quyidagi texnik matnni {langs.get(target_lang,target_lang)} tiliga tarjima qil. "
            f"Texnik atamalar uchun asl terminni qavsda qoldir:\n\n{text[:4000]}"}], 2000)

    async def simulate_emergency(self, scenario: str) -> str:
        return await self._openrouter([
            {"role":"system","content":MECHANIC_SYSTEM},
            {"role":"user","content":
                f"Avariya simulyatsiyasi: {scenario}\n\n"
                "1.⚠️ Xavf darajasi (1-5)\n2.🔴 Darhol choralar (5 daqiqa)\n"
                "3.📞 Kimga xabar berish\n4.🔧 Texnik choralar (ketma-ket)\n"
                "5.🦺 Xavfsizlik\n6.📋 Hujjatlashtirish\n7.🔄 Qayta tiklash"}], 1500)

    async def generate_request_form(self, content: str) -> str:
        from datetime import datetime
        now = datetime.now().strftime('%d.%m.%Y')
        return await self._openrouter([{"role":"user","content":
            f"Rasmiy so'rov-ariza (zayavka) tayyorla:\n{content}\n\n"
            f"Format:\nARIZA / ЗАЯВКА\nSana: {now}\nTashkilot: AGMK 3-MBF\n"
            "Mavzu: ...\nAsoslanish: ...\n"
            "Jadval: № | Nomi | Miqdori | O'lchov birligi | Izoh\n"
            "Imzo: Mexanik O'tkirbek"}], 800)

    async def generate_shift_handover(self, info: str) -> str:
        from datetime import datetime
        now = datetime.now()
        return await self._openrouter([{"role":"user","content":
            f"Smena topshirish protokoli:\nMa'lumot: {info}\n\n"
            f"📋 SMENA TOPSHIRISH PROTOKOLI\n"
            f"🗓 {now.strftime('%d.%m.%Y')} | ⏰ {now.strftime('%H:%M')}\n"
            "✅ BAJARILGAN ISHLAR:\n⚠️ DAVOM ETAYOTGAN MUAMMOLAR:\n"
            "🔧 KEYINGI SMENAGA TOPSHIRIQ:\n📊 USKUNALAR HOLATI:\nImzo:___"}], 1000)

    async def calc_bearing_life(self, params: str) -> str:
        return await self._openrouter([
            {"role":"system","content":MECHANIC_SYSTEM},
            {"role":"user","content":
                f"Podshipnik resursini hisoblа (ISO 281):\n{params}\n\n"
                "1.L10 resurs (soat) formulasi bilan\n"
                "2.Tavsiya etilgan almashtirish muddati\n"
                "3.Yog'lash intervali\n4.Monitoring parametrlari"}], 800)

    async def build_voice_proxy_text(self, original_msg: str, owner_name: str = "O'tkirbek") -> str:
        try:
            resp = self.groq.chat.completions.create(
                model=GROQ_MODEL, max_tokens=300, temperature=0.5,
                messages=[{"role":"user","content":
                    f"Xabarni professional vositachi tarzida o'zbek tilida qayta yoz:\n"
                    f"Original: \"{original_msg}\"\n"
                    f"Format: \"Assalomu alaykum! Men {owner_name}ning AI yordamchisiman. "
                    f"{owner_name} sizga shuni yetkazishni so'radi: [mazmun]\""}])
            return resp.choices[0].message.content.strip()
        except Exception:
            return f"Assalomu alaykum! Men {owner_name}ning AI yordamchisiman. Xabar: {original_msg}"
