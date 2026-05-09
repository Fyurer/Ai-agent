"""
AutoReply — Kimdir yozsa, AI O'tkirbek nomidan javob beradi
Telethon event handler + Groq AI + owner nazorati
"""

import os
import logging
import asyncio
from datetime import datetime, timedelta
from telethon import events
from groq import Groq

log = logging.getLogger(__name__)

GROQ_MODEL = os.getenv("GROQ_MODEL", "llama3-70b-8192")
OWNER_NAME = os.getenv("OWNER_NAME", "O'tkirbek")

# ── Ruxsat berilgan rejimlar ──────────────────────────────────
# "on"    — hammaga javob beradi
# "whitelist" — faqat ruxsat etilgan kontaktlarga
# "off"   — o'chirilgan
AUTO_REPLY_MODE = os.getenv("AUTO_REPLY_MODE", "whitelist")

# Whitelist: telefon yoki username, vergul bilan ajratilgan
# Masalan: "+998901234567,@aziz_uz,Shodi"
WHITELIST_RAW = os.getenv("AUTO_REPLY_WHITELIST", "")

# Bir kishidan ketma-ket xabarlarda javob oralig'i (soniya)
REPLY_COOLDOWN = int(os.getenv("AUTO_REPLY_COOLDOWN", "30"))

# Guruh chatlariga javob bersinmi?
REPLY_TO_GROUPS = os.getenv("AUTO_REPLY_GROUPS", "false").lower() == "true"

# O'tkirbek haqida AI ga berilgan kontekst (qo'shimcha ma'lumot qo'shish mumkin)
OWNER_CONTEXT = os.getenv("AUTO_REPLY_CONTEXT", "")

AUTO_REPLY_SYSTEM = f"""Sen {OWNER_NAME} ning Telegram sun'iy intellekt yordamchisisan.
Hozir {OWNER_NAME} band yoki telefoniga qaray olmaydi.
Siz uning nomidan xabarlarga javob berasiz.

{OWNER_NAME} haqida:
- Olmaliq kon-metallurgiya kombinati (AGMK) 3-mis boyitish fabrikasida mexanik
- Professional, mas'uliyatli, do'stona muloqot uslubi
- O'zbek va rus tillarida muloqot qiladi
{f"- {OWNER_CONTEXT}" if OWNER_CONTEXT else ""}

Javob berish qoidalari:
1. Qisqa va aniq javob ber (2-4 jumladan oshmasin)
2. {OWNER_NAME} nomidan birinchi shaxsda gapir ("Men...", "Hozir...")
3. Agar muhim savol bo'lsa — "Hozir band edim, tez orada o'zim yozaman" de
4. Telefon raqam, bank ma'lumotlari so'ralsa — HECH QACHON berma, "O'zim qo'ng'iroq qilaman" de
5. Uchrashuvga chaqirilsa — "Vaqtimni tekshirib yozaman" de
6. Juda shaxsiy yoki muhim masalalarda — "{OWNER_NAME} o'zi javob beradi, hozir band" de
7. O'zbek tilida javob ber (agar rus tilida yozsa — ruscha javob)
8. Hech qachon AI ekanligingni oshkor qilma (so'ralsa ham)
"""


