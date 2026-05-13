# 🤖 AI Agent v5.0 — AGMK 3-MBF Mexanik O'tkirbek

**Shaxsiy Telegram AI yordamchisi — Groq + OpenRouter + Self-Evolution + Semantic RAG**

---

## 📋 Mundarija

1. [Imkoniyatlar](#imkoniyatlar)
2. [O'rnatish](#o'rnatish)
3. [Kerakli API kalitlar](#kerakli-api-kalitlar)
4. [Fayl tuzilmasi](#fayl-tuzilmasi)
5. [Buyruqlar va misollar](#buyruqlar-va-misollar)
6. [Self-Evolution Engine](#self-evolution-engine)
7. [AI Arxitektura](#ai-arxitektura)
8. [.env to'liq namuna](#env-to'liq-namuna)
9. [Muammolar va yechimlar](#muammolar-va-yechimlar)

---

## Imkoniyatlar

| Modul | Tavsif |
|-------|--------|
| 🎤 **STT** | Whisper large-v3 — O'zbek+Rus ovozli xabarlar |
| 🧠 **RAG** | FTS5 + Semantic vector qidiruv (bilim bazasi) |
| 🔗 **Prompt Chain** | 3 bosqichli javob: intent → generate → filter |
| 🧬 **Self-Evolution** | AI o'zi modul yozib, dinamik yuklaydi |
| 📊 **Digital Twin** | Uskunalar real-vaqt holati dashboard |
| 🔬 **Vision** | Defekt, HSE, sensor, chertyo'j tahlili |
| 📚 **Knowledge Base** | MBF-3 texnik hujjatlar + PDF yuklash |
| 🤖 **AutoPilot** | Kiruvchi xabarlarga avtomatik javob |
| 📋 **Hujjatlar** | Defekt akti, ish hisoboti, PPR jadvali |
| ⏰ **Eslatmalar** | Aniq daqiqali vazifa eslatmalari (Toshkent UTC+5) |
| ☀️ **Briefing** | Har kuni 12:00 da avtomatik kunlik hisobot |

---

## O'rnatish

```bash
# 1. Kutubxonalar
pip install -r requirements.txt

# 2. Muhit o'zgaruvchilari
cp .env.example .env
# .env faylini to'ldiring (quyida namuna)

# 3. Telegram session (Railway uchun)
python get_session.py
# TG_SESSION_STRING qiymatini .env ga qo'shing

# 4. Ishga tushirish
python bot.py
```

### Railway Deploy
```bash
# railway.toml allaqachon sozlangan
railway up
```

---

## Kerakli API kalitlar

| Xizmat | Link | Narx |
|--------|------|------|
| Telegram Bot Token | [t.me/BotFather](https://t.me/BotFather) | Bepul |
| Telegram API ID/Hash | [my.telegram.org](https://my.telegram.org) | Bepul |
| Groq (Llama 3.3 + Whisper) | [console.groq.com](https://console.groq.com) | Bepul |
| OpenRouter (Gemini vision) | [openrouter.ai](https://openrouter.ai) | Bepul tier |
| ElevenLabs TTS | [elevenlabs.io](https://elevenlabs.io) | 10k belgi/oy bepul |
| OpenWeatherMap | [openweathermap.org](https://openweathermap.org) | Bepul |

---

## Fayl tuzilmasi

```
├── bot.py                 # Asosiy kirish nuqtasi (briefing, scheduler)
├── handlers.py            # Barcha Telegram handlerlar
├── ai_services.py         # ⭐ Groq + SemanticRAG + PromptChain
├── knowledge_base.py      # MBF-3 bilim bazasi (SQLite FTS5)
├── mechanic_service.py    # Mexanik funksiyalar (hisob, hujjat)
├── digital_twin.py        # Uskunalar holati dashboard
├── vision_service.py      # Rasm tahlili (defekt, HSE)
├── tts_service.py         # ElevenLabs ovozli xabar
├── auto_reply.py          # AutoPilot (kiruvchi xabarlar)
├── auto_learner.py        # Manbalardan avtomatik o'rganish
├── personal_twin.py       # Shaxsiy uslub modeli
├── self_evolution.py      # 🧬 AI modul yaratish mexanizmi
├── evolution_handlers.py  # 🧬 /modules buyruqlari
├── userbot.py             # Telethon (xabar yuborish)
├── database.py            # SQLite (vazifa, eslatma, xotira)
├── get_session.py         # Session string olish
├── modules/               # 🧬 AI yozgan pluginlar (avtomatik)
├── logs/                  # Xato loglari
├── requirements.txt
└── .env.example
```

---

## Buyruqlar va misollar

### 💬 Oddiy suhbat va kod
```
Python da asyncio.gather misoli yoz
Docker Compose nginx + fastapi konfiguratsiya
SQL query: oxirgi 30 kunda eng ko'p buyurtma bergan 10 ta mijoz
Xatoni tuzat: [kodni pastga yozing]
```

### 🎤 Ovozli xabarlar
```
[ovozli xabar] → bot transkripsiya qilib, buyruqni bajaradi
Azizga ovozli yoz: kechikmoqdaman
Shodigа ovoz: yig'ilishga 10 daqiqada keling
```

### 🔬 Rasm tahlili
```
[rasm] defekt        → nosozlik tahlili
[rasm] hse           → xavfsizlik auditi
[rasm] sensor        → sensor skrinshot tahlili
[rasm] chertyo'j     → o'lchamlar va belgilar tahlili
```

### 📚 Bilim bazasi (RAG)
```
KB: warman nasos kaviatsiya sabablari
KB: GMD blokirovka tartibi
KB: flotatsiya reagentlari xavfsizligi
[PDF yuborish] → bilim bazasiga qo'shiladi
```

### 📋 Vazifa va eslatmalar
```
Vazifa: smena topshirish, soat 17:30
Vazifa: PPR rejasi tayyor, ertaga 09:00
Vazifa 3 bajarildi
/tasks — barcha vazifalar
```

### 🔧 Mexanik hisob-kitoblar
```
Gidravlik hisob: sarif=50, diametr=100, uzunlik=200
Pnevmatik hisob: hajm=10, bosim=8, vaqt=5
Podshipnik resursi: C=50, P=20, n=1500
```

### 🦺 Xavfsizlik
```
Elektr ishi oldidan xavfsizlik
Balandlikda ishlash xavfsizligi
Bosimli tizimda ishlash
Baxtsiz hodisa bo'ldi
Yong'in chiqdi → avariya tartibi
```

### 📄 Hujjatlar
```
Defekt akti: qurilma=Nasos №3, nuqson=muhr yeyilgan, muddat=2 kun
Ish hisoboti: bugungi smena bajarildi, 3 nasos tekshirildi
Xizmat xati: kimga=sexboshlig'i, mavzu=kapital ta'mirlash
PPR jadvali: nasos, kompressor, konveyer
```

### 📊 Digital Twin
```
/dashboard           → barcha uskunalar holati
/equipment           → uskunalar ro'yxati
```

### 🤖 AutoPilot
```
/autopilot_on        → yoqish
/autopilot_off       → o'chirish
/autopilot_status    → holat
```

### 💱 Tezkor ma'lumotlar
```
Valyuta kursi
500 dollar necha so'm
Ob-havo: Olmaliq
```

---

## Self-Evolution Engine

Bot o'z-o'zini kengaytira oladi — AI yangi modul yozib, uni dinamik yuklaydi.

### Qanday ishlaydi

```
Siz: "Yangi modul qo'sh: USD/UZS kursni ko'rsatadigan funksiya"
       ↓
Bot: AI → currency_rates.py yozadi → modules/ ga saqlaydi
       ↓
Bot: importlib orqali dinamik yuklaydi
       ↓
[Xato bo'lsa] → logs/error.log → AI xatoni o'qiydi → tuzatadi
       ↓
[Muvaffaqiyat] → git commit -m "Self-update: added currency_rates"
```

### Telegram buyruqlari

| Buyruq | Vazifa |
|--------|--------|
| `/modules` | Barcha modullar ro'yxati |
| `/module_run weather` | weather.py ning `run()` ni chaqirish |
| `/module_code weather` | Modul kodini ko'rish |
| `/module_del weather` | Modulni o'chirish |
| `/git_push` | GitHub ga push qilish |

### Matnli buyruqlar
```
Yangi modul qo'sh: sms yuborish funksiyasi
Yangi modul qo'sh: nasos vibratsiyasini Excel ga eksport qilish
Modul ishga tushir: weather
Modul chaqir: currency_rates
```

### Modul strukturasi
Har bir AI yaratgan modul shu shaklda bo'ladi:

```python
import os, logging
log = logging.getLogger(__name__)

async def run(**kwargs) -> str:
    """Asosiy funksiya — bu chaqiriladi"""
    try:
        # ... kod ...
        return "✅ Natija"
    except Exception as e:
        log.error(f"Xato: {e}")
        return f"❌ Xato: {e}"
```

---

## AI Arxitektura

### To'liq xabar oqimi

```
Foydalanuvchi xabari (matn / ovoz / rasm)
              │
   ┌──────────▼──────────┐
   │    quick_intent      │  ← regex/pattern (tezkor, API yo'q)
   └──────────┬──────────┘
              │ topilmadi
   ┌──────────▼──────────┐
   │    detect_intent     │  ← Groq LLM → JSON
   └──────────┬──────────┘
              │
   ┌──────────▼──────────────────────────┐
   │           Action Router              │
   │  send_msg / task / weather / kb ...  │
   └──────────┬──────────────────────────┘
              │ action = "chat"
   ┌──────────▼──────────────────────────────────┐
   │          CHAT TIZIMI v2.0                    │
   │                                              │
   │  1. Xotira     db.get_relevant_memories()    │
   │                                              │
   │  2a. FTS5 RAG  kb.get_rag_context()          │
   │  2b. Semantic  ai.semantic_search()           │
   │       → TF-IDF vector + cosine similarity    │
   │       → Ikki natija birlashtiriladi          │
   │                                              │
   │  3. Prompt Chain  ai.chat_v2()               │
   │     ├─ Bosqich 1: Intent classification      │
   │     │   {type, language, complexity,         │
   │     │    needs_code, urgency}                │
   │     ├─ Bosqich 2: Moslashtirilgan javob      │
   │     │   code→2000tok, simple→1000tok         │
   │     └─ Bosqich 3: Format/etika filtri        │
   │                                              │
   │  4. PersonalTwin fallback                    │
   └──────────────────────────────────────────────┘
```

### STT (Ovoz → Matn) pipeline

```
Ovozli xabar
     │
     ▼
Whisper large-v3  ← verbose_json (ishonch darajasi)
     │
     ▼
Shovqin filtri    ← < 3 harf, takrorlangan belgilar
     │
     ▼
LLM tuzatish      ← sanoat terminlari, imlo, ismlar
     │
     ▼
Tuzatilgan matn + should_save flag
```

### RAG (Bilim qidiruv) pipeline

```
Savol matni
     │
     ├──→ FTS5 qidiruv (SQLite)        tezkor, kalit so'z
     │
     └──→ Semantic qidiruv (TF-IDF)    sekin, ma'no bo'yicha
               │
               ▼
          Cosine similarity
               │
               ▼
     Top-3 eng mos hujjat
               │
               ▼
     Birlashtirilgan kontekst → LLM
```

---

## .env to'liq namuna

```env
# ── Telegram ───────────────────────────────────────────
BOT_TOKEN=your_bot_token
OWNER_CHAT_ID=your_telegram_id
OWNER_NAME=O'tkirbek

TG_API_ID=12345678
TG_API_HASH=your_api_hash
TG_PHONE=+998901234567
TG_SESSION_STRING=   # get_session.py dan olinadi

# ── AI Modellar ────────────────────────────────────────
GROQ_API_KEY=your_groq_key
GROQ_MODEL=llama-3.3-70b-versatile

OPENROUTER_API_KEY=your_openrouter_key
OPENROUTER_MODEL=google/gemini-2.0-flash-exp:free
OPENROUTER_VISION_MODEL=google/gemini-2.0-flash-exp:free

# ── STT ────────────────────────────────────────────────
# whisper-large-v3 (aniq) yoki whisper-large-v3-turbo (tez)
WHISPER_MODEL=whisper-large-v3

# ── TTS ────────────────────────────────────────────────
ELEVENLABS_API_KEY=your_elevenlabs_key
ELEVENLABS_VOICE_ID=your_voice_id

# ── Tashqi xizmatlar ───────────────────────────────────
WEATHER_API_KEY=your_openweather_key

# ── Database ───────────────────────────────────────────
DB_PATH=ai_agent.db

# ── Self-Evolution ─────────────────────────────────────
GIT_AUTO_COMMIT=true
MODULES_DIR=modules
LOGS_DIR=logs

# ── AutoLearner ────────────────────────────────────────
LEARN_INTERVAL_H=24
```

---

## Muammolar va yechimlar

### STT aniq tanimayapti
```
Yechim 1: WHISPER_MODEL=whisper-large-v3 (turbo emas)
Yechim 2: Shovqinli muhitda mikrofon yaqinroq ushlab gapiring
Yechim 3: Rus tilida gapiring (Whisper ruscha yaxshiroq tushunadi)
```

### RAG noto'g'ri javob qaytarmoqda
```
Yechim 1: KB: prefiks bilan aniq so'rang
  → "KB: Warman nasos kaviatsiya"
Yechim 2: PDF yuklab, bilim bazasini boyiting
Yechim 3: knowledge_base.py ga yangi hujjat qo'shing
```

### Semantic RAG xatosi
```log
Semantic RAG xatosi: cannot import name 'MBF3_KNOWLEDGE'
```
```
Yechim: knowledge_base.py da MBF3_KNOWLEDGE ro'yxati
        modul darajasida (class tashqarisida) e'lon qilinganligini tekshiring
```

### Prompt Chain sekin
```
Yechim: Har bir chat_v2 chaqiruvi 2-3 ta Groq so'rov qiladi.
        Agar tezlik muhim bo'lsa — ai.chat() ga qaytib o'ting
        (handlers.py da chat_v2 → chat)
```

### Self-Evolution moduli yuklanmayapti
```log
ImportError: cannot import name 'run' from 'modules.weather'
```
```
Yechim: modules/weather.py da async def run(**kwargs) -> str:
        funksiyasi mavjudligini tekshiring
```

### UserBot ulanmayapti
```
Yechim: python get_session.py → session string oling
        TG_SESSION_STRING .env ga to'g'ri yozing
        TG_API_ID va TG_API_HASH my.telegram.org dan oling
```

---

## Versiyalar

| Versiya | Yangiliklar |
|---------|-------------|
| v5.0 | Semantic RAG, Prompt Chaining (3 bosqich), STT yaxshilash |
| v4.2 | Self-Evolution Engine, AutoLearner, PersonalTwin |
| v4.0 | OpenRouter integratsiya, Vision, Digital Twin |
| v3.0 | Knowledge Base (FTS5), ElevenLabs TTS, AutoPilot |
| v2.0 | UserBot, ovozli xabar yuborish |
| v1.0 | Asosiy Groq chat, vazifa, eslatma |
