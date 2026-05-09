"""
AutoReply — AutoPilot moduli
Sizning nomingizdan kelgan xabarlarga AI orqali javob beradi
Telethon event handler orqali ishlaydi
"""

import os
import logging
import asyncio
from datetime import datetime, timedelta
from groq import Groq

log = logging.getLogger(__name__)

GROQ_API_KEY = os.getenv("GROQ_API_KEY", "")
GROQ_MODEL   = os.getenv("GROQ_MODEL", "llama3-70b-8192")
OWNER_NAME   = os.getenv("OWNER_NAME", "O'tkirbek")
OWNER_ID     = int(os.getenv("OWNER_CHAT_ID", "0"))

# Whitelist — .env dan olinadi: AUTO_REPLY_WHITELIST=@user1,@user2
WHITELIST_ENV = os.getenv("AUTO_REPLY_WHITELIST", "")


class AutoReply:
    """
    Rejimlar:
    - off       : o'chirilgan
    - on        : hammaga javob beradi
    - whitelist : faqat ruxsatli kontaktlarga
    """

    def __init__(self, client, bot_instance=None):
        self.client      = client
        self.bot         = bot_instance
        self.mode        = "off"
        self.enabled     = False
        self.paused_until = None
        self.groq        = Groq(api_key=GROQ_API_KEY) if GROQ_API_KEY else None

        # Whitelist
        self.whitelist = [
            w.strip() for w in WHITELIST_ENV.split(",")
            if w.strip()
        ]

        # Xabar tarixi (spam oldini olish)
        self._replied: dict = {}  # {chat_id: last_reply_time}

    def register_handlers(self):
        """Telethon event handlerlarini ro'yxatdan o'tkazish"""
        from telethon import events

        @self.client.on(events.NewMessage(incoming=True))
        async def handle_incoming(event):
            await self._process_incoming(event)

        log.info("✅ AutoReply handlers ro'yxatdan o'tdi")

    async def _process_incoming(self, event):
        """Kelgan xabarni qayta ishlash"""
        try:
            # Rejim tekshiruvi
            if not self.enabled or self.mode == "off":
                return

            # Pause tekshiruvi
            if self.paused_until and datetime.now() < self.paused_until:
                return

            # Guruh xabarlari — o'tkazib yuborish
            if event.is_group or event.is_channel:
                return

            # O'z xabarlarimiz — o'tkazib yuborish
            sender = await event.get_sender()
            if not sender:
                return
            if getattr(sender, 'id', None) == OWNER_ID:
                return
            if getattr(sender, 'bot', False):
                return

            chat_id = event.chat_id

            # Whitelist tekshiruvi
            if self.mode == "whitelist":
                if not self._is_whitelisted(sender):
                    return

            # Spam oldini olish — 5 daqiqada 1 marta
            last = self._replied.get(chat_id)
            if last and (datetime.now() - last) < timedelta(minutes=5):
                return

            # Xabar matni
            text = event.message.text or event.message.message or ""
            if not text.strip():
                return

            # AI javob yaratish
            reply = await self._generate_reply(text, sender)
            if not reply:
                return

            # Javob yuborish
            await event.respond(reply)
            self._replied[chat_id] = datetime.now()

            log.info(f"AutoReply → {getattr(sender, 'first_name', '?')}: {reply[:50]}...")

            # Owner ga bildirishnoma
            if self.bot and OWNER_ID:
                sender_name = getattr(sender, 'first_name', '') or 'Noma\'lum'
                username    = getattr(sender, 'username', '') or ''
                uname_str   = f" (@{username})" if username else ""
                await self.bot.send_message(
                    OWNER_ID,
                    f"🤖 *AutoPilot javob berdi*\n\n"
                    f"👤 Kim: {sender_name}{uname_str}\n"
                    f"💬 Xabar: _{text[:100]}_\n"
                    f"📤 Javob: _{reply[:100]}_"
                )

        except Exception as e:
            log.error(f"AutoReply process xatosi: {e}")

    async def _generate_reply(self, text: str, sender) -> str:
        """Groq orqali javob yaratish"""
        if not self.groq:
            return (
                f"Assalomu alaykum! Men {OWNER_NAME}ning AI yordamchisiman. "
                f"{OWNER_NAME} hozir band, tez orada javob beradi. "
                f"Muhim bo'lsa, qayta yozing."
            )

        sender_name = getattr(sender, 'first_name', 'Do\'st') or "Do'st"

        system = (
            f"Sen {OWNER_NAME}ning shaxsiy AI yordamchisisan. "
            f"{OWNER_NAME} hozir band — sen uning nomidan javob berasan. "
            f"Uslub: muloyim, professional, o'zbek yoki rus tilida (xabar tiliga qarab). "
            f"Javob qisqa bo'lsin (2-3 jumla). "
            f"Muhim xabarlarda '{OWNER_NAME} tez orada bog'lanadi' de. "
            f"Hech qachon sun'iy intellekt ekanligingni aytma — inson kabi gapir."
        )

        try:
            resp = self.groq.chat.completions.create(
                model=GROQ_MODEL,
                messages=[
                    {"role": "system", "content": system},
                    {"role": "user",   "content": f"{sender_name} yozdi: {text}"}
                ],
                max_tokens=200,
                temperature=0.8
            )
            return resp.choices[0].message.content.strip()
        except Exception as e:
            log.error(f"AutoReply Groq xatosi: {e}")
            return (
                f"Salom! {OWNER_NAME} hozir band. "
                f"Xabaringiz qabul qilindi, tez orada javob beradi."
            )

    def _is_whitelisted(self, sender) -> bool:
        """Foydalanuvchi whitelist da bor-yo'qligini tekshirish"""
        username = getattr(sender, 'username', '') or ''
        user_id  = str(getattr(sender, 'id', ''))
        phone    = getattr(sender, 'phone', '') or ''

        for entry in self.whitelist:
            entry = entry.lstrip('@').lower()
            if (entry == username.lower() or
                entry == user_id or
                entry == phone):
                return True
        return False

    # ── Boshqaruv metodlari ───────────────────────────────────

    def enable(self):
        self.enabled     = True
        self.paused_until = None
        log.info(f"AutoReply YONDIRILDI — rejim: {self.mode}")

    def disable(self):
        self.enabled = False
        log.info("AutoReply O'CHIRILDI")

    def set_mode(self, mode: str):
        """on | whitelist | off"""
        if mode in ("on", "whitelist", "off"):
            self.mode = mode
            log.info(f"AutoReply rejim: {mode}")

    def pause(self, minutes: int = 60):
        self.paused_until = datetime.now() + timedelta(minutes=minutes)
        log.info(f"AutoReply {minutes} daqiqa to'xtatildi")

    def add_to_whitelist(self, username: str):
        username = username.lstrip('@').lower()
        if username not in self.whitelist:
            self.whitelist.append(username)
            log.info(f"Whitelist qo'shildi: {username}")

    def remove_from_whitelist(self, username: str):
        username = username.lstrip('@').lower()
        if username in self.whitelist:
            self.whitelist.remove(username)

    def get_status(self) -> str:
        if not self.enabled:
            return "⚫ O'chirilgan"

        if self.paused_until and datetime.now() < self.paused_until:
            left = int((self.paused_until - datetime.now()).total_seconds() / 60)
            return f"⏸ To'xtatilgan ({left} daqiqa qoldi)"

        mode_str = {
            "on":        "🟢 Hammaga javob beradi",
            "whitelist": f"🟡 Faqat ruxsatlilarga ({len(self.whitelist)} ta)",
            "off":       "⚫ O'chirilgan"
        }.get(self.mode, "❓ Noma'lum")

        return mode_str
