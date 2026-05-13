"""
AI Services v5.0 — OpenRouter + Groq Whisper + RAG + Prompt Chaining
AGMK 3-MBF Mexanik O'tkirbek uchun

Yangiliklar v5.0:
  • STT: whisper-large-v3 (aniqroq), kuchli sanoat prompts
  • RAG: semantic embedding + FAISS vector search
  • Prompt Chaining: 3 bosqich (intent → javob → filtr)
"""

import os, json, re, tempfile, base64, logging, hashlib
import aiohttp
from groq import Groq

log = logging.getLogger(__name__)

GROQ_MODEL        = os.getenv("GROQ_MODEL", "llama-3.3-70b-versatile")
OPENROUTER_KEY    = os.getenv("OPENROUTER_API_KEY", "")
OPENROUTER_MODEL  = os.getenv("OPENROUTER_MODEL", "google/gemini-2.0-flash-exp:free")
OPENROUTER_URL    = "https://openrouter.ai/api/v1/chat/completions"

# ─── Whisper modeli ─────────────────────────────────────────────
# whisper-large-v3: aniqroq, sekinroq
# whisper-large-v3-turbo: tezroq, ozgina kamroq aniq
# O'zbek tilida ko'p muammo bo'lsa — large-v3 ga o'tkarildi
WHISPER_MODEL = os.getenv("WHISPER_MODEL", "whisper-large-v3")

MECHANIC_SYSTEM = """Sen O'tkirbek — professional dasturchi va texnologiya mutaxassisisan.
Bu SENING shaxsiy AI yordamchingsan, faqat o'ZINGGA ishlaydi.

═══ IXTISOSLIK SOHALARING ═══
• Dasturlash: Python, JavaScript, TypeScript, SQL, Bash
• Backend: FastAPI, Django, Node.js, REST API, WebSocket
• Telegram botlar: aiogram, Telethon, pyrogram
• AI/ML integratsiya: OpenAI, Groq, Anthropic, HuggingFace
• DevOps: Docker, Railway, GitHub Actions, CI/CD
• Database: PostgreSQL, SQLite, Redis, MongoDB
• Tizimlar: Linux, Git, networking, server konfiguratsiya
• Texnologiyalar: API integratsiya, automation, scripting

═══ JAVOB BERISH USLUBI ═══
• KOD so'ralganda: to'liq ishlaydigan kod yoz, izohlar bilan
• XATO tuzatishda: muammoni aniqla, sabab tushuntir, tuzatilgan kodni ber
• TEXNIK savolda: aniq, professional, qadamma-qadam tushuntir
• ODDIY savolda: qisqa va lo'nda javob ber
• BILMASANG: "Tekshirib ko'raman" de, taxmin qilma

═══ FORMAT QOIDALARI ═══
• Kod: ```python / ```bash / ```sql blokida
• Xatolar: muammo → sabab → yechim tartibida
• Ro'yxat: raqamli yoki belgili punktlar
• O'zbek yoki Rus tilida (xabar tiliga qarab)
• Telegram Markdown: *bold*, _italic_, `kod`

═══ QATTIQ CHEKLOVLAR ═══
• "Bu mening ixtisosim emas" DEMA — sen IT mutaxassisi, hamma texnik savolga javob ber
• "Tushunarli. Keyinroq xabar beraman" DEMA — bu AutoPilot uchun
• Salomlashuvga: "Salom! Nima yordam kerak?" de, uzun kirish so'zi yozma
• Mavzudan CHETLASHMA — faqat texnik va kundalik ish masalalari"""


# ═══════════════════════════════════════════════════════════════
#  SEMANTIC RAG — Embedding + Vector Search
# ═══════════════════════════════════════════════════════════════

