# 🤖 AI Agent Bot — Railway Deploy

## ⚡ O'rnatish (15 daqiqa)

---

### 1-QADAM — Bot yaratish (@BotFather)

1. Telegramda `@BotFather` ga yozing
2. `/newbot` → nom bering → username bering
3. **BOT_TOKEN** ni saqlang

---

### 2-QADAM — Chat ID olish (@userinfobot)

1. `@userinfobot` ga `/start` yuboring
2. **Your ID** raqamini saqlang — bu OWNER_CHAT_ID

---

### 3-QADAM — Session String olish (Termux da)

```bash
# Termux da:
pkg install python -y
pip install telethon python-dotenv -q
python get_session.py
```

Telefon kodi so'raydi → kiritasiz → **SESSION STRING** chiqadi → saqlang!

---

### 4-QADAM — GitHub ga yuklash

1. GitHub.com → New repository → `ai-agent-bot`
2. Barcha fayllarni yuklang (ZIP ichidagilarni)
3. `.env.example` faylini **YUKLAMANG** (maxfiy)

```bash
# Yoki Termux da:
git clone https://github.com/SIZNING_USERNAME/ai-agent-bot
cd ai-agent-bot
# fayllarni ko'chiring
git add .
git commit -m "AI Agent bot"
git push
```

---

### 5-QADAM — Railway deploy

1. **railway.app** ga kiring → GitHub bilan login
2. **New Project** → **Deploy from GitHub repo**
3. Repozitoriyangizni tanlang
4. **Variables** bo'limiga kiring, quyidagilarni qo'shing:

```
BOT_TOKEN          = 7123456789:AAF...
OWNER_CHAT_ID      = 123456789
TG_API_ID          = 12345678
TG_API_HASH        = abc123...
TG_PHONE           = +998901234567
TG_SESSION_STRING  = (3-qadamdan)
GROQ_API_KEY       = gsk_...
GEMINI_API_KEY     = AIza...
WEATHER_API_KEY    = (ixtiyoriy)
MEMORY_DAYS        = 60
```

5. **Deploy** tugmasini bosing
6. **Logs** da `✅ Bot ishga tushdi!` ko'rsangiz — tayyor!

---

## 🎮 Bot Buyruqlari

| Yozasiz | Bot nima qiladi |
|---------|-----------------|
| `Azizga yoz: ertaga 10da` | Azizga sizning nomingizdan yuboradi |
| `Eslab qol: shartnoma 15-may` | Xotiraga saqlaydi |
| `Vazifa: hisobot tayyorla` | Vazifa qo'shadi |
| `Vazifa 2 bajarildi` | 2-vazifani yopadi |
| `1000 dollar necha so'm` | CBU kursini ko'rsatadi |
| `Toshkentda ob-havo` | Ob-havo beradi |
| `/tasks` | Vazifalar ro'yxati |
| `/notes` | Zametka ro'yxati |
| `/report` | Haftalik hisobot |
| `/memory` | Xotira statistikasi |
| `/cleanup` | Eski ma'lumotlar tozalash |
| 🎤 Ovozli xabar | Gemini tahlil qiladi |
| 📄 PDF fayl | Gemini tahlil qiladi |
| 🖼 Rasm | Gemini tahlil qiladi |

---

## 🔒 Xavfsizlik

- Bot faqat **OWNER_CHAT_ID** dan kelgan xabarlarga javob beradi
- Boshqalar yozsa — **jim turadi** (hech qanday javob yo'q)
- Session string maxfiy — hech kimga bermang

---

## 📁 Fayl Tuzilmasi

```
ai-agent-bot/
├── bot.py              ← Asosiy fayl
├── database.py         ← SQLite boshqaruvi
├── ai_services.py      ← Groq + Gemini
├── userbot.py          ← Telethon (nomingizdan yuborish)
├── handlers.py         ← Barcha buyruqlar
├── get_session.py      ← Session olish (bir marta)
├── requirements.txt    ← Paketlar
├── railway.toml        ← Railway sozlamalar
└── .env.example        ← Namuna sozlamalar
```

---

## ❓ Muammolar

**Bot javob bermayapti:**
- Railway Logs da xatolikni ko'ring
- OWNER_CHAT_ID to'g'riligini tekshiring

**UserBot ishlamayapti:**
- TG_SESSION_STRING ni qayta oling (get_session.py)

**Groq xatosi:**
- console.groq.com da API kalitni tekshiring
