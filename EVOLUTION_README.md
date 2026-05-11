# 🧬 Self-Evolution Engine — O'z-o'zini Kuchaytirish Tizimi

## Arxitektura

```
bot.py                  ← Asosiy kirish nuqtasi (o'zgarmaydi)
self_evolution.py       ← Miya: modul yaratish, yuklash, tuzatish
evolution_handlers.py   ← Telegram buyruqlari
modules/                ← AI tomonidan yozilgan pluginlar saqlanadi
  weather.py
  currency_rates.py
  ... (AI qo'shadi)
logs/
  error.log             ← AI xatolarni shu yerdan o'qiydi
```

---

## 🔄 Workflow — Qanday Ishlaydi

```
Siz:   "Yangi modul qo'sh: USD/UZS kursni ko'rsatadigan funksiya"
         ↓
Bot:   AI → currency_rates.py yozadi → modules/ ga saqlaydi
         ↓
Bot:   importlib orqali dinamik yuklaydi
         ↓
[Xato bo'lsa] → logs/error.log → AI xatoni o'qiydi → kod tuzatadi
         ↓
[Muvaffaqiyat] → git commit -m "Self-update: added currency_rates"
```

---

## 📱 Telegram Buyruqlari

| Buyruq | Vazifa |
|--------|--------|
| `/modules` | Barcha modullar ro'yxati |
| `/module_run weather` | weather.py ning run() ni chaqirish |
| `/module_code weather` | Modul kodini ko'rish |
| `/module_del weather` | Modulni o'chirish |
| `/git_push` | GitHub ga push qilish |

### Matnli buyruqlar:
```
Yangi modul qo'sh: sms yuborish funksiyasi
Yangi modul qo'sh: nasos vibratsiyasini Excel ga eksport qilish
Modul ishga tushir: weather
Modul chaqir: currency_rates
```

---

## ⚙️ .env Sozlamalar

```env
# Self-Evolution
GIT_AUTO_COMMIT=true        # git commit avtomatik
MODULES_DIR=modules          # modullar papkasi
LOGS_DIR=logs                # xato loglar papkasi
```

---

## 📦 Modul Strukturasi

Har bir AI yaratgan modul shu tuzilishda bo'lishi kerak:

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

## 🔒 Xavfsizlik

- Faqat owner Telegram buyruqlari modul yarata oladi
- AI faqat `modules/` papkasiga yozadi
- Barcha modullar `try-except` bilan o'ralgan
- Xato bo'lsa butun bot to'xtamaydi — faqat modul qaytaradi xato xabari
