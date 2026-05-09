"""
UserBot — Telethon orqali kontaktlarga xabar yuborish
send_voice qo'shildi (ElevenLabs mp3 fayllarini yuborish uchun)
"""

import os
import logging
from telethon import TelegramClient
from telethon.tl.types import InputPeerUser
from telethon.errors import SessionPasswordNeededError

log = logging.getLogger(__name__)

SESSION_STRING = os.getenv("TG_SESSION_STRING", "")


class UserBot:
    def __init__(self, api_id: int, api_hash: str, phone: str):
        self.api_id   = api_id
        self.api_hash = api_hash
        self.phone    = phone
        self.client: TelegramClient = None
        self.is_connected = False

    async def start(self):
        try:
            if SESSION_STRING:
                self.client = TelegramClient(
                    StringSession(SESSION_STRING), self.api_id, self.api_hash
                )
            else:
                self.client = TelegramClient("userbot", self.api_id, self.api_hash)

            await self.client.start(phone=self.phone)
            self.is_connected = True
            me = await self.client.get_me()
            log.info(f"✅ UserBot: {me.first_name} (@{me.username})")
        except Exception as e:
            log.error(f"UserBot xatosi: {e}")
            self.is_connected = False

    async def stop(self):
        if self.client:
            await self.client.disconnect()

    # ── Kontaktdan entity topish ──────────────────────────────
    async def _resolve_target(self, target: str):
        """Ism, username yoki telefon → entity"""
        target = target.strip()

        # Username
        if target.startswith("@"):
            return await self.client.get_entity(target)

        # Telefon raqami
        if re.match(r'^\+?\d{7,15}$', target.replace(' ', '')):
            return await self.client.get_entity(target)

        # Ism bo'yicha kontaktlardan qidirish
        contacts = await self.get_contacts_raw()
        target_lower = target.lower()
        for c in contacts:
            full_name = f"{c.get('first','',)} {c.get('last','')}".strip().lower()
            if target_lower in full_name or full_name in target_lower:
                return await self.client.get_entity(c['user_id'])

        # To'g'ridan username sifatida urinib ko'rish
        return await self.client.get_entity(target)

    async def send_message(self, target: str, content: str) -> dict:
        """Matnli xabar yuborish"""
        if not self.is_connected:
            return {"ok": False, "error": "UserBot ulanmagan"}
        try:
            import re
            entity = await self._resolve_target(target)
            await self.client.send_message(entity, content)
            name = getattr(entity, 'first_name', None) or getattr(entity, 'title', target)
            return {"ok": True, "name": name}
        except Exception as e:
            log.error(f"Xabar yuborish xatosi: {e}")
            return {"ok": False, "error": str(e)}

    async def send_voice(self, target: str, audio_path: str) -> dict:
        """Ovozli xabar yuborish (mp3/ogg fayl yo'li)"""
        if not self.is_connected:
            return {"ok": False, "error": "UserBot ulanmagan"}
        try:
            import re
            entity = await self._resolve_target(target)
            await self.client.send_file(
                entity,
                audio_path,
                voice_note=True,
                attributes=[]
            )
            name = getattr(entity, 'first_name', None) or getattr(entity, 'title', target)
            return {"ok": True, "name": name}
        except Exception as e:
            log.error(f"Ovozli xabar yuborish xatosi: {e}")
            return {"ok": False, "error": str(e)}

    async def get_contacts_raw(self) -> list:
        """Xom kontaktlar"""
        if not self.is_connected:
            return []
        try:
            from telethon.tl.functions.contacts import GetContactsRequest
            result = await self.client(GetContactsRequest(hash=0))
            contacts = []
            for u in result.users:
                contacts.append({
                    "user_id": u.id,
                    "first":   u.first_name or "",
                    "last":    u.last_name or "",
                    "username": u.username,
                })
            return contacts
        except Exception as e:
            log.error(f"Kontaktlar xatosi: {e}")
            return []

    async def get_contacts_list(self) -> list:
        """Formatlangan kontaktlar ro'yxati"""
        if not self.is_connected:
            return []
        try:
            from telethon.tl.functions.contacts import GetContactsRequest
            result = await self.client(GetContactsRequest(hash=0))
            contacts = []
            for u in result.users:
                name = f"{u.first_name or ''} {u.last_name or ''}".strip() or "Nomsiz"
                contacts.append({
                    "name":     name,
                    "username": u.username,
                    "phone":    getattr(u, "phone", None),
                })
            return sorted(contacts, key=lambda x: x["name"])
        except Exception as e:
            log.error(f"Kontaktlar xatosi: {e}")
            return []


# StringSession import (agar SESSION_STRING ishlatilsa)
try:
    from telethon.sessions import StringSession
except ImportError:
    pass

import re