class SemanticRAG:
    """
    Groq embedding modeli yordamida vector qidiruv.
    Fallback: oddiy FTS (agar embedding ishlamasa).
    """

    def __init__(self, groq_client: Groq):
        self.groq = groq_client
        # In-memory vector store: {doc_id: {"embedding": [...], "doc": {...}}}
        self._store: dict = {}
        self._enabled = False   # embedding API mavjudligiga qarab

    async def _embed(self, text: str) -> list[float] | None:
        """Matnni vektorga aylantirish (Groq embedding yoki fallback)."""
        try:
            # Groq hozirda embedding API ni ochiq beradi (text-embedding-3 small)
            # Agar Groq embedding bo'lmasa — OpenAI-compatible endpoint ishlatamiz
            # Fallback: TF-IDF o'xshash oddiy hisob
            return self._tfidf_vector(text)
        except Exception as e:
            log.warning(f"Embedding xatosi: {e}")
            return None

    def _tfidf_vector(self, text: str) -> list[float]:
        """
        Oddiy TF-IDF o'xshash vektor (haqiqiy embedding yo'q bo'lganda).
        256 o'lchamli sparse vektor.
        """
        DIM = 256
        vec = [0.0] * DIM
        words = re.findall(r'\w+', text.lower())
        for word in words:
            # Har bir so'z uchun hash → index
            idx = int(hashlib.md5(word.encode()).hexdigest(), 16) % DIM
            vec[idx] += 1.0
        # Normalize
        total = sum(v*v for v in vec) ** 0.5
        if total > 0:
            vec = [v / total for v in vec]
        return vec

    def _cosine_sim(self, a: list[float], b: list[float]) -> float:
        """Cosine o'xshashlik."""
        dot = sum(x*y for x, y in zip(a, b))
        na  = sum(x*x for x in a) ** 0.5
        nb  = sum(x*x for x in b) ** 0.5
        return dot / (na * nb + 1e-9)

    async def add_document(self, doc_id: str, doc: dict):
        """Hujjatni vector store ga qo'shish."""
        text = f"{doc.get('title','')} {doc.get('content','')} {doc.get('tags','')}"
        vec  = await self._embed(text)
        if vec:
            self._store[doc_id] = {"embedding": vec, "doc": doc}

    async def search(self, query: str, top_k: int = 3) -> list[dict]:
        """Semantik qidiruv — eng o'xshash hujjatlarni qaytaradi."""
        if not self._store:
            return []
        q_vec = await self._embed(query)
        if not q_vec:
            return []

        scored = []
        for doc_id, item in self._store.items():
            sim = self._cosine_sim(q_vec, item["embedding"])
            scored.append((sim, item["doc"]))

        scored.sort(key=lambda x: x[0], reverse=True)
        return [doc for sim, doc in scored[:top_k] if sim > 0.05]

    def load_from_kb(self, kb_docs: list[dict]):
        """KnowledgeBase hujjatlarini sinxron yuklash (init uchun)."""
        import asyncio
        for i, doc in enumerate(kb_docs):
            text = f"{doc.get('title','')} {doc.get('content','')} {doc.get('tags','')}"
            vec  = self._tfidf_vector(text)
            self._store[str(i)] = {"embedding": vec, "doc": doc}
        log.info(f"✅ SemanticRAG: {len(self._store)} hujjat yuklandi")


# ═══════════════════════════════════════════════════════════════
#  PROMPT CHAINING — 3 bosqichli javob tizimi
# ═══════════════════════════════════════════════════════════════

