"""
UserBot — Telethon orqali sizning profilingizdan xabar yuborish
"""

import os
import logging
from telethon import TelegramClient
from telethon.sessions import StringSession

log = logging.getLogger(__name__)


class UserBot:
    def __init__(self, api_id: int, api_hash: str, phone: str):
        self.api_id   = api_id
        self.api_hash = api_hash
        self.phone    = phone
        self.session  = os.getenv("TG_SESSION_STRING", "")  # Railway da env orqali
        self.client   = None

    async def start(self):
        try:
            if self.session:
                # Session string mavjud bo'lsa (Railway uchun)
                self.client = TelegramClient(
                    StringSession(self.session),
                    self.api_id,
                    self.api_hash
                )
            else:
                # Fayl session (lokal test uchun)
                self.client = TelegramClient(
                    "userbot_session",
                    self.api_id,
                    self.api_hash
                )

            await self.client.start(phone=self.phone)
            me = await self.client.get_me()
            log.info(f"✅ UserBot ulandi: {me.first_name} (@{me.username})")
        except Exception as e:
            log.error(f"UserBot ulanish xatosi: {e}")
            self.client = None

    async def stop(self):
        if self.client:
            await self.client.disconnect()

    async def send_message(self, target: str, text: str) -> dict:
        """
        Kontakt qidirish va xabar yuborish
        target — ism, username yoki telefon raqam
        """
        if not self.client:
            return {"ok": False, "error": "UserBot ulanmagan"}

        try:
            # Username yoki telefon bo'lsa to'g'ridan yuborish
            if target.startswith("@") or target.startswith("+"):
                entity = await self.client.get_entity(target)
            else:
                # Ism bo'yicha kontaktlardan qidirish
                entity = await self._find_contact(target)
                if not entity:
                    return {"ok": False, "error": f"'{target}' kontaktlar orasida topilmadi"}

            await self.client.send_message(entity, text)
            name = getattr(entity, 'first_name', '') + ' ' + getattr(entity, 'last_name', '')
            return {"ok": True, "name": name.strip()}

        except Exception as e:
            return {"ok": False, "error": str(e)}

    async def _find_contact(self, name: str):
        """Ism bo'yicha kontakt qidirish"""
        try:
            from telethon.tl.functions.contacts import GetContactsRequest
            result = await self.client(GetContactsRequest(hash=0))
            name_lower = name.lower()

            for user in result.users:
                full = f"{user.first_name or ''} {user.last_name or ''}".lower()
                username = (user.username or "").lower()
                if name_lower in full or name_lower in username:
                    return user

            return None
        except Exception as e:
            log.error(f"Kontakt qidirish xatosi: {e}")
            return None

    async def get_session_string(self) -> str:
        """Session stringni olish (Railway env uchun bir marta ishlatiladi)"""
        if self.client:
            return self.client.session.save()
        return ""

    @property
    def is_connected(self) -> bool:
        return self.client is not None and self.client.is_connected()