class AutoReply:
    def __init__(self, client, bot_instance=None):
        self.client = client
        self.bot = bot_instance          # Owner ga xabarnoma yuborish uchun
        self.groq = Groq(api_key=os.getenv("GROQ_API_KEY"))
        self.cooldowns: dict = {}         # {sender_id: last_reply_time}
        self.is_enabled = AUTO_REPLY_MODE != "off"
        self.whitelist = self._parse_whitelist()
        self.owner_id = int(os.getenv("OWNER_CHAT_ID", "0"))
        self.paused_until: datetime | None = None  # Vaqtincha to'xtatish

        log.info(f"AutoReply: rejim={AUTO_REPLY_MODE}, whitelist={self.whitelist}")

    def _parse_whitelist(self) -> list:
        if not WHITELIST_RAW:
            return []
        return [x.strip().lower() for x in WHITELIST_RAW.split(",") if x.strip()]

    def _in_whitelist(self, sender) -> bool:
        if not self.whitelist:
            return False
        phone = getattr(sender, "phone", "") or ""
        username = (getattr(sender, "username", "") or "").lower()
        first = (getattr(sender, "first_name", "") or "").lower()
        last  = (getattr(sender, "last_name",  "") or "").lower()
        full  = f"{first} {last}".strip()

        for entry in self.whitelist:
            if entry.startswith("@") and entry[1:] == username:
                return True
            if entry.startswith("+") and phone and entry in phone:
                return True
            if entry in full or entry in first:
                return True
        return False

    def _is_on_cooldown(self, sender_id: int) -> bool:
        last = self.cooldowns.get(sender_id)
        if not last:
            return False
        return (datetime.now() - last).total_seconds() < REPLY_COOLDOWN

    def _set_cooldown(self, sender_id: int):
        self.cooldowns[sender_id] = datetime.now()

    def _is_paused(self) -> bool:
        if self.paused_until and datetime.now() < self.paused_until:
            return True
        self.paused_until = None
        return False

    async def _generate_reply(self, incoming: str, sender_name: str,
                               history: list) -> str:
        """AI orqali javob generatsiya"""
        try:
            messages = [{"role": "system", "content": AUTO_REPLY_SYSTEM}]
            # Oxirgi 6 ta xabar tarixi
            for h in history[-6:]:
                messages.append(h)
            messages.append({
                "role": "user",
                "content": f"{sender_name} yozdi: {incoming}"
            })

            resp = self.groq.chat.completions.create(
                model=GROQ_MODEL,
                messages=messages,
                max_tokens=200,
                temperature=0.7
            )
            return resp.choices[0].message.content.strip()
        except Exception as e:
            log.error(f"AutoReply AI xatosi: {e}")
            return f"Salom! Hozir band edim, tez orada javob beraman."

    def register_handlers(self):
        """Telethon event handlerlarini ro'yxatdan o'tkazish"""

        @self.client.on(events.NewMessage(incoming=True))
        async def on_new_message(event):
            try:
                await self._handle_incoming(event)
            except Exception as e:
                log.error(f"AutoReply handler xatosi: {e}")

    async def _handle_incoming(self, event):
        """Kiruvchi xabarni qayta ishlash"""
        # Bot o'chirilgan
        if not self.is_enabled:
            return

        # Vaqtincha pauza
        if self._is_paused():
            return

        # Xabar matnini olish
        text = event.message.text or ""
        if not text:
            return

        # Guruh/kanal tekshirish
        if event.is_group or event.is_channel:
            if not REPLY_TO_GROUPS:
                return

        # Jo'natuvchini olish
        sender = await event.get_sender()
        if not sender:
            return

        sender_id = sender.id

        # O'ziga yozilgan xabarlarga javob berma
        me = await self.client.get_me()
        if sender_id == me.id:
            return

        # Owner ning o'z telefonidan yuborilgan xabarlarga javob berma
        if sender_id == self.owner_id:
            return

        # Whitelist rejimi
        if AUTO_REPLY_MODE == "whitelist" and not self._in_whitelist(sender):
            return

        # Cooldown tekshirish
        if self._is_on_cooldown(sender_id):
            return

        # Jo'natuvchi nomi
        sender_name = getattr(sender, "first_name", "") or "Noma'lum"

        # Suhbat tarixini olish (Telethon orqali)
        history = await self._get_chat_history(event.chat_id, limit=6)

        # AI javob generatsiya
        reply = await self._generate_reply(text, sender_name, history)

        # Javob yuborish
        await asyncio.sleep(1.5)  # Tabiiy kechikish
        await event.reply(reply)

        # Cooldown belgilash
        self._set_cooldown(sender_id)

        log.info(f"AutoReply: {sender_name} ({sender_id}) → javob yuborildi")

        # Owner ga xabarnoma (bot orqali)
        if self.bot and self.owner_id:
            try:
                notif = (
                    f"🤖 *AutoReply ishladi*\n\n"
                    f"👤 Kim: {sender_name}\n"
                    f"💬 Xabar: _{text[:80]}{'...' if len(text)>80 else ''}_\n"
                    f"🗣 Javob: _{reply[:80]}{'...' if len(reply)>80 else ''}_"
                )
                await self.bot.send_message(self.owner_id, notif)
            except Exception:
                pass

    async def _get_chat_history(self, chat_id, limit: int = 6) -> list:
        """Oxirgi xabarlarni olish (kontekst uchun)"""
        try:
            history = []
            async for msg in self.client.iter_messages(chat_id, limit=limit):
                if msg.text:
                    me = await self.client.get_me()
                    role = "assistant" if msg.sender_id == me.id else "user"
                    history.insert(0, {"role": role, "content": msg.text})
            return history
        except Exception:
            return []

    # ── Owner tomonidan boshqarish ────────────────────────────
    def enable(self):
        self.is_enabled = True
        self.paused_until = None
        log.info("AutoReply yoqildi")

    def disable(self):
        self.is_enabled = False
        log.info("AutoReply o'chirildi")

    def pause(self, minutes: int = 60):
        self.paused_until = datetime.now() + timedelta(minutes=minutes)
        log.info(f"AutoReply {minutes} daqiqa to'xtatildi")

    def set_mode(self, mode: str):
        """on / whitelist / off"""
        if mode in ("on", "whitelist", "off"):
            AUTO_REPLY_MODE_CURRENT = mode
            self.is_enabled = mode != "off"

    def add_to_whitelist(self, contact: str):
        self.whitelist.append(contact.strip().lower())

    def remove_from_whitelist(self, contact: str):
        key = contact.strip().lower()
        self.whitelist = [w for w in self.whitelist if w != key]

    def get_status(self) -> str:
        if not self.is_enabled:
            return "🔴 O'chirilgan"
        if self._is_paused():
            remaining = int((self.paused_until - datetime.now()).total_seconds() / 60)
            return f"⏸ Pauza ({remaining} daqiqa qoldi)"
        mode_emoji = {"on": "🟢", "whitelist": "🟡"}.get(AUTO_REPLY_MODE, "⚪")
        wl = f" | {len(self.whitelist)} ta kontakt" if AUTO_REPLY_MODE == "whitelist" else ""
        return f"{mode_emoji} Faol — rejim: {AUTO_REPLY_MODE}{wl}"