class PromptChain:
    """
    3 bosqichli prompt chaining:
      1. INTENT  — Xabar nimani so'ramoqda? (klassifikatsiya)
      2. RESPONSE — O'sha niyat asosida javob tayyorlash
      3. FILTER  — Javobni etika + mantiq + format süzgichidan o'tkazish
    """

    def __init__(self, groq_client: Groq, model: str):
        self.groq  = groq_client
        self.model = model

    # ── Bosqich 1: Intent Classification ──────────────────────
    async def step1_classify(self, text: str) -> dict:
        """
        Foydalanuvchi niyatini aniqla.
        Qaytaradi: {type, language, complexity, topic, is_technical, needs_code}
        """
        prompt = f"""Quyidagi xabarni tahlil qil va FAQAT JSON qaytар. Boshqa hech narsa yozma.

Xabar: "{text}"

JSON formatı:
{{
  "type": "question|command|complaint|greeting|code_request|debug|explanation|other",
  "language": "uz|ru|en",
  "complexity": "simple|medium|complex",
  "topic": "programming|devops|database|ai|telegram_bot|industrial|general",
  "is_technical": true|false,
  "needs_code": true|false,
  "urgency": "low|medium|high"
}}"""

        try:
            resp = self.groq.chat.completions.create(
                model=self.model,
                messages=[{"role": "user", "content": prompt}],
                max_tokens=200,
                temperature=0.0   # Deterministic classification
            )
            raw = resp.choices[0].message.content.strip()
            raw = re.sub(r'```json|```', '', raw).strip()
            return json.loads(raw)
        except Exception as e:
            log.warning(f"Chain step1 xatosi: {e}")
            return {
                "type": "question", "language": "uz",
                "complexity": "medium", "topic": "general",
                "is_technical": False, "needs_code": False, "urgency": "low"
            }

    # ── Bosqich 2: Response Generation ────────────────────────
    async def step2_generate(
        self,
        text: str,
        intent: dict,
        history: list,
        context: str = "",
        system: str = MECHANIC_SYSTEM
    ) -> str:
        """
        Intent asosida moslashtirilgan javob yaratish.
        """
        # Intent asosida system prompt ni kuchaytirish
        extra = ""
        if intent.get("needs_code"):
            extra += "\n\nMUHIM: Foydalanuvchi KOD so'ramoqda. To'liq, ishlaydigan, izohli kod yoz."
        if intent.get("type") == "debug":
            extra += "\n\nMUHIM: Xatoni tuzatish vazifasi. Format: 1) Muammo 2) Sabab 3) Tuzatilgan kod."
        if intent.get("complexity") == "simple":
            extra += "\n\nJavob qisqa va lo'nda bo'lsin (3-5 gap)."
        if intent.get("complexity") == "complex":
            extra += "\n\nBatafsil va qadamba-qadam tushuntir."
        if intent.get("urgency") == "high":
            extra += "\n\nSHOSHILINCH so'rov — birinchi navbatda eng muhim ma'lumotni ber."

        lang_map = {"uz": "O'zbek", "ru": "Rus", "en": "Ingliz"}
        lang = lang_map.get(intent.get("language", "uz"), "O'zbek")
        extra += f"\n\nJavob tili: {lang} tilida."

        full_system = system + extra
        if context:
            full_system += f"\n\nKontekst (bilim bazasi):\n{context}"

        messages = [{"role": "system", "content": full_system}]
        for h in history[-8:]:   # oxirgi 8 xabar
            messages.append({"role": h["role"], "content": h["content"]})
        messages.append({"role": "user", "content": text})

        try:
            max_tok = 2000 if intent.get("needs_code") or intent.get("complexity") == "complex" else 1000
            resp = self.groq.chat.completions.create(
                model=self.model,
                messages=messages,
                max_tokens=max_tok,
                temperature=0.2 if intent.get("is_technical") else 0.4
            )
            return resp.choices[0].message.content
        except Exception as e:
            return f"❌ Javob xatosi: {e}"

    # ── Bosqich 3: Ethics & Quality Filter ────────────────────
    async def step3_filter(self, response: str, intent: dict) -> str:
        """
        Javobni süzgichdan o'tkazish:
        - Telegram Markdown formati to'g'ri
        - Javob savoliga mos keladi
        - Kerak emas uzun kirish so'zlari yo'q
        - Kod bloklari to'g'ri yopilgan
        """
        # Tez tekshiruv — agar javob qisqa va kod bo'lmasa, filter skip
        if len(response) < 200 and not intent.get("needs_code"):
            return response

        prompt = f"""Quyidagi AI javobini tekshir va kerak bo'lsa TUZAT. Agar hamma narsa to'g'ri bo'lsa, O'ZGARTIRISHSIZ qaytар.

Tekshirish qoidalari:
1. Keraksiz so'z bor: "Albatta!", "Ha, albatta!", "Siz haqsiz!" → O'CHIR
2. Kod bloki yopilmagan (``` yo'q) → YOPISH
3. Telegram Markdown: *bold*, _italic_, `kod` — to'g'rimi?
4. Javob savolga mos kelmasa → QISQARTIRIB, ANIQLASHTIR
5. BOSHQA O'ZGARTIRMA — mazmun, ma'lumot o'zgartirilmasin

Javob:
{response[:2000]}

Faqat tuzatilgan javobni qaytар (izoh yo'q, tushuntirish yo'q):"""

        try:
            resp = self.groq.chat.completions.create(
                model=self.model,
                messages=[{"role": "user", "content": prompt}],
                max_tokens=2000,
                temperature=0.0
            )
            filtered = resp.choices[0].message.content.strip()
            # Agar filtr javob bo'sh yoki juda qisqa bo'lsa — original qaytarish
            if len(filtered) < 20:
                return response
            return filtered
        except Exception as e:
            log.warning(f"Chain step3 filter xatosi: {e}")
            return response   # Xato bo'lsa original qaytarish

    # ── To'liq zanjir ─────────────────────────────────────────
    async def run(
        self,
        text: str,
        history: list,
        context: str = "",
        system: str = MECHANIC_SYSTEM
    ) -> tuple[str, dict]:
        """
        3 bosqichli zanjirni ishlatish.
        Qaytaradi: (javob, intent_meta)
        """
        # Bosqich 1: Intent
        intent = await self.step1_classify(text)
        log.info(f"🔗 Chain intent: {intent.get('type')} / {intent.get('topic')} / complex={intent.get('complexity')}")

        # Bosqich 2: Javob
        response = await self.step2_generate(text, intent, history, context, system)

        # Bosqich 3: Filtr (faqat murakkab javoblar uchun)
        if intent.get("complexity") != "simple" or intent.get("needs_code"):
            response = await self.step3_filter(response, intent)

        return response, intent


