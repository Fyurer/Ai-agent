# 🤖 AI Agent — AGMK 3-Mis Boyitish Fabrika Mexanigi

**O'tkirbek uchun shaxsiy Telegram AI yordamchisi**

---

## 🆕 Yangi funksiyalar

### 🎤 ElevenLabs TTS — Ovozli xabar yuborish
```
Azizga ovozli yoz: kechikmoqdaman
Shodigа ovoz: yig'ilishga 10 daqiqada keling
```
Bot avval AI yordamida professional vositachi matni tuzadi, keyin ElevenLabs orqali ovozga aylantirib yuboradi:
> *"Assalomu alaykum! Men O'tkirbek ning sun'iy intellekt yordamchisiman. O'tkirbek sizga ular uchrashuvga bir oz kechikishlarini aytdi."*

---

## ⚙️ Texnik funksiyalar

### 🔧 Qurilma muammolari
```
Nasos ishlamayapti
Kompressor tekshirish tartibi
Konveyerdagi muammo
```

### 📐 Hisob-kitoblar
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
Baxtsiz hodisa bo'ldi → ko'rsatma
Yong'in chiqdi → avariya tartibi
```

### 📋 Hujjatlar
```
Defekt akti: qurilma=Nasos №3, nuqson=muhr yeyilgan
Ish hisoboti: bugungi smena bajarildi...
Xizmat xati: kimga=sexboshlig'i, mavzu=kapital ta'mirlash
PPR jadvali: nasos, kompressor, konveyer
```

### 🖼 Chertyo'j tahlili
Rasm yuboring + `chertyo'j` yoki `sxema` deb yozing → AI tahlil qiladi

---

## 🛠 O'rnatish

### 1. Requirements
```bash
pip install -r requirements.txt
```

### 2. .env fayli
```bash
cp .env.example .env
# .env ni to'ldiring
```

### 3. Session olish (Railway uchun)
```bash
python get_session.py
# TG_SESSION_STRING ni .env ga qo'shing
```

### 4. Ishga tushirish
```bash
python bot.py
```

---

## 🔑 Kerakli API kalitlar

| Xizmat | Link | Narx |
|--------|------|------|
| Telegram Bot Token | @BotFather | Bepul |
| Telegram API ID/Hash | my.telegram.org | Bepul |
| Groq (Llama 3 + Whisper) | console.groq.com | Bepul |
| Gemini 1.5 Flash | aistudio.google.com | Bepul |
| **ElevenLabs TTS** | elevenlabs.io | 10k belgi/oy bepul |
| OpenWeatherMap | openweathermap.org | Bepul |

---

## 📁 Fayl tuzilmasi

```
├── bot.py              # Asosiy kirish nuqtasi
├── handlers.py         # Barcha handlerlar + TTS yuborish
├── ai_services.py      # Groq + Gemini + mexanik prompt
├── mechanic_service.py # ⭐ Mexanik uchun barcha funksiyalar
├── tts_service.py      # ⭐ ElevenLabs TTS xizmati
├── userbot.py          # Telethon + send_voice
├── database.py         # SQLite
├── get_session.py      # Session string olish
├── requirements.txt
├── railway.toml
└── .env.example
```

---

## 💡 Foydali maslahatlar

**Chertyo'j yuborishda:** Rasm bilan birga `chertyo'j` so'zini yozing
```
[rasm] + "Bu chertyo'jni tushuntir, o'lchamlarni ko'rsat"
```

**Ovozli buyruq berish:**
Telefonda gaplashing → bot transkripsiya qiladi → kerakli funksiyani bajaradi

**Defekt akti tezda:**
```
Defekt akti: qurilma=Flotatsiya mashinasi №4, joy=1-qavat, nuqson=turbina podshipnik yeyilgan, muddat=3 kun
```