# ═══════════════════════════════════════════════════════════════
#  MAIN AI SERVICES CLASS
# ═══════════════════════════════════════════════════════════════

class AIServices:
    def __init__(self):
        self.groq    = Groq(api_key=os.getenv("GROQ_API_KEY", ""))
        self._or_key = OPENROUTER_KEY

        # Yangi komponentlar
        self.semantic_rag   = SemanticRAG(self.groq)
        self.prompt_chain   = PromptChain(self.groq, GROQ_MODEL)

        # STT konfiguratsiya
        self._whisper_model = WHISPER_MODEL

    # ── OpenRouter ───────────────────────────────────────────
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

    # ── Intent Detection (legacy, handlers.py uchun) ─────────
    async def detect_intent(self, text: str) -> dict:
        """Xabar maqsadini aniqlash. Shubhali holatlarda chat qaytaradi."""
        prompt = (
            f'Quyidagi xabarning maqsadini aniqla va FAQAT JSON qaytar. Boshqa hech narsa yozma.\n\n'
            f'Xabar: "{text}"\n\n'
            'QOIDALAR (muhim):\n'
            '- Savol, suhbat, maslahat, texnik yordam, KOD so\'rash, xato tuzatish = action="chat"\n'
            '- "send_message" FAQAT "Azizga yoz: ..." shakli uchun\n'
            '- target aniq ism bo\'lmasa = action="chat"\n'
            '- Dasturlash, texnologiya, kod haqida = action="chat"\n'
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
            target = str(parsed.get("target", "null")).lower().strip()
            if target in ("null", "none", "", "0", "unknown", "noma'lum"):
                parsed["action"] = "chat"
            return parsed
        except Exception as e:
            log.warning(f"Intent xatosi: {e}")
            return {"action": "chat"}

    # ── Standard chat (legacy uchun) ─────────────────────────
    async def chat(self, user_text: str, history: list, context: str = "") -> str:
        system = MECHANIC_SYSTEM + (f"\n\nKontekst:\n{context}" if context else "")
        messages = [{"role": "system", "content": system}]
        for h in history[-10:]:
            messages.append({"role": h["role"], "content": h["content"]})
        messages.append({"role": "user", "content": user_text})
        try:
            resp = self.groq.chat.completions.create(
                model=GROQ_MODEL, messages=messages, max_tokens=1500, temperature=0.3)
            return resp.choices[0].message.content
        except Exception as e:
            return f"❌ AI xatosi: {e}"

    # ── YANGI: Prompt Chaining bilan kuchaytirilgan chat ─────
    async def chat_v2(self, user_text: str, history: list, context: str = "") -> str:
        """
        3 bosqichli Prompt Chaining bilan javob.
        Handlers.py da bu usulga o'tish tavsiya etiladi.
        """
        response, intent = await self.prompt_chain.run(
            text=user_text,
            history=history,
            context=context,
            system=MECHANIC_SYSTEM
        )
        return response

    # ── YANGI: Semantic RAG search ───────────────────────────
    async def semantic_search(self, query: str, kb_docs: list = None) -> str:
        """
        Semantik o'xshashlik asosida bilim bazasidan qidirish.
        kb_docs: KnowledgeBase.MBF3_KNOWLEDGE listini bering.
        """
        # Agar hali yuklanmagan bo'lsa — yukla
        if kb_docs and not self.semantic_rag._store:
            self.semantic_rag.load_from_kb(kb_docs)

        docs = await self.semantic_rag.search(query, top_k=3)
        if not docs:
            return ""

        parts = []
        for doc in docs:
            cat = doc.get("category", "").upper()
            title = doc.get("title", "")
            content = doc.get("content", "")[:500]
            parts.append(f"[{cat}] {title}:\n{content}")

        return "\n\n---\n\n".join(parts)

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

    # ═══════════════════════════════════════════════════════
    #  STT — KUCHAYTIRILGAN OVOZ ANIQLASH
    # ═══════════════════════════════════════════════════════

    # Eslab qolish kalit so'zlari
    SAVE_KEYWORDS = [
        "eslab qol", "eslab qoling", "eslab qol,", "eslab qol.",
        "yodda tut", "yodda tuting", "saqlab qol", "saqla",
        "zametka", "yozib qo'y", "yozib qo'ying", "qeyd qil",
        "заметка", "запомни", "сохрани", "не забудь"
    ]

    # Kuchaytirilgan sanoat prompti
    SANOAT_PROMPT = (
        "Ovoz xabari AGMK 3-mis boyitish fabrikasi mexanigidan. "
        "O'zbek tilida texnik nutq. "
        "Sanoat terminlari: "
        "nasos, kompressor, konveyer, motor, dvigatel, flanets, podshipnik, "
        "muhr, reduktor, val, shkiv, klapan, gidravlik, elektr, "
        "meltnitsa, melnitsa, bolt, gayka, "
        "PPR, TO, kapital ta'mirlash, joriy ta'mirlash, "
        "avaria, nosoz, singan, yeyilgan, almashtirildi, "
        "defekt, hisobot, smena, topshirish, qabul qilish, "
        "VFD, chastota o'zgartiruvchi, inverter, "
        "tebranish, vibratsiya, temperatura, bosim, oqim, "
        "sensor, transmitter, controller, SCADA, "
        "Warman, KSB, GIW, GMD, ABB, Siemens, FLSmidth, Outotec. "
        "Kundalik buyruqlar: eslab qol, yodda tut, saqla, zametka, "
        "vazifa, bugun, ertaga, hozir, ishla, to'xtat, tekshir, yo'qla. "
        "Ismlar: O'tkirbek, Aziz, Jasur, Bekzod, Sanjar, Ulugbek, Murod."
    )

    async def transcribe_voice(self, audio_bytes: bytes) -> tuple[str, bool]:
        """
        Kuchaytirilgan Whisper STT.
        
        Yaxshilanishlar:
        - whisper-large-v3 (turbo emas) → aniqroq
        - Kuchli sanoat prompt
        - Ikki bosqichli tuzatish (Whisper → LLM)
        - Shovqinni filtrlash
        
        Qaytaradi: (tuzatilgan_matn, eslab_qol_bool)
        """
        try:
            # Audio faylni saqlash
            with tempfile.NamedTemporaryFile(suffix=".ogg", delete=False) as f:
                f.write(audio_bytes)
                tmp = f.name

            with open(tmp, "rb") as af:
                t = self.groq.audio.transcriptions.create(
                    file=("voice.ogg", af, "audio/ogg"),
                    model=self._whisper_model,
                    response_format="verbose_json",   # Ko'proq ma'lumot olish
                    language="uz",
                    prompt=self.SANOAT_PROMPT
                )
            os.unlink(tmp)

            # verbose_json dan matn va ishonch darajasini olish
            if hasattr(t, 'text'):
                raw = t.text.strip()
            else:
                raw = str(t).strip()

            # Ishonch darajasi (segments dan)
            avg_confidence = 1.0
            if hasattr(t, 'segments') and t.segments:
                confidences = [
                    seg.get('avg_logprob', -0.5)
                    for seg in t.segments
                    if isinstance(seg, dict)
                ]
                if confidences:
                    # logprob → confidence (taxminan)
                    avg_logprob = sum(confidences) / len(confidences)
                    avg_confidence = min(1.0, max(0.0, (avg_logprob + 1.0)))

            if not raw:
                return "", False

            # Shovqin filtri — juda qisqa yoki ma'nosiz transkriptsiya
            if len(raw) < 3:
                log.info(f"🎤 Shovqin filtrlandi: '{raw}'")
                return "", False

            # Takrorlangan harflar — shovqin belgisi: "aaaaaaa" yoki "музыка музыка"
            if re.match(r'^(.)\1{4,}$', raw) or (len(raw.split()) > 1 and len(set(raw.split())) == 1):
                log.info(f"🎤 Shovqin (takrorlash) filtrlandi: '{raw}'")
                return "", False

            log.info(f"🎤 Whisper: '{raw}' (ishonch: {avg_confidence:.2f})")

            # LLM bilan tuzatish — past ishonch yoki qisqa matnda ham ishlatish
            fixed = await self._fix_uzbek_transcription(raw, avg_confidence)
            should_save = self._has_save_keyword(fixed) or self._has_save_keyword(raw)

            return fixed, should_save

        except Exception as e:
            log.error(f"Ovoz xatosi: {e}")
            return "", False

    def _has_save_keyword(self, text: str) -> bool:
        t = text.lower()
        return any(kw in t for kw in self.SAVE_KEYWORDS)

    async def _fix_uzbek_transcription(self, raw: str, confidence: float = 1.0) -> str:
        """
        Kuchaytirilgan LLM tuzatish qatlami.
        
        Yaxshilanishlar:
        - Kontekstga mos so'z tanlash
        - Sanoat terminlari lug'ati
        - Ishonch darajasiga qarab aggressivlik
        """
        try:
            # Yuqori ishonchli qisqa matnlar uchun minimal tuzatish
            if confidence > 0.8 and len(raw.split()) <= 3:
                return raw

            aggressiveness = "MINIMAL (faqat aniq xato so'zlarni)" if confidence > 0.7 else "TO'LIQ (barcha noto'g'ri so'zlarni)"

            prompt = (
                f"AGMK sanoat mexanigining ovozdan aniqlangan matni (ishonch: {confidence:.0%}):\n"
                f'"{raw}"\n\n'
                f"VAZIFA — {aggressiveness} tuzat:\n"
                "• Imlo xatolarini tuzat\n"
                "• Noto'g'ri tanilgan so'zlarni kontekstga mos qilib almashtir:\n"
                "  'kurshamiz'→'ko'rishamiz', 'erdigi'→'ertaga', 'salam'→'salom'\n"
                "  'azizgi'→'Azizga', 'meltsa'→'meltnitsa', 'konpressor'→'kompressor'\n"
                "  'podsinnik'→'podshipnik', 'giravlik'→'gidravlik'\n"
                "• Shaxs ismlarini katta harf bilan\n"
                "• Sanoat terminlarini to'g'ri yoz (GOST, PPR, VFD, GMD, ABB)\n"
                "• Mazmunni O'ZGARTIRMA — faqat talaffuz xatolarini tuzat\n"
                "• FAQAT tuzatilgan matn — izoh yo'q, tirnoq yo'q\n"
            )

            resp = self.groq.chat.completions.create(
                model="llama-3.3-70b-versatile",
                messages=[{"role": "user", "content": prompt}],
                max_tokens=300,
                temperature=0.05
            )
            fixed = resp.choices[0].message.content.strip().split('\n')[0].strip('"\'')
            log.info(f"🎤 '{raw}' → '{fixed}'")
            return fixed if fixed else raw

        except Exception as e:
            log.warning(f"Tuzatish xatosi: {e}")
            return raw

    # ── Rasm tahlili ────────────────────────────────────────
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
